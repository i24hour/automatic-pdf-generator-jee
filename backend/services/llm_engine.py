"""
LLM Engine Service
Uses litellm for provider-agnostic LLM calls.
Switch between Gemini, OpenAI, or Claude by changing ACTIVE_MODEL in .env
"""

import os
import json
import re
import asyncio
import hashlib
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import litellm

# Load environment variables
load_dotenv()
print("DEBUG: Loading llm_engine module...")

# Fallback models for reliability - if primary fails, try these in order
FALLBACK_MODELS = []  # No fallbacks as per user request (Quality/Cost control)


# =============================================
# Question History Helpers for Fresh Questions
# =============================================

def hash_question(question_text: str) -> str:
    """Generate MD5 hash of question text for fast duplicate detection."""
    # Normalize: lowercase, strip whitespace
    normalized = question_text.lower().strip()
    return hashlib.md5(normalized.encode()).hexdigest()


def get_user_question_history(db, user_id: str, topic: str, level: str, limit: int = 50) -> List[str]:
    """
    Fetch the last N questions for a user+topic+level combination.
    Returns list of question texts to include in the "do not repeat" prompt.
    """
    from models import UserQuestionHistory  # type: ignore[attr-defined]
    try:
        history = db.query(UserQuestionHistory).filter(
            UserQuestionHistory.user_id == user_id,
            UserQuestionHistory.topic == topic,
            UserQuestionHistory.level == level
        ).order_by(UserQuestionHistory.created_at.desc()).limit(limit).all()
        
        return [h.question_text for h in history]
    except Exception as e:
        print(f"Error fetching question history: {e}")
        return []


def save_question_history(db, user_id: str, topic: str, level: str, questions: List[str], max_history: int = 50):
    """
    Save new questions to history and prune old ones to keep only max_history.
    Uses rolling window approach to prevent database bloat.
    """
    from models import UserQuestionHistory, generate_uuid  # type: ignore[attr-defined]
    try:
        # Get existing count for this user+topic+level
        existing_count = db.query(UserQuestionHistory).filter(
            UserQuestionHistory.user_id == user_id,
            UserQuestionHistory.topic == topic,
            UserQuestionHistory.level == level
        ).count()
        
        # Add new questions
        added_count = 0
        for q_text in questions:
            if not q_text or len(q_text.strip()) < 10:
                continue  # Skip empty or very short questions
            
            q_hash = hash_question(q_text)
            
            # Check if already exists (same hash = same question)
            exists = db.query(UserQuestionHistory).filter(
                UserQuestionHistory.user_id == user_id,
                UserQuestionHistory.topic == topic,
                UserQuestionHistory.level == level,
                UserQuestionHistory.question_hash == q_hash
            ).first()
            
            if not exists:
                history_entry = UserQuestionHistory(
                    id=generate_uuid(),
                    user_id=user_id,
                    topic=topic,
                    level=level,
                    question_text=q_text[:2000],  # type: ignore # Limit text length
                    question_hash=q_hash
                )
                db.add(history_entry)
                added_count += 1
        
        db.commit()
        
        # Prune old entries if we exceed max_history
        total_count = existing_count + added_count
        if total_count > max_history:
            # Delete oldest entries
            to_delete = total_count - max_history
            oldest_entries = db.query(UserQuestionHistory).filter(
                UserQuestionHistory.user_id == user_id,
                UserQuestionHistory.topic == topic,
                UserQuestionHistory.level == level
            ).order_by(UserQuestionHistory.created_at.asc()).limit(to_delete).all()
            
            for entry in oldest_entries:
                db.delete(entry)
            
            db.commit()
        
        print(f"Saved {added_count} new questions to history for {topic}/{level}")
        
    except Exception as e:
        db.rollback()
        print(f"Error saving question history: {e}")


class LLMEngine:
    """LLM-agnostic engine for generating test questions."""
    
    def __init__(self):
        self.primary_model = os.getenv("ACTIVE_MODEL", "gemini/gemini-2.5-flash")
        self.model = self.primary_model
        self.fallback_models = FALLBACK_MODELS
        self._current_user_id = None      # Set per-request for verify/solution log calls
        self._current_generation_id = None  # UUID per test generation session
        self._setup_api_keys()
    
    def _setup_api_keys(self):
        """Setup API keys for litellm based on the active model."""
        # litellm automatically picks up these environment variables
        # GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY
        if not os.getenv("GEMINI_API_KEY") and os.getenv("GOOGLE_API_KEY"):
            os.environ["GEMINI_API_KEY"] = os.getenv("GOOGLE_API_KEY", "")
            print("DEBUG: Mapped GOOGLE_API_KEY to GEMINI_API_KEY")

    async def _log_usage(self, response, feature: str, user_id: Optional[str] = None,
                         subject: Optional[str] = None, level: Optional[str] = None):
        """Fire-and-forget: log LLM API usage to api_usage_logs table."""
        try:
            usage = getattr(response, "usage", None)
            if not usage:
                return
            from database import SessionLocal  # type: ignore[attr-defined]
            from models import APIUsageLog  # type: ignore[attr-defined]
            db = SessionLocal()
            try:
                log = APIUsageLog(
                    user_id=user_id,
                    generation_id=self._current_generation_id,
                    feature=feature,
                    model_name=str(self.model),
                    input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                    output_tokens=getattr(usage, "completion_tokens", 0) or 0,
                    total_tokens=getattr(usage, "total_tokens", 0) or 0,
                    subject=subject,
                    level=level,
                )
                db.add(log)
                db.commit()
            finally:
                db.close()
        except Exception as e:
            print(f"[UsageLog] Failed to log usage: {e}")
    
    def generate_with_fallback(
        self,
        subject: str,
        topic: str,
        mcq_count: int,
        numerical_count: int,
        level: str = "JEE Mains",
        difficulty: str = "Medium",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate questions with automatic model fallback for reliability.
        If primary model fails, tries fallback models in order.
        """
        all_models = [self.primary_model] + self.fallback_models
        last_error = None
        
        for model in all_models:
            try:
                self.model = model
                print(f"Trying model: {model}")
                result = self.generate_questions(
                    subject=subject,
                    topic=topic,
                    mcq_count=mcq_count,
                    numerical_count=numerical_count,
                    level=level,
                    difficulty=difficulty,
                    **kwargs
                )
                if result.get("success") and result.get("questions"):
                    print(f"✓ Success with model: {model}")
                    return result
                else:
                    print(f"✗ Model {model} returned no questions, trying next...")
                    last_error = result.get("error", "No questions generated")
            except Exception as e:
                print(f"✗ Model {model} failed: {str(e)}")
                last_error = str(e)
                continue
        
        # All models failed
        return {
            "success": False,
            "error": f"All models failed. Last error: {last_error}",
            "questions": []
        }

    async def generate_with_fallback_async(
        self,
        subject: str,
        topic: str,
        mcq_count: int,
        numerical_count: int,
        level: str = "JEE Mains",
        difficulty: str = "Medium",
        **kwargs
    ) -> Dict[str, Any]:
        """
        ASYNC version of generate_with_fallback.
        Uses litellm.acompletion for true non-blocking parallelism.
        """
        all_models = [self.primary_model] + self.fallback_models
        last_error = None
        
        for model in all_models:
            try:
                self.model = model
                print(f"Trying model (async): {model}")
                # Call the async generation method
                result = await self.generate_questions_async(
                    subject=subject,
                    topic=topic,
                    mcq_count=mcq_count,
                    numerical_count=numerical_count,
                    level=level,
                    difficulty=difficulty,
                    **kwargs
                )
                if result.get("success") and result.get("questions"):
                    print(f"✓ Success with model (async): {model}")
                    return result
                else:
                    print(f"✗ Model {model} returned no questions, trying next...")
                    last_error = result.get("error", "No questions generated")
            except Exception as e:
                print(f"✗ Model {model} failed (async): {str(e)}")
                last_error = str(e)
                continue
        
        # All models failed
        return {
            "success": False,
            "error": f"All models failed. Last error: {last_error}",
            "questions": []
        }
    
    async def generate_parallel(
        self,
        subject: str,
        topic: str,
        mcq_count: int,
        numerical_count: int,
        level: str = "JEE Mains",
        difficulty: str = "Medium",
        chunk_size: int = 10,  # Smaller chunks = more reliable JSON from flash-lite = fewer retries
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate questions in PARALLEL for faster performance.
        Splits the request into multiple smaller chunks and runs them concurrently.
        This can reduce generation time by 50-70%.

        Supports an optional `on_chunk_ready` async callback in kwargs.
        Called with the cumulative list of questions each time a chunk completes,
        so the caller can stream partial results to the client in real-time.
        """
        import asyncio

        # Pop the streaming callback before kwargs reach the LLM
        on_chunk_ready = kwargs.pop('on_chunk_ready', None)
        
        # If small enough, just do single call
        total_requested = mcq_count + numerical_count
        if total_requested <= chunk_size:
            result = await self.generate_with_fallback_async(subject, topic, mcq_count, numerical_count, level, difficulty, **kwargs)
            if on_chunk_ready and result.get("success") and result.get("questions"):
                try:
                    await on_chunk_ready(result["questions"])
                except Exception as cb_err:
                    print(f"on_chunk_ready callback error: {cb_err}")
            return result
            
        # NOTE: GATE now uses same flow as other exams (no special parallel strategy)
        # This avoids rate limit issues from multiple simultaneous API calls
        
        # Calculate chunks for MCQs
        mcq_chunks = []
        remaining_mcq = mcq_count
        while remaining_mcq > 0:
            chunk = min(chunk_size, remaining_mcq)
            mcq_chunks.append(chunk)
            remaining_mcq -= chunk
        
        # Calculate chunks for numericals
        num_chunks = []
        remaining_num = numerical_count
        while remaining_num > 0:
            chunk = min(chunk_size, remaining_num)
            num_chunks.append(chunk)
            remaining_num -= chunk
        
        print(f"Parallel generation: {len(mcq_chunks)} MCQ chunks + {len(num_chunks)} numerical chunks")
        
        # Create async tasks for each chunk
        async def generate_chunk(index, mcq_cnt, num_cnt):
            """Run async generation"""
            print(f"--- Starting chunk {index} (MCQ: {mcq_cnt}, Num: {num_cnt}) ---")
            import time
            start_time = time.time()
            
            # Use ASYNC method directly - no to_thread needed
            result = await self.generate_with_fallback_async(
                subject, topic, mcq_cnt, num_cnt, level, difficulty, **kwargs
            )
            
            duration = time.time() - start_time
            print(f"--- Finished chunk {index} in {duration:.2f}s ---")
            return result
        
        tasks = []
        # MCQ-only chunks
        for i, mcq_chunk in enumerate(mcq_chunks):
            tasks.append(generate_chunk(f"M{i}", mcq_chunk, 0))
        # Numerical-only chunks
        for i, num_chunk in enumerate(num_chunks):
            tasks.append(generate_chunk(f"N{i}", 0, num_chunk))
        
        # ── STREAM chunks as they complete (instead of waiting for all) ──
        all_questions = []
        for future in asyncio.as_completed(tasks):
            try:
                result = await future
                if isinstance(result, dict) and result.get("success") and result.get("questions"):
                    all_questions.extend(result["questions"])
                    # Notify caller so it can push partial results to the client
                    if on_chunk_ready:
                        try:
                            await on_chunk_ready(list(all_questions))
                        except Exception as cb_err:
                            print(f"on_chunk_ready callback error: {cb_err}")
                    print(f"Streamed {len(all_questions)} questions so far")
            except Exception as e:
                print(f"Chunk failed: {e}")
        
        # Deduplicate
        all_questions = self._deduplicate_questions(all_questions)
        
        print(f"Parallel generation complete: {len(all_questions)} total questions")
        
        return {
            "success": len(all_questions) > 0,
            "subject": subject,
            "topic": topic,
            "questions": all_questions
        }

    async def _generate_gate_parallel(
        self,
        subject: str,
        topic: str,
        mcq_count: int,
        numerical_count: int,
        level: str,
        difficulty: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Special parallel generation for GATE exams.
        Splits into 4 parallel tasks: GA, MCQ, MSQ, NAT.
        """
        import asyncio
        import time
        
        num_ga = kwargs.get("num_ga", 0)
        num_msq = kwargs.get("num_msq", 0)
        num_nat = kwargs.get("num_nat", 0)
        num_mcq = mcq_count
        
        print(f"GATE Parallel: GA={num_ga}, MCQ={num_mcq}, MSQ={num_msq}, NAT={num_nat}")
        
        async def generate_gate_part(part_name, **part_kwargs):
            print(f"--- Starting GATE Part: {part_name} ---")
            start_time = time.time()
            
            # Merge original kwargs with part-specific kwargs
            call_kwargs = kwargs.copy()
            call_kwargs.update(part_kwargs)
            
            # For MCQ part, we pass mcq_count=num_mcq. For others, mcq_count=0 (but they use their own counts)
            # Actually, generate_questions uses mcq_count as num_mcq.
            # So for GA, MSQ, NAT, we can pass mcq_count=0, but we must ensure they don't generate MCQs.
            # Our updated generate_questions handles this via gate_subset.
            
            # However, generate_with_fallback_async takes mcq_count as arg.
            # If gate_subset="GA", num_mcq is ignored by generate_questions logic, but we should pass 0 to be safe/clean.
            
            result = await self.generate_with_fallback_async(
                subject, topic, 
                mcq_count=part_kwargs.get("mcq_count_arg", 0), 
                numerical_count=0, 
                level=level, 
                difficulty=difficulty, 
                **call_kwargs
            )
            
            duration = time.time() - start_time
            print(f"--- Finished GATE Part: {part_name} in {duration:.2f}s ---")
            return result

        tasks = []
        
        # 1. General Aptitude
        if num_ga > 0:
            tasks.append(generate_gate_part("GA", gate_subset="GA", mcq_count_arg=0))
            
        # 2. MCQs
        if num_mcq > 0:
            # Split MCQs if too many? For now, 20-30 is fine in one go.
            tasks.append(generate_gate_part("MCQ", gate_subset="MCQ", mcq_count_arg=num_mcq))
            
        # 3. MSQs
        if num_msq > 0:
            tasks.append(generate_gate_part("MSQ", gate_subset="MSQ", mcq_count_arg=0))
            
        # 4. NATs
        if num_nat > 0:
            tasks.append(generate_gate_part("NAT", gate_subset="NAT", mcq_count_arg=0))
            
        # Run all
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_questions = []
        for result in results:
            if isinstance(result, BaseException):
                print(f"GATE Part failed: {result}")
                continue
            if isinstance(result, dict) and result.get("success") and result.get("questions"):
                all_questions.extend(result["questions"])
                
        print(f"GATE Parallel complete: {len(all_questions)} questions")
        
        return {
            "success": len(all_questions) > 0,
            "subject": subject,
            "topic": topic,
            "questions": all_questions
        }

    def detect_subject(self, topic: str) -> Dict[str, Any]:
        """Classify a topic into a subject with confidence using the LLM."""
        
        # Handle common abbreviations and patterns BEFORE sending to LLM
        topic_upper = topic.upper().strip()
        topic_lower = topic.lower().strip()
        
        # ============ MULTI-SUBJECT PATTERNS ============
        # Check for PCM/PCMB abbreviations - these indicate ALL subjects
        if "PCMB" in topic_upper or "PCBM" in topic_upper:
            return {"subject": "PCMB", "confidence": "high", "is_multi": True}
        elif "PCM" in topic_upper or "PMC" in topic_upper:
            return {"subject": "PCM", "confidence": "high", "is_multi": True}
        elif "PCB" in topic_upper:
            return {"subject": "PCB", "confidence": "high", "is_multi": True}
        
        # "Full syllabus" without subject specification - return all subjects (PCMB)
        # Frontend/backend will filter based on exam type
        if ("full syllabus" in topic_lower or "complete syllabus" in topic_lower or 
            "all chapters" in topic_lower or "entire syllabus" in topic_lower or
            topic_lower in ["full", "complete", "all"]):
            return {"subject": "PCMB", "confidence": "high", "is_multi": True}
        
        # ============ PREFIX OPTIMIZATION (No LLM) ============
        # Catch common prefixes to avoid LLM calls for partial typing
        if topic_lower.startswith("phy"): return {"subject": "Physics", "confidence": "high"}
        if topic_lower.startswith("chem"): return {"subject": "Chemistry", "confidence": "high"}
        if topic_lower.startswith("math"): return {"subject": "Maths", "confidence": "high"}
        if topic_lower.startswith("zoo"): return {"subject": "Zoology", "confidence": "high"}
        if topic_lower.startswith("bot"): return {"subject": "Botany", "confidence": "high"}
        if topic_lower.startswith("bio"): return {"subject": "Zoology", "confidence": "medium"} # Ambiguous but better than LLM
        if len(topic.strip()) < 4: return {"subject": "Physics", "confidence": "low"} # Return default for short inputs
        
        # ============ PHYSICS PATTERNS ============
        physics_keywords = [
            "electrostatics", "electrostatic", "magnetism", "magnetic", "optics", "optical",
            "mechanics", "kinematics", "dynamics", "newton", "rotational", "gravitation",
            "waves", "oscillations", "thermodynamics", "heat", "carnot", "shm", "simple harmonic",
            "fluid", "bernoulli", "viscosity", "current electricity", "ohm", "kirchhoff",
            "capacitor", "capacitance", "inductor", "inductance", "electromagnetic", "em waves",
            "photoelectric", "nuclear", "radioactive", "semiconductor", "diode", "transistor",
            "ray optics", "wave optics", "interference", "diffraction", "polarization",
            "motion", "force", "momentum", "energy", "work", "power", "projectile", "friction"
        ]
        
        # ============ CHEMISTRY PATTERNS ============
        chemistry_keywords = [
            "atomic structure", "atom", "orbital", "quantum", "electronic configuration",
            "chemical bonding", "covalent", "ionic", "vsepr", "hybridization", "molecular",
            "periodic", "periodicity", "s-block", "p-block", "d-block", "f-block", "transition",
            "organic", "alkane", "alkene", "alkyne", "alcohol", "aldehyde", "ketone", "carboxylic",
            "inorganic", "coordination", "ligand", "isomer", "goc", "general organic",
            "electrochemistry", "electrolysis", "galvanic", "nernst", "redox", "oxidation",
            "solution", "colligative", "osmotic", "raoult", "mole concept", "stoichiometry",
            "equilibrium", "le chatelier", "kp", "kc", "ionic equilibrium", "ph", "buffer",
            "iupac", "nomenclature", "polymer", "biomolecule", "carbohydrate", "protein", "amino",
            "chemical kinetics", "rate", "order", "arrhenius", "catalyst", "surface chemistry"
        ]
        
        # ============ MATHS PATTERNS ============
        maths_keywords = [
            "integration", "integral", "differentiation", "derivative", "calculus",
            "algebra", "quadratic", "polynomial", "equation", "inequality",
            "trigonometry", "trigonometric", "sin", "cos", "tan", "inverse trig",
            "coordinate", "straight line", "circle", "parabola", "ellipse", "hyperbola", "conic",
            "vector", "3d", "three dimensional", "plane", "direction cosine",
            "matrix", "matrices", "determinant", "inverse matrix",
            "probability", "permutation", "combination", "binomial", "statistics",
            "sequence", "series", "ap", "gp", "harmonic", "arithmetic progression",
            "complex number", "argand", "de moivre", "limits", "continuity",
            "function", "relation", "domain", "range", "composite", "lcd", "monotonicity"
        ]
        
        # ============ BIOLOGY PATTERNS (NEET) ============
        zoology_keywords = [
            "human physiology", "digestion", "respiration", "circulation", "excretion",
            "animal kingdom", "classification", "phylum", "chordata", "mammalia",
            "genetics", "mendel", "chromosome", "dna", "rna", "mutation", "heredity",
            "evolution", "darwin", "lamarck", "natural selection", "speciation",
            "reproduction", "gametogenesis", "fertilization", "embryology", "menstrual",
            "human health", "disease", "immunity", "vaccine", "pathogen", "aids", "cancer"
        ]
        
        botany_keywords = [
            "plant physiology", "photosynthesis", "transpiration", "mineral nutrition",
            "plant kingdom", "algae", "bryophyte", "pteridophyte", "gymnosperm", "angiosperm",
            "cell biology", "cell structure", "mitochondria", "chloroplast", "cell cycle",
            "ecology", "ecosystem", "biodiversity", "environment", "pollution", "conservation",
            "plant reproduction", "flower", "pollination", "seed", "fruit",
            "biotechnology", "genetic engineering", "recombinant", "pcr", "gel electrophoresis"
        ]
        
        # Check patterns (case-insensitive)
        for keyword in physics_keywords:
            if keyword in topic_lower:
                return {"subject": "Physics", "confidence": "high"}
        
        for keyword in chemistry_keywords:
            if keyword in topic_lower:
                return {"subject": "Chemistry", "confidence": "high"}
        
        for keyword in maths_keywords:
            if keyword in topic_lower:
                return {"subject": "Maths", "confidence": "high"}
        
        for keyword in zoology_keywords:
            if keyword in topic_lower:
                return {"subject": "Zoology", "confidence": "high"}
        
        for keyword in botany_keywords:
            if keyword in topic_lower:
                return {"subject": "Botany", "confidence": "high"}
        
        # If no pattern matched, use LLM
        prompt = f"""
You are a subject classifier for JEE/NEET exam topics. Given the topic text, return a JSON with:
- "subject": one of ["Physics", "Chemistry", "Maths", "Zoology", "Botany"]
- "confidence": "high", "medium", or "low"

IMPORTANT Classification Rules:
- Chemistry topics include: Atomic Structure, Chemical Bonding, Periodic Table, Organic Chemistry, Inorganic Chemistry, Electrochemistry, Thermodynamics (Chemical), Solutions, Equilibrium, Mole Concept, Redox Reactions, Coordination Compounds, s-block/p-block/d-block elements, Acids & Bases, Polymers, Biomolecules
- Physics topics include: Mechanics, Electrostatics, Magnetism, Optics, Modern Physics (Photoelectric effect, Nuclear Physics), Waves, Thermodynamics (Heat engines, Carnot cycle), Fluid Mechanics, Gravitation, Rotational Motion
- Maths topics include: Calculus, Integration, Differentiation, Algebra, Trigonometry, Coordinate Geometry, Probability, Statistics, Matrices, Sequences and Series, Complex Numbers
- Zoology topics include: Human Physiology, Animal Kingdom, Genetics, Evolution, Reproduction in Animals, Human Health and Disease
- Botany topics include: Plant Physiology, Plant Kingdom, Cell Biology, Ecology, Plant Reproduction, Biotechnology

Topic: "{topic}"

Return ONLY JSON, no extra text.
Example: {{"subject":"Chemistry","confidence":"high"}}
"""

        try:
            response = litellm.completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise subject classifier. Only return valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            response_text = response.choices[0].message.content or ""  # type: ignore[union-attr]
            cleaned = self._clean_json_response(response_text)
            data = json.loads(cleaned)
            subject = str(data.get("subject", "Physics")).strip()
            confidence = str(data.get("confidence", "medium")).strip().lower()
            if confidence not in {"high", "medium", "low"}:
                confidence = "medium"
            # Normalize subject casing
            subject_map = {s.lower(): s for s in ["Physics", "Chemistry", "Maths", "Zoology", "Botany"]}
            subject = subject_map.get(subject.lower(), "Physics")
            return {"subject": subject, "confidence": confidence}
        except Exception as e:
            print(f"detect_subject failed: {e}")
            return {"subject": "Physics", "confidence": "low"}
    
    def _clean_json_response(self, response_text: str) -> str:
        """
        Clean the LLM response to extract valid JSON.
        Handles markdown code blocks, extra text, and invalid escape sequences.
        """
        import re
        
        # Remove markdown code blocks
        cleaned = response_text.strip()
        
        # Remove ```json or ``` blocks
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]  # type: ignore
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]  # type: ignore
        
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]  # type: ignore
        
        cleaned = cleaned.strip()
        
        # Find the JSON object boundaries
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}") + 1
        
        if start_idx != -1 and end_idx > start_idx:
            candidate = cleaned[start_idx:end_idx]  # type: ignore
            # Handle double-braced JSON {{...}} which some models might output if prompted with {{
            if candidate.startswith("{{") and candidate.endswith("}}"):
                # Check if it's not just a nested object, but truly double braced
                # Heuristic: if len > 2 and char at 1 is {, and char at -2 is }
                if len(candidate) > 2 and candidate[1] == "{" and candidate[-2] == "}":
                     candidate = candidate[1:-1]
            cleaned = candidate
        
        # CRITICAL FIX: Escape LaTeX backslashes BEFORE JSON parsing
        # Common LaTeX commands that start with characters that are invalid JSON escapes
        # \f (form feed), \b (backspace), \r (carriage return), \n (newline), \t (tab)
        # These get interpreted as control characters during JSON.parse if not escaped
        
        # List of LaTeX commands to protect (that start with problematic characters)
        latex_commands = [
            'frac', 'forall', 'fbox',
            'binom', 'bar', 'beta', 'begin', 'bf', 'big', 'bigg',
            'right', 'rangle', 'rceil', 'rfloor', 'rm',
            'nabla', 'neg', 'neq', 'newline', 'nu',
            'tan', 'tau', 'text', 'textbf', 'therefore', 'theta', 'times', 'to', 'triangle',
            'alpha', 'gamma', 'delta', 'epsilon', 'zeta', 'eta', 'theta', 'iota', 'kappa',
            'lambda', 'mu', 'nu', 'xi', 'pi', 'rho', 'sigma', 'tau', 'upsilon', 'phi', 'chi', 'psi', 'omega',
            'Gamma', 'Delta', 'Theta', 'Lambda', 'Xi', 'Pi', 'Sigma', 'Upsilon', 'Phi', 'Psi', 'Omega',
            'inf', 'infty', 'int', 'item',
            'left', 'lim', 'limits',
            'matrix', 'pmatrix', 'bmatrix', 'vmatrix', 'Vmatrix', 'Bmatrix',
            'hat', 'hline', 'huge', 'Huge',
            'prod', 'partial',
            'sum', 'sqrt', 'sim', 'sin', 'cos', 'sec', 'csc', 'cot', 'log', 'ln', 'exp',
            'end', 'exists', 'epsilon',
            'det', 'dim', 'div',
            'subset', 'subseteq', 'sum',
            'vec', 'vert',
            'approx', 'angle', 'arc',
            'cap', 'cup', 'cdot',
        ]
        
        # Replace \cmd with \\cmd for all LaTeX commands (double the backslash)
        for cmd in latex_commands:
            # Match \cmd but not \\cmd (already escaped)
            pattern = r'(?<!\\)\\' + cmd
            replacement = r'\\\\' + cmd
            cleaned = re.sub(pattern, replacement, cleaned)
        
        # Also escape any remaining single backslashes that aren't valid JSON escapes
        # Valid JSON escapes: \", \\, \/, \b, \f, \n, \r, \t, \uXXXX
        def fix_remaining_escapes(match):
            char = match.group(1)
            # Only keep truly valid JSON escapes as-is
            if char in ['"', '\\', '/']:
                return match.group(0)
            elif char == 'u' and len(match.group(0)) >= 6:  # \uXXXX
                return match.group(0)
            else:
                # Double the backslash for anything else
                return '\\\\' + char
        
        # Match single backslash followed by any character (not already doubled)
        cleaned = re.sub(r'(?<!\\)\\([^\\])', fix_remaining_escapes, cleaned)
        
        return cleaned

    def _repair_truncated_json(self, truncated: str) -> List[Dict[str, Any]]:
        """
        Attempt to salvage questions from a truncated JSON response.
        When the LLM runs out of tokens mid-JSON, we try to extract
        whatever complete question objects exist in the partial response.
        """
        import re

        # Find all complete question objects using brace matching
        # Look for individual {...} blocks inside the "questions" array
        questions_match = re.search(r'"questions"\s*:\s*\[', truncated)
        if not questions_match:
            return []

        array_start = questions_match.end()
        salvaged_questions: List[Dict[str, Any]] = []
        i = array_start
        
        while i < len(truncated):
            # Skip whitespace and commas
            while i < len(truncated) and truncated[i] in ' \t\n\r,':
                i += 1
            
            if i >= len(truncated) or truncated[i] != '{':
                break
            
            # Track braces to find complete objects
            depth = 0
            obj_start = i
            in_string = False
            escaped = False
            
            for j in range(i, len(truncated)):
                c = truncated[j]
                if escaped:
                    escaped = False
                    continue
                if c == '\\':
                    escaped = True
                    continue
                if c == '"' and not escaped:
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        # Found a complete object
                        obj_str = truncated[obj_start:j+1]
                        try:
                            # Re-clean this individual object
                            cleaned_obj = self._clean_json_response(obj_str)
                            obj = json.loads(cleaned_obj)
                            if isinstance(obj, dict) and (obj.get("question") or obj.get("text")):
                                salvaged_questions.append(obj)
                        except (json.JSONDecodeError, Exception):
                            pass  # Skip malformed individual objects
                        i = j + 1
                        break
            else:
                # Reached end without closing brace — this object is truncated
                break

        return salvaged_questions

    
    def _escape_latex_outside_math(self, text: str) -> str:
        """
        Escape special LaTeX characters in text, but PRESERVE math mode content.
        Handles both inline $...$ and block $$...$$ math modes correctly.
        """
        if not text:
            return text
        
        import re
        
        # Use regex to find all math regions:
        # 1. Block math: $$ ... $$
        # 2. Inline math: $ ... $
        # 3. Explicit environments: \begin{...} ... \end{...} (using backreference \2 to match end tag)
        # 4. Use (?s) flag to ensure . matches newlines (crucial for matrices)
        math_pattern = r'(?s)(\$\$.*?\$\$|\\begin\{([a-zA-Z]+\*?)\}.*?\\end\{\2\}|\$[^$]+?\$)'
        
        result = []
        last_end = 0
        
        for match in re.finditer(math_pattern, text):
            # Process content BEFORE this math block (non-math text)
            non_math_part = text[last_end:match.start()]  # type: ignore
            if non_math_part:
                escaped = non_math_part.replace('&', r'\&').replace('%', r'\%')
                result.append(escaped)
            
            # Process the math block itself (preserve as is)
            result.append(match.group(0))  # group(0) is the full match, ignoring subgroups
            
            last_end = match.end()
            
        # Process remaining text after the last math block
        remaining_part = text[last_end:]  # type: ignore
        if remaining_part:
            escaped = remaining_part.replace('&', r'\&').replace('%', r'\%')
            result.append(escaped)
        
        return ''.join(result)
    
    def _fix_spacing(self, text: str) -> str:
        """Fix common spacing issues in LLM output and convert markdown to LaTeX."""
        if not text:
            return text
        
        import re
        
        # Convert markdown **bold** to LaTeX \textbf{bold}
        text = re.sub(r'\*\*([^*]+)\*\*', r'\\textbf{\1}', text)
        
        # Convert markdown *italic* to LaTeX \textit{italic}
        text = re.sub(r'\*([^*]+)\*', r'\\textit{\1}', text)
        
        # Fix period/comma followed directly by lowercase (missing space)
        text = re.sub(r'([.,])([a-z])', r'\1 \2', text)
        
        # Add space after colon if followed by a letter/number (not in math mode)
        text = re.sub(r':([A-Za-z0-9$])', r': \1', text)
        
        # Add space after closing paren followed by letter (outside math)
        text = re.sub(r'\)([A-Z])', r') \1', text)
        
        # Add space between Roman numerals and letters: (I)CH -> (I) CH
        text = re.sub(r'\(([IVX]+)\)([A-Za-z$])', r'(\1) \2', text)
        
        # Add space after period if followed by capital letter
        text = re.sub(r'\.([A-Z])', r'. \1', text)
        
        # Add space around arrows that aren't in math mode
        text = text.replace('→', ' → ')
        text = text.replace('->', ' -> ')
        
        # ===== SOLUTION STEP SPACING & BOLDING =====
        
        # 1. Fix fully bold steps: \textbf{Step 1: Text} -> \textbf{Step 1:} Text
        # This handles case where LLM outputs **Step 1: Text**
        text = re.sub(r'\\textbf\{\s*(Step\s*\d+\s*:)\s*([^}]+)\}', r'\\textbf{\1} \2', text, flags=re.IGNORECASE)
        
        # 2. Normalize: Remove \textbf wrapper from "Step N:" if it exists, so we can re-apply consistently
        text = re.sub(r'\\textbf\{\s*(Step\s*\d+\s*:)\s*\}', r'\1', text, flags=re.IGNORECASE)
        
        # 3. Apply Spacing + Bold: Add line break and bold ONLY the label "Step N:"
        # Matches: Step 1:, Step 2:, etc. (not at start of string)
        text = re.sub(r'(?<!^)\s*(Step\s*\d+\s*:)', r'\n\n\\par\\vspace{0.3em}\n\\textbf{\1}', text, flags=re.IGNORECASE)
        
        # 4. Handle FIRST step (at start of string) - Just Bold, no vertical space
        text = re.sub(r'^\s*(Step\s*\d+\s*:)', r'\\textbf{\1}', text, flags=re.IGNORECASE)
        
        # Clean up multiple spaces
        text = re.sub(r' +', ' ', text)
        
        return text.strip()
    
    def _process_questions(self, questions: List[Dict]) -> List[Dict]:
        """Process questions - preserve math mode, minimal escaping, fix spacing."""
        processed = []
        for q in questions:
            # Apply spacing fixes before LaTeX escaping
            raw_text = q.get("text") or q.get("question") or ""
            text = self._fix_spacing(raw_text)
            text = self._escape_latex_outside_math(text)
            
            processed_q = {
                "type": q.get("type", "mcq"),
                "text": text,
                "answer": q.get("answer", ""),
                # "diagram_tikz": q.get("diagram_tikz"), # OLD
                "diagram_type": q.get("diagram_type"),   # NEW
                "diagram_params": q.get("diagram_params") # NEW
            }
            
            if q.get("options"):
                processed_q["options"] = [
                    self._escape_latex_outside_math(self._fix_spacing(opt)) 
                    for opt in q["options"]
                ]
            else:
                processed_q["options"] = []
            
            processed.append(processed_q)
        
        return processed
    
    def _deduplicate_questions(self, questions: List[Dict]) -> List[Dict]:
        """Remove duplicate questions based on text similarity."""
        seen_texts = set()
        unique_questions = []
        
        for q in questions:
            # Normalize text for comparison (lowercase, remove extra spaces)
            raw_text = q.get('text') or q.get('question') or ''
            normalized = ' '.join(raw_text.lower().split())
            
            # Only add if we haven't seen similar text
            if normalized not in seen_texts and len(normalized) > 10:
                seen_texts.add(normalized)
                unique_questions.append(q)
        
        return unique_questions

    def generate_questions(  # noqa: ... kept for API compatibility
        self,
        subject: str,
        topic: str,
        mcq_count: int,
        numerical_count: int,
        level: str = "JEE Mains",
        difficulty: str = "Medium",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate test questions using the configured LLM.
        
        Args:
            subject: The subject (Physics, Chemistry, Maths)
            topic: The specific topic
            mcq_count: Number of MCQ questions
            numerical_count: Number of numerical questions
            level: Exam type (CBSE Board, JEE Mains, JEE Advanced, Olympiad, NEET)
            difficulty: Difficulty within exam (Easy, Medium, Hard)
            
        Returns:
            Dictionary with questions data
        """
        total_requested = mcq_count + numerical_count
        return {}

    async def _generate_questions_async_v1(
        self,
        subject: str,
        topic: str,
        mcq_count: int,
        numerical_count: int,
        level: str = "JEE Mains",
        difficulty: str = "Medium",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Legacy ASYNC version of generate_questions (v1, kept for compatibility).
        """
        total_requested = mcq_count + numerical_count
        
        # Get difficulty percentages from kwargs (default: 20-50-30)
        easy_percent = kwargs.get('easy_percent', 20)
        medium_percent = kwargs.get('medium_percent', 50)
        hard_percent = kwargs.get('hard_percent', 30)
        
        # Calculate exact counts for each difficulty level
        easy_count = max(1, round(total_requested * easy_percent / 100)) if easy_percent > 0 else 0
        hard_count = max(1, round(total_requested * hard_percent / 100)) if hard_percent > 0 else 0
        medium_count = total_requested - easy_count - hard_count
        # Ensure medium_count is at least 0
        if medium_count < 0:
            medium_count = 0
            # Redistribute
            if easy_count > hard_count:
                easy_count = total_requested - hard_count
            else:
                hard_count = total_requested - easy_count
        
        # Build difficulty distribution prompt with EXACT COUNTS
        difficulty_prompt = f"""DIFFICULTY DISTRIBUTION (STRICT REQUIREMENT):
You MUST generate EXACTLY the following number of questions at each difficulty level:
- {easy_count} EASY questions: Straightforward application, simple calculations, most students should solve
- {medium_count} MEDIUM questions: Standard exam-level, 2-3 step problems, some conceptual depth  
- {hard_count} HARD questions: Challenging, multi-step with conceptual twists, differentiates toppers

TOTAL: {easy_count} + {medium_count} + {hard_count} = {total_requested} questions

IMPORTANT: 
- This distribution is MANDATORY, not a suggestion.
- Mix difficulty levels throughout the paper, don't group all Easy questions together.
- If you generate fewer HARD questions than required, the paper will be rejected."""
        
        # Detailed level-specific prompts with examples
        level_prompts = {
            "CBSE Board": """EXAM TYPE: CBSE Board Pattern
CHARACTERISTICS:
- Follow EXACT CBSE Board exam pattern
- Direct application of NCERT concepts
- Focus on definitions, derivations, and conceptual understanding
- Questions should match CBSE Class 11/12 term exams

CBSE QUESTION TYPES (generate a mix of ALL types):

1. VERY SHORT ANSWER (VSA) - 1-2 Marks:
   - One-liner answers, definitions, state laws/principles
   - Example: "Define electric flux. Write its SI unit."
   - Example: "State the principle of superposition of waves."
   - Generate as type "short_answer" with marks: 1 or 2

2. SHORT ANSWER (SA) - 2-3 Marks:
   - Brief explanations, simple derivations, diagrams
   - Example: "Derive the relation between electric field and potential."
   - Example: "Explain the working of a transformer with a diagram."
   - Generate as type "short_answer" with marks: 2 or 3

3. LONG ANSWER (LA) - 5 Marks:
   - Detailed derivations, proofs, multi-part questions
   - Example: "Derive lens maker's formula. Using it, derive thin lens formula."
   - Example: "State and prove Gauss's law. Apply it to find field due to infinite charged plane."
   - Generate as type "long_answer" with marks: 5

4. CASE-BASED QUESTIONS - 4 Marks:
   - A paragraph describing a real-world scenario
   - Followed by 4 MCQs (1 mark each) based on that paragraph
   - Example: Paragraph about electromagnetic induction in power plants, then 4 MCQs
   - Generate as type "case_based" with a "passage" field and "sub_questions" array

5. NUMERICALS - 3-5 Marks:
   - Direct formula application, simple calculations
   - Example: "A wire of resistance 10Ω is bent into a circle. Find equivalent resistance across diameter."
   - Generate as type "numerical" with marks: 3 or 5

IMPORTANT: 
- DO NOT generate only MCQs for CBSE Board
- Generate a balanced mix of VSA, SA, LA, and Numericals
- Include at least 1-2 Case-based questions if total questions >= 10
- Questions should be NCERT-aligned""",

            "JEE Mains": """EXAM TYPE: JEE Main Level
CHARACTERISTICS:
- Application-based problems requiring 2-3 step solutions
- Conceptual twists and common misconception traps
- Integration of 2 related concepts
- Moderate calculation complexity
- Questions similar to NTA JEE Main papers
- Numerical questions are INTEGER TYPE (answer must be an integer from 0-999)

EXAMPLE JEE MAINS-LEVEL QUESTIONS:
- "A capacitor is charged to V volts and then connected to an inductor. Find maximum current"
- "Two blocks connected by spring on frictionless surface - find oscillation frequency"
- "In Young's double slit, if one slit is covered with thin film, find fringe shift"
- Distractors should include common calculation errors

IMPORTANT FOR NUMERICAL QUESTIONS:
- Design questions so that the final answer is a WHOLE NUMBER (integer)
- Answers should be in range 0-999 (as per actual JEE Mains pattern)
- Frame questions like "Find the value of X" where X comes out to be an integer
- Example: Instead of "find velocity" giving 2.5 m/s, ask "find velocity in cm/s" giving 250""",

            "JEE Advanced": """EXAM TYPE: JEE Advanced Level
CHARACTERISTICS:
- Multi-concept problems requiring 4-5 step solutions
- Non-obvious approach needed, lateral thinking required
- Integration of 3+ concepts from different subtopics
- Complex mathematical manipulation
- Questions similar to actual IIT JEE Advanced papers
- Paragraph-based or assertion-reason style thinking

QUESTION TYPES FOR JEE ADVANCED:
1. MULTI-CORRECT MCQs (first ~20% of MCQs): Questions where MORE THAN ONE option is correct
   - Use type "mcq_multi" for these
   - Answer should be like "AB", "ACD", "BD" etc. (multiple correct options)
   - These test deeper understanding where multiple statements/conditions can be true
   
2. SINGLE-CORRECT MCQs (remaining ~80% of MCQs): Standard single answer questions
   - Use type "mcq" for these
   - Answer should be single letter like "A", "B", "C", or "D"

EXAMPLE JEE ADVANCED-LEVEL QUESTIONS:
- Multi-correct: "Which of the following are true for an adiabatic process?" (Answer: "AC")
- Single-correct: "A conducting sphere in non-uniform electric field - find induced dipole moment"
- "Block on accelerating wedge with friction - find condition for relative motion"
- Problems that test edge cases and deep understanding""",

            "Olympiad": """EXAM TYPE: Physics/Chemistry/Math Olympiad Level
CHARACTERISTICS:
- Research-level problem-solving skills needed
- Creative and unconventional approaches required
- May require deriving new results from first principles
- International Olympiad (IPhO, IChO, IMO) standard
- Problems that top 0.1% students find challenging
- Often involves elegant mathematical tricks or physical insights

EXAMPLE OLYMPIAD-LEVEL QUESTIONS:
- "Derive the shape of a rotating liquid surface and find the focal length of the parabolic mirror formed"
- "N coupled oscillators - find normal modes and frequencies for arbitrary N"
- "Prove using variational methods that a certain physical quantity is minimized"
- Problems from IPHO, INPHO, IMO, RMO past papers""",

            "NEET": """EXAM TYPE: NEET Level (Medical Entrance Exam)
CHARACTERISTICS:
- NCERT-based conceptual questions - stick to NCERT content strictly
- Assertion-Reason type questions are very common (format as regular MCQ with options like "Both A and R are true and R is the correct explanation of A")
- Statement-based MCQs (identify correct/incorrect statements)
- Focus on factual recall, definitions, and direct application
- Similar to NTA NEET papers and NEET PYQs
- ONLY MCQs (no numerical questions in NEET)

IMPORTANT FORMATTING RULES FOR NEET:
- DO NOT use tables, columns, or "Match the following" format - these don't render well
- For matching questions, convert to regular MCQ format with options like "A-2, B-3, C-1, D-4"
- Keep questions simple and text-based
- Keep questions simple and text-based
- Use simple lists if needed, not complex formatting

REQUIREMENTS FOR SOLUTIONS:
- Provide brief explanation for the correct answer in "solution" field.
- For Biology: Explain why option is correct.
- For Physics/Chem: Show calculation steps using \\textbf{{Step 1:}} format and $$...$$ for equations.

EXAMPLE NEET-LEVEL QUESTIONS:
- "Which of the following is NOT a function of liver?"
- "Assertion: Mitochondria are called powerhouse of cell. Reason: ATP synthesis occurs here. Options: (a) Both A and R are true, R explains A (b) Both A and R are true, R does not explain A..."
- "The correct sequence of air passage in humans is:"
- "Which of the following statements about photosynthesis is incorrect?"
- Questions from NEET, AIIMS, JIPMER past papers""",

            "GATE": """EXAM TYPE: GATE (Graduate Aptitude Test in Engineering)
CHARACTERISTICS:
- High conceptual depth and problem-solving required
- Questions test fundamental understanding of core engineering subjects
- Mix of theoretical and numerical problems
- Questions often link multiple concepts
- Similar to actual GATE PYQs (Past Year Questions)

QUESTION TYPES:
1. MCQ (Multiple Choice): 1 correct option (Negative marking)
2. MSQ (Multiple Select): 1 or more correct options (NO negative marking)
3. NAT (Numerical Answer Type): Enter a number (NO negative marking)
4. GA (General Aptitude): Verbal and Numerical ability

IMPORTANT:
- For MSQ, use type "mcq_multi" and answer like "AC"
- For NAT, use type "numerical" and answer must be a number
- For GA, cover both Verbal (English) and Quantitative Aptitude"""
        }
        
        level_prompt: str = level_prompts.get(level, level_prompts["JEE Mains"])
        
        # JEE Mains uses integer-type numerical questions (0-999)
        if level == "JEE Mains":
            numerical_answer_instruction = "7. NUMERICAL ANSWERS: Must be INTEGERS ONLY (whole numbers like 42, 150, 0, 999). NO decimals, NO formulas, NO fractions, NO symbols. Design questions so answers fall in range 0-999."
        elif level == "GATE":
            numerical_answer_instruction = "7. NUMERICAL ANSWERS: Can be integers or decimals (e.g., 25, 3.14, -1.5). NO formulas, NO fractions."
        else:
            numerical_answer_instruction = "7. NUMERICAL ANSWERS: Must be ONLY integers or decimals (e.g., \"42\", \"3.14\", \"-5.5\"). NO formulas, NO fractions, NO symbols."
            
        subject_constraint = f"""
CRITICAL SUBJECT CONSTRAINT:
You MUST ONLY generate questions for the subject: {subject.upper()}. 
DO NOT generate any questions from other subjects like Physics or Maths if the subject is Chemistry.
Even if the topic says 'Full Syllabus' or 'Mock Test', you must restrict all questions strictly to the {subject.upper()} syllabus.
"""

        # JEE Advanced: first 20% of MCQs should be multi-correct
        mcq_instruction: str = ""  # default; overridden below for specific levels
        json_example: str = ""  # default
        if level == "JEE Advanced":
            multi_correct_count = max(1, int(mcq_count * 0.2))  # At least 1 multi-correct
            single_correct_count = mcq_count - multi_correct_count
            mcq_instruction = f"""FOR MCQs:
- Generate {multi_correct_count} MULTI-CORRECT MCQs FIRST (type: "mcq_multi", answer like "AB", "ACD", "BC")
- Then generate {single_correct_count} SINGLE-CORRECT MCQs (type: "mcq", answer like "A", "B", "C", "D")
- Multi-correct questions should have 2-3 correct options out of 4

SOLUTION REQUIREMENTS:
- Provide a "solution" field for EVERY question.
- Solution must be detailed and step-by-step.
- Use \\textbf{{Step 1:}} format for steps.
- **CRITICAL**: Put a full empty line (gap) between each step.
- **CRITICAL**: Write EVERY mathematical equation on a SEPARATE LINE using display math ($$ ... $$) so it is centered.
- Do NOT write equations inline with text.
- Example: "The force is given by: $$ F = ma $$" """
            json_example = """{
    "questions": [
        {
            "type": "mcq_multi",
            "text": "Which of the following are correct for an isothermal process?",
            "options": ["$\\Delta U = 0$", "$PV = constant$", "$\\Delta T = 0$", "$Q = 0$"],
            "answer": "ABC",
            "answer": "ABC",
            "solution": "\\textbf{Step 1:} For an isothermal process, temperature is constant ($T = constant$), so change in temperature is zero. $$ \\Delta T = 0 $$ \\vspace{1em} \\textbf{Step 2:} Internal energy depends only on temperature for an ideal gas. $$ \\Delta U = 0 $$ \\vspace{1em} \\textbf{Step 3:} From ideal gas equation $PV = nRT$, since $T$ is constant: $$ PV = constant $$ (Boyle's Law).",
            "diagram_tikz": null
            "diagram_tikz": null
        }},
        {{
            "type": "mcq",
            "text": "Single correct question with $math$ notation",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "answer": "A",
            "solution": "\\\\textbf{Step 1:} Analyze each option systematically.\\n\\n\\\\textbf{Step 2:} Apply the relevant formula: $$ F = ma $$\\n\\n\\\\textbf{Step 3:} Option A satisfies all conditions as the acceleration is directly proportional to applied force. Hence, correct answer is A.",
            "diagram_tikz": null
        }},
        {{
            "type": "numerical", 
            "text": "Numerical question with $math$",
            "options": [],
            "answer": "3",
            "solution": "\\textbf{Step 1:} Identify given values: $$ x = 10, y = 5 $$ \\vspace{1em} \\textbf{Step 2:} Apply formula: $$ z = x + y $$ \\vspace{1em} \\textbf{Step 3:} Calculate result: $$ z = 15 $$",
            "diagram_tikz": null
        }}
    ]
}}"""
        elif level == "GATE":
            # GATE Logic
            gate_paper = kwargs.get("gate_paper", "CSE")
            num_msq = kwargs.get("num_msq", 0)
            num_nat = kwargs.get("num_nat", 0)
            num_ga = kwargs.get("num_ga", 0)
            num_mcq = mcq_count  # Remaining are MCQs
            
            mcq_instruction = f"""FOR GATE PATTERN:
- Generate {num_ga} General Aptitude (GA) questions (Verbal/Quant)
- Generate {num_mcq} MCQs (Single Correct) on {gate_paper} Core Subject
- Generate {num_msq} MSQs (Multiple Select) on {gate_paper} Core Subject (type: "mcq_multi")
- Generate {num_nat} NATs (Numerical Answer) on {gate_paper} Core Subject (type: "numerical")"""
            
            json_example = """{
    "questions": [
        {
            "type": "mcq",
            "text": "GA Question: Choose the correct word...",
            "options": ["A", "B", "C", "D"],
            "answer": "A"
        },
        {
            "type": "mcq",
            "text": "Core Subject MCQ...",
            "options": ["A", "B", "C", "D"],
            "answer": "B"
        },
        {
            "type": "mcq_multi",
            "text": "Core Subject MSQ...",
            "options": ["A", "B", "C", "D"],
            "answer": "AC"
        },
        {
            "type": "numerical",
            "text": "Core Subject NAT...",
            "options": [],
            "answer": "25.5"
        }
    ]
}"""
        if level == "JEE Advanced":
            # JEE Advanced specific instructions with diagrams
            mcq_instruction = """FOR MCQs: Mix of Single Correct and Multi-Correct (match exam pattern).
DIAGRAM HANDLING (STRICT):
1. Decide if diagram is required (Ray optics, Circuits, Graph-based, Geometry).
2. If REQUIRED: Set diagram_type to one of ["free_body", "projectile_motion", "inclined_plane", "basic_circuit"].
3. If NOT REQUIRED: Set diagram_type to null.
4. If diagram_type is set, providing matching diagram_params object.

QUESTION OUTPUT FORMAT (STRICT):
For EACH question, return a JSON object in this format:
{
  "question_text": "...",
  "options": ["A", "B", "C", "D"],
  "correct_answer": "A",
  "solution": "...",
  "difficulty": "medium",
  "diagram_type": "free_body",
  "diagram_params": { "mass": 5, "angle": 30 } (or null)
}"""

            json_example = """{
    "questions": [
        {
            "type": "mcq",
            "question_text": "A block of mass 5kg slides down an incline of 30 degrees...",
            "options": ["2 m/s^2", "4 m/s^2", "5 m/s^2", "9.8 m/s^2"],
            "answer": "A",
            "solution": "...",
            "diagram_type": "free_body",
            "diagram_params": {
                "mass": 5,
                "angle": 30
            }
        }
    ]
}"""
        
        # Special handling for CBSE Board - generate CBSE pattern questions, not just MCQs
        if level == "CBSE Board":
            # Calculate CBSE question distribution based on totals
            total_cbse_theory = mcq_count  # VSA+SA+LA+Case from frontend
            total_numericals = numerical_count
            
            # Get detailed breakdown if provided (from frontend), otherwise approximate
            vsa_count = kwargs.get("cbse_vsa", 0) or 0
            sa_count = kwargs.get("cbse_sa", 0) or 0
            la_count = kwargs.get("cbse_la", 0) or 0
            case_count = kwargs.get("cbse_case", 0) or 0
            
            # If explicit counts are not provided (all zero), fallback to approximation
            if vsa_count + sa_count + la_count + case_count == 0:
                if total_cbse_theory > 0:
                    vsa_count = max(1, int(total_cbse_theory * 0.4))
                    sa_count = max(1, int(total_cbse_theory * 0.3))
                    la_count = max(1, int(total_cbse_theory * 0.15))
                    case_count = max(0, total_cbse_theory - vsa_count - sa_count - la_count)
            
            # Ensure total numericals is respecting user input or backend logic
            total_numericals = numerical_count
            
            boards_json_example = """{
    "questions": [
        {"type": "short_answer", "marks": 1, "text": "Define electric flux.", "answer": "Electric flux is the measure of electric field lines passing through a surface.", "solution": "Electric flux ($\\\\Phi_E$) is defined as the total number of electric field lines passing through a given surface. Mathematically: $$ \\\\Phi_E = \\\\vec{E} \\\\cdot \\\\vec{A} = EA\\\\cos\\\\theta $$ where $E$ is the electric field, $A$ is the area, and $\\\\theta$ is the angle between field and normal."},
        {"type": "short_answer", "marks": 2, "text": "State the principle of superposition.", "answer": "When two waves meet, the resultant displacement is the vector sum of individual displacements.", "solution": "\\\\textbf{Step 1:} Principle of superposition states that when two or more waves overlap, the resultant displacement at any point is the algebraic sum of the individual displacements.\\n\\n\\\\textbf{Step 2:} Mathematically, if $y_1$ and $y_2$ are two waves: $$ y = y_1 + y_2 $$ This principle applies to all types of waves - sound, light, water waves."},
        {"type": "short_answer", "marks": 3, "text": "Derive E = -dV/dr.", "answer": "The electric field is the negative gradient of potential.", "solution": "\\\\textbf{Step 1:} Work done in moving charge $q$ from $r$ to $r+dr$: $$ dW = -qE \\\\cdot dr $$\\n\\n\\\\textbf{Step 2:} This work equals change in potential energy: $$ dW = q \\\\cdot dV $$\\n\\n\\\\textbf{Step 3:} Equating: $$ q \\\\cdot dV = -qE \\\\cdot dr $$\\n\\n\\\\textbf{Step 4:} Simplifying: $$ E = -\\\\frac{dV}{dr} $$ This shows electric field points from high to low potential."},
        {"type": "long_answer", "marks": 5, "text": "State and prove Gauss's law.", "answer": "Gauss's law states that total electric flux through a closed surface equals enclosed charge divided by permittivity.", "solution": "\\\\textbf{Statement:} The total electric flux through any closed surface is equal to $\\\\frac{1}{\\\\epsilon_0}$ times the total charge enclosed.\\n\\n$$\\\\oint \\\\vec{E} \\\\cdot d\\\\vec{A} = \\\\frac{Q_{enc}}{\\\\epsilon_0}$$\\n\\n\\\\textbf{Step 1:} Consider a point charge $q$ at center of a sphere of radius $r$.\\n\\n\\\\textbf{Step 2:} Electric field at surface: $$ E = \\\\frac{1}{4\\\\pi\\\\epsilon_0} \\\\frac{q}{r^2} $$\\n\\n\\\\textbf{Step 3:} Total flux: $$ \\\\Phi = E \\\\times 4\\\\pi r^2 = \\\\frac{q}{4\\\\pi\\\\epsilon_0 r^2} \\\\times 4\\\\pi r^2 $$\\n\\n\\\\textbf{Step 4:} Simplifying: $$ \\\\Phi = \\\\frac{q}{\\\\epsilon_0} $$ Hence proved."},
        {"type": "case_based", "marks": 4, "passage": "Electromagnetic induction is the phenomenon of generation of electric current due to changing magnetic flux.", "sub_questions": [
            {"text": "Who discovered electromagnetic induction?", "options": ["Newton", "Faraday", "Maxwell", "Ampere"], "answer": "B"},
            {"text": "What is required for electromagnetic induction?", "options": ["Static field", "Changing flux", "Electric field", "Gravity"], "answer": "B"},
            {"text": "Which device uses electromagnetic induction?", "options": ["Capacitor", "Resistor", "Transformer", "Diode"], "answer": "C"},
            {"text": "When was it discovered?", "options": ["1820", "1831", "1840", "1850"], "answer": "B"}
        ], "answer": "B, B, C, B", "solution": "\\\\textbf{Q1:} Michael Faraday discovered electromagnetic induction in 1831.\\n\\n\\\\textbf{Q2:} Changing magnetic flux is essential; static fields don't induce EMF.\\n\\n\\\\textbf{Q3:} Transformers work on mutual induction principle.\\n\\n\\\\textbf{Q4:} Faraday discovered it in 1831 through his famous ring experiment."},
        {"type": "numerical", "marks": 3, "text": "A wire of resistance $10\\\\Omega$ is bent into a circle. Find equivalent resistance across diameter.", "answer": "2.5", "solution": "\\\\textbf{Step 1:} When wire is bent into circle, total resistance = $10\\\\Omega$.\\n\\n\\\\textbf{Step 2:} Across diameter, circle divides into two equal halves.\\n\\n\\\\textbf{Step 3:} Each half has resistance: $$ R_{half} = \\\\frac{10}{2} = 5\\\\Omega $$\\n\\n\\\\textbf{Step 4:} Two $5\\\\Omega$ resistors in parallel: $$ R_{eq} = \\\\frac{5 \\\\times 5}{5 + 5} = \\\\frac{25}{10} = 2.5\\\\Omega $$"}
    ]
}"""
            
            prompt = f"""You are an expert CBSE Board exam setter. Generate CBSE pattern questions on "{topic}" for {subject}.

{level_prompt}

{difficulty_prompt}

{subject_constraint}

GENERATE EXACTLY:
- {vsa_count} Very Short Answer (1-2 marks, type: "short_answer", marks: 1 or 2)
- {sa_count} Short Answer (2-3 marks, type: "short_answer", marks: 2 or 3)  
- {la_count} Long Answer (5 marks, type: "long_answer", marks: 5)
- {case_count} Case-Based (4 marks, type: "case_based" with passage and 4 MCQ sub_questions)
- {total_numericals} Numerical (3-5 marks, type: "numerical", marks: 3 or 5)

TOTAL: {total_cbse_theory + total_numericals} questions

REQUIREMENTS:
- NCERT-aligned content
- Each question MUST be UNIQUE
- Use LaTeX math mode: $F = ma$, $\\\\frac{{a}}{{b}}$
- For case_based: include "passage", "sub_questions" array with 4 MCQs

Return ONLY valid JSON:
{boards_json_example}"""
        elif level == "JEE Advanced":
            num_msq = kwargs.get("num_msq", 0) or 0
            num_matrix = kwargs.get("num_matrix", 0) or 0
            num_paragraph = kwargs.get("num_paragraph", 0) or 0
            # mcq_count contains (Single Correct + Multi Correct), numericals are integer type
            num_single = max(0, mcq_count - num_msq)

            # Build generate list
            gen_lines: List[str] = []
            if num_single > 0:
                gen_lines.append(f'- {num_single} Single Correct MCQ(s) [type: "mcq", 4 options, 1 correct, Mark: 3]')
            if num_msq > 0:
                gen_lines.append(f'- {num_msq} Multi Correct MCQ(s) [type: "mcq_multi", 4 options, >=1 correct, Mark: 4]')
            if numerical_count > 0:
                gen_lines.append(f'- {numerical_count} Integer Type Question(s) [type: "numerical", integer answer, Mark: 3]')
            if num_matrix > 0:
                gen_lines.append(f'- {num_matrix} Matrix Match Question(s) [type: "matrix_match", Match List-I rows A/B/C/D with List-II options p/q/r/s, Mark: 8]')
            if num_paragraph > 0:
                gen_lines.append(f'- {num_paragraph} Comprehension Set(s) [type: "paragraph", each has a passage + 2 MCQ sub_questions, Mark: 3 each]')
            gen_list = "\n".join(gen_lines)
            total_jee = num_single + num_msq + numerical_count + num_matrix + num_paragraph

            matrix_json = ''
            if num_matrix > 0:
                matrix_json = ''',
        {{
            "type": "matrix_match",
            "text": "Match List-I (Column I) with List-II (Column II):",
            "list1": ["A. Statement about concept X", "B. Statement about concept Y", "C. Statement about concept Z", "D. Statement about concept W"],
            "list2": ["p. Result p", "q. Result q", "r. Result r", "s. Result s"],
            "answer": "A-p,q; B-r; C-p,s; D-q,r",
            "solution": "\\\\textbf{{Step 1:}} Analyse row A: ...",
            "options": []
        }}'''

            paragraph_json = ''
            if num_paragraph > 0:
                paragraph_json = ''',
        {{
            "type": "paragraph",
            "text": "Comprehension: Based on the passage below, answer the questions that follow.",
            "passage": "A paragraph describing the physical/chemical scenario in 3-5 lines. Include relevant equations.",
            "sub_questions": [
                {{"text": "Sub-question 1 text based on passage", "options": ["A", "B", "C", "D"], "answer": "A", "solution": "Step 1..."}},
                {{"text": "Sub-question 2 text based on passage", "options": ["A", "B", "C", "D"], "answer": "C", "solution": "Step 1..."}}
            ],
            "answer": "See sub_questions",
            "options": []
        }}'''

            prompt = f"""You are an expert JEE Advanced question setter.

Generate exactly:
{gen_list}

Topic: "{topic}" for {subject}

{level_prompt}

{difficulty_prompt}

{subject_constraint}

TOTAL: {total_jee} questions

REQUIREMENTS:
1. For mcq: "answer" is single letter like "A"
2. For mcq_multi: "answer" is letters like "A, C" or "B, D"
3. For numerical: "answer" is an integer string like "5" or "-3"
4. For matrix_match: use fields "list1" (4 rows A-D) and "list2" (4 cols p-s). "answer" format: "A-p,r; B-q; C-p,s; D-r"
5. For paragraph: use "passage" field (3-5 line scenario) + "sub_questions" array with 2 MCQs each having text/options/answer/solution
6. Use LaTeX for math: $...$ inline, $$...$$ for display equations (centered)
7. PROVIDE a concise "solution" field (3-5 steps) for every question and sub_question.
8. Use \\textbf{{Step 1:}} format. End with \\textbf{{Final Answer:}}.

Return ONLY valid JSON:
{{"questions": [
    {{"type": "mcq", "text": "...", "options": ["A", "B", "C", "D"], "answer": "A", "solution": "..."}},
    {{"type": "mcq_multi", "text": "...", "options": ["A", "B", "C", "D"], "answer": "A, C", "solution": "..."}},
    {{"type": "numerical", "text": "...", "options": [], "answer": "5", "solution": "..."}}{matrix_json}{paragraph_json}
]}}"""
        elif level == "GATE":
            gate_paper = kwargs.get("gate_paper", "CSE")
            num_msq = kwargs.get("num_msq", 0) or 0
            num_nat = kwargs.get("num_nat", 0) or 0
            num_ga = kwargs.get("num_ga", 0) or 0
            # mcq_count now contains total questions, we need actual MCQ count
            num_mcq_actual = max(0, mcq_count - num_ga - num_msq - num_nat)
            
            # Build requirement list based on what user requested
            req_parts = []
            if num_ga > 0:
                req_parts.append(f"- {num_ga} General Aptitude (GA) MCQs (Verbal Reasoning, Quantitative Aptitude)")
            if num_mcq_actual > 0:
                req_parts.append(f"- {num_mcq_actual} Core Subject MCQs (single correct answer)")
            if num_msq > 0:
                req_parts.append(f"- {num_msq} Multiple Select Questions (MSQ - one or more correct options)")
            if num_nat > 0:
                req_parts.append(f"- {num_nat} Numerical Answer Type (NAT - type: \"numerical\")")
            
            req_list = "\n".join(req_parts) if req_parts else f"- {mcq_count} MCQs"
            total_q = mcq_count
            
            prompt = f"""You are an expert GATE {gate_paper} exam question setter.

Generate exactly {total_q} GATE-style questions on "{topic}".

{level_prompt}

{difficulty_prompt}

{subject_constraint}

GENERATE EXACTLY:
{req_list}

TOTAL: {total_q} Questions

REQUIREMENTS:
- All questions should be MCQ format with 4 options (A, B, C, D)
- Questions should match GATE {gate_paper} difficulty and syllabus
- Use LaTeX for math. Use $$...$$ for ALL equations to center them.
- Each question must have exactly one correct answer for MCQs
- PROVIDE DETAILED SOLUTIONS in "solution" field for every question.
- Use \\textbf{{Step 1:}} format.
- Ensure 1 line gap between steps (Use \\n\\n).
- START EACH STEP ON A NEW LINE.
- Center ALL equations.

Return ONLY valid JSON:
{json_example}"""
        else:
            # General Logic (Exam Specific)
            num_msq = kwargs.get("num_msq", 0) or 0
            # Ensure num_mcq_single is not negative
            num_mcq_single = max(0, mcq_count - num_msq)
            
            # Construct breakdown string
            req_list = []
            if num_mcq_single > 0:
                req_list.append(f"- {num_mcq_single} Single Correct MCQs (Type: 'mcq')")
            if num_msq > 0:
                req_list.append(f"- {num_msq} Multiple Correct MCQs (Type: 'mcq_multi', one or more correct options)")
            if numerical_count > 0:
                req_list.append(f"- {numerical_count} Numerical Type Questions (Type: 'numerical')")
            
            req_str = "\n".join(req_list)
            
            prompt = f"""You are an expert exam setter with 20+ years of experience setting {level} level examination papers for top coaching institutes like FIITJEE, Allen, and Resonance.

TASK: Generate fully detailed questions on "{topic}" for {subject}.

{level_prompt}

{difficulty_prompt}

{subject_constraint}

STRICT BREAKDOWN:
{req_str}

STRICT REQUIREMENTS:
1. Generate EXACTLY the count of questions requested above.
2. Each question MUST be UNIQUE.
3. Questions MUST match the specified difficulty level EXACTLY.
4. {mcq_instruction}
5. For Multiple Correct MCQs (mcq_multi):
   - There can be 1, 2, 3, or 4 correct options.
   - The 'answer' field should be a comma-separated string of correct options (e.g., "A, C" or "A, B, D").
   - Ensure these are challenging.
6. {numerical_answer_instruction}
7. PROVIDE DETAILED STEP-BY-STEP SOLUTIONS in "solution" field for EVERY question.
   - Use "\\\\textbf{{Step 1:}}" for steps.
   - Leave a ONE LINE GAP between steps (Use \\\\n\\\\n).
   - Write equations on SEPARATE LINES using $$...$$ (display math).
   - Center align all equations.
   - End with "\\\\textbf{{Final Answer:}} Option X" or value.

FORMATTING REQUIREMENTS:
- Use LaTeX math mode for ALL mathematical expressions: $...$
- FOR CHEMICAL REACTIONS OR LONG EQUATIONS use $$...$$
- Proper subscripts/superscripts ($x_2$, $x^2$).

QUALITY CHECK:
- Total questions = {total_requested}
- Check if you generated correct number of Single vs Multi correct MCQs.

Return ONLY valid JSON:
{json_example}"""

        max_retries = 1
        response_text: str = ""
        data: Dict[str, Any] = {}
        for attempt in range(max_retries + 1):
            try:
                response = litellm.completion(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert exam setter. Always respond with valid JSON only. Generate EXACTLY the number of questions requested."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.7
                )
                
                response_text = response.choices[0].message.content or ""  # type: ignore[union-attr]
                
                # DEBUG: Log raw response for troubleshooting
                print(f"[DEBUG] LLM raw response (first 500 chars): {response_text[:500] if response_text else 'EMPTY'}")
                
                # Clean and parse JSON
                cleaned_json = self._clean_json_response(response_text)
                data = json.loads(cleaned_json)
                
                # DEBUG: Log parsed data structure
                print(f"[DEBUG] Parsed JSON keys: {data.keys() if isinstance(data, dict) else 'Not a dict'}")
                print(f"[DEBUG] Questions count: {len(data.get('questions', []))}")
                
                # Process questions (escape LaTeX special chars)
                if "questions" in data:
                    data["questions"] = self._process_questions(data["questions"])
                    
                    # Deduplicate questions
                    data["questions"] = self._deduplicate_questions(data["questions"])
                    
                    # Validate question count
                    actual_count = len(data["questions"])
                    if actual_count < total_requested and attempt < max_retries:
                        print(f"Got {actual_count} questions, expected {total_requested}. Retrying...")
                        continue
                    
                    # Trim if we got too many
                    if actual_count > total_requested:
                        data["questions"] = data["questions"][:total_requested]
                
                # After all retries, supplement if still short
                final_questions = data.get("questions", [])
                actual_mcq = sum(1 for q in final_questions if q.get("type") in ["mcq", "mcq_multi"])
                actual_num = sum(1 for q in final_questions if q.get("type") == "numerical")
                
                # FORCE EXACT COUNT: If we're short, generate more questions
                missing_mcq = mcq_count - actual_mcq
                missing_num = numerical_count - actual_num
                
                if missing_mcq > 0 or missing_num > 0:
                    print(f"Supplementing: need {missing_mcq} more MCQs and {missing_num} more numericals")
                    # Recursive call for missing questions
                    supplement_result = await self.generate_questions_async(
                        subject=subject,
                        topic=topic,
                        mcq_count=max(missing_mcq, 0),
                        numerical_count=max(missing_num, 0),
                        level=level,
                        difficulty=difficulty
                    )
                    if supplement_result.get("success") and supplement_result.get("questions"):
                        final_questions.extend(supplement_result["questions"])
                        # Deduplicate again after supplementing
                        final_questions = self._deduplicate_questions(final_questions)
                
                return {
                    "success": True,
                    "subject": subject,
                    "topic": topic,
                    "questions": final_questions
                }
                
            except json.JSONDecodeError as e:
                if attempt < max_retries:
                    continue
                return {
                    "success": False,
                    "error": f"Failed to parse LLM response as JSON: {str(e)}",
                    "raw_response": response_text if response_text else None
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"LLM call failed: {str(e)}"
                }
        
        # If we get here, we exhausted retries
        return {
            "success": True,
            "subject": subject,
            "topic": topic,
            "questions": list(data.get("questions", []))
        }

    # ==================== HARD DIFFICULTY PROMPT GENERATOR ====================
    
    # Level normalization map — handles different naming conventions
    # Test portal uses JEE_MAINS, JEE_ADV; PDF generator uses JEE Mains, JEE Advanced
    LEVEL_ALIASES = {
        "JEE_MAINS": "JEE Mains",
        "JEE_ADV": "JEE Advanced",
        "Mains": "JEE Mains",
        "Advanced": "JEE Advanced",
        "NEET": "NEET",
        "GATE": "GATE",
        "Olympiad": "Olympiad",
        "CBSE Board": "CBSE Board",
        "CBSE": "CBSE Board",
        "CUSTOM": "JEE Mains",  # Default for custom tests
    }
    
    def _normalize_level(self, level: str) -> str:
        """Normalize level name to canonical form."""
        return self.LEVEL_ALIASES.get(level, level)
    
    def _get_hard_difficulty_prompt(self, total: int, level: str) -> str:
        """
        Returns a level-aware Hard difficulty prompt.
        JEE Advanced Hard ≠ CBSE Hard ≠ Olympiad Hard.
        """
        level = self._normalize_level(level)  # Normalize level name
        # Base hard instructions (always included)
        base = f"""DIFFICULTY: HARD — ABSOLUTE MAXIMUM DIFFICULTY (All {total} questions)
⚠️  CRITICAL: These must be the HARDEST possible questions. NOT medium-hard. NOT "slightly tricky". 
We mean GENUINELY BRUTAL problems that only the top 0.1% of students can solve.

MANDATORY REQUIREMENTS FOR EVERY HARD QUESTION:
- Minimum 5+ steps of non-trivial reasoning to reach the answer
- Must combine concepts from AT LEAST 3 different sub-topics or chapters
- The approach should NOT be immediately obvious — student must think laterally
- Calculations must be complex: systems of equations, integration, matrix methods, etc.
- A well-prepared student should need 8-15 minutes per question
- If a student can solve it in under 5 minutes with a single formula, it is NOT hard enough

ANTI-SIMPLIFICATION CHECK — your question FAILS if:
✘ It can be solved by direct formula substitution
✘ It only tests one concept
✘ The setup is a standard textbook problem with different numbers
✘ A coaching institute student would call it "easy marks"
✘ The solution is less than 4 steps"""

        # Level-specific additions
        level_specific = {
            "JEE Advanced": f"""
LEVEL CALIBRATION: IIT JEE ADVANCED PAPER 2 (Toughest questions only)
Think like a senior IIT professor setting Paper 2, Section C (the hardest section).

WHAT JEE ADVANCED HARD LOOKS LIKE:
- Paragraph-based problems where 2-3 questions share a complex physical/chemical/mathematical scenario
- Problems requiring insight that isn't taught in any textbook
- Setups where you must derive intermediate results before solving
- Questions where choosing the wrong approach leads to impossibly complex math
- Edge case problems where intuition fails and rigorous analysis is needed

PHYSICS EXAMPLES (this level of difficulty):
- "A charged particle enters a region with crossed E and B fields that vary as functions of position. The particle follows a specific trajectory. Find the work done by the electric field over one complete cycle."
- "A rigid body with a cavity containing fluid rotates about a tilted axis. Find the steady-state angular velocity considering viscous damping."
- "Two conducting spheres connected by a wire in a non-uniform external field — find the charge distribution and force between them."

MATHS EXAMPLES (this level of difficulty):
- "Find all continuous functions f: R→R satisfying f(x+y) = f(x)f(y) - sin(x)sin(y) for all x,y ∈ R"
- "A parabola and ellipse intersect at 4 points. A circle passes through all 4 intersection points. Prove the circle's center lies on a fixed line and find that line."
- "Evaluate ∫₀^π x·ln(sin x) dx using properties of definite integrals and series expansion"

CHEMISTRY EXAMPLES (this level of difficulty):
- "Predict the major product when a bridged bicyclic compound with 3 different functional groups undergoes a specific sequence of 4 reactions, justifying each stereochemical outcome."
- "Calculate the EMF of a cell involving a complex equilibrium with 3 simultaneous reactions and activity coefficients."
- "A mixture of 5 gases reaches equilibrium. Given Kp values for 3 independent reactions, find the partial pressure of each gas."

REMEMBER: JEE Advanced Hard means only 1-2% of JEE aspirants can solve these correctly.""",

            "Olympiad": f"""
LEVEL CALIBRATION: INTERNATIONAL OLYMPIAD (IMO / IPhO / IChO)
These are competition-level problems that require mathematical maturity beyond the syllabus.

WHAT OLYMPIAD HARD LOOKS LIKE:
- Problems requiring proof or construction, not just calculation
- Elegant problems with surprising solutions
- Problems where brute force doesn't work — you need a key insight
- Questions that connect seemingly unrelated areas of mathematics/physics
- Problems that professional mathematicians/physicists find interesting

PHYSICS (IPhO level):
- "Design an experiment using only a pendulum and ruler to measure the coefficient of restitution of a ball. Derive all equations from first principles."
- "A soap bubble of radius R contains a gas at temperature T. The bubble is illuminated by monochromatic light. Derive the condition for constructive interference as the bubble slowly evaporates."

MATHS (IMO level):
- "Find all functions f: Z⁺ → Z⁺ such that f(m²+n²) = f(m)²+f(n)² for all positive integers m, n."
- "Given n points in the plane, no three collinear, prove that the number of convex quadrilaterals is at most C(n,4). When does equality hold?"

CHEMISTRY (IChO level):
- "Propose a complete retrosynthetic analysis for a natural product with 5+ stereocenters, justifying each disconnection based on reactivity principles."

REMEMBER: Olympiad Hard means these could appear in an actual international competition.""",

            "JEE Mains": f"""
LEVEL CALIBRATION: JEE MAINS — HARDEST TIER (99.9+ percentile questions)
These are the questions that even JEE Mains toppers find time-consuming.

WHAT JEE MAINS HARD LOOKS LIKE:
- Multi-step problems combining 3+ concepts (NOT standard plug-and-chug)
- Tricky numerical answers that require careful substitution
- Problems with non-standard setups that test deep conceptual clarity
- Questions where most students pick the wrong approach
- Must require minimum 5-6 minutes even for well-prepared students

EXAMPLES:
- "A capacitor with a dielectric slab partially inserted is connected to a battery. Find the force on the dielectric as a function of its position, then find the equilibrium position."
- "Find the number of solutions of sin(x) = x/100 using graphical and analytical methods."
- "A thermodynamic cycle consists of an isothermal, adiabatic, and isochoric process. Given efficiency, find the ratio of volumes."

REMEMBER: These questions should make coaching students say "yeh tough tha".""",

            "NEET": f"""
LEVEL CALIBRATION: NEET — HARDEST TIER
These are the trickiest NEET questions requiring deep conceptual understanding.

WHAT NEET HARD LOOKS LIKE:
- Assertion-reason questions where the reasoning is non-obvious
- Application of concepts to unseen biological/medical scenarios
- Multi-step problems in Physics/Chemistry sections
- Questions requiring integration of multiple NCERT chapters
- Tricky exception-based questions in Biology

REMEMBER: These should stump even students who memorized the entire NCERT.""",

            "CBSE Board": f"""
LEVEL CALIBRATION: CBSE — HOTS (Higher Order Thinking Skills)
These are the toughest questions that appear in CBSE board examinations.

WHAT CBSE HARD LOOKS LIKE:
- Multi-concept application problems
- Case-study based questions requiring analysis
- Problems that require derivations combined with numerical application
- Cross-chapter integration questions

REMEMBER: These are the 5-mark questions that even board toppers find challenging.""",

            "GATE": f"""
LEVEL CALIBRATION: GATE — HARDEST TIER
These are the questions that differentiate AIR 1-100 from the rest.

WHAT GATE HARD LOOKS LIKE:
- Problems requiring deep mathematical analysis
- Multi-concept questions spanning multiple subjects
- Numerical answer questions with complex calculations
- Questions requiring derivation from first principles

REMEMBER: Only the top 0.1% of GATE aspirants should get these right."""
        }

        # Get level-specific prompt, default to JEE Advanced if not found
        specific = level_specific.get(level, level_specific.get("JEE Mains", ""))

        return base + specific

    def _get_system_message(self, subject: str, difficulty_label: str, level: str) -> str:
        """Level-aware system message for LLM calls."""
        level = self._normalize_level(level)
        if difficulty_label == "Hard":
            hard_personas = {
                "JEE Advanced": f"IIT professor setting JEE Advanced Paper 2 questions in {subject}. Only top 100 rankers solve these. Return ONLY valid JSON.",
                "Advanced":     f"IIT professor setting hardest JEE Advanced {subject} questions. Return ONLY valid JSON.",
                "Olympiad":     f"National Olympiad coach for {subject} (IMO/IPhO/IChO level). Return ONLY valid JSON.",
                "JEE Mains":    f"NTA JEE Mains setter — hardest 20% questions in {subject} for 99.9 percentile. Return ONLY valid JSON.",
                "NEET":         f"Senior NEET setter — trickiest conceptual {subject} questions beyond NCERT. Return ONLY valid JSON.",
                "GATE":         f"GATE setter from IISc/IIT — deep {subject} analysis questions. Return ONLY valid JSON.",
            }
            return hard_personas.get(level, f"Expert {subject} setter, extremely challenging problems. Return ONLY valid JSON.")
        return f"Expert {subject} question setter, {difficulty_label.upper()} difficulty. Return ONLY valid JSON."

    # ==================== PER-DIFFICULTY HELPER ====================
    async def _generate_batch_for_difficulty(
        self,
        subject: str,
        topic: str,
        mcq_count: int,
        numerical_count: int,
        level: str,
        difficulty_label: str,
        level_prompt: str,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Generate questions for a SINGLE difficulty level (Easy/Medium/Hard).
        Returns a list of question dicts, each stamped with 'difficulty' field.
        """
        import random
        total = mcq_count + numerical_count
        if total <= 0:
            return []

        # ---- Load JEE Archive reference context for this topic ----
        # This injects real JEE Mains 2025/2026 questions as few-shot examples
        # so the LLM calibrates difficulty and question style correctly.
        try:
            from services.jee_reference_loader import get_reference_context
            jee_reference = get_reference_context(topic=topic, subject=subject, max_chars=3000)
        except Exception:
            jee_reference = ""


        # SUB-BATCH STRATEGY: If total > 7, split into parallel sub-batches
        # Each sub-batch requests at most 7 questions to avoid LLM truncation
        MAX_PER_CALL = 5
        if total > MAX_PER_CALL:
            import asyncio as _sub_asyncio
            sub_batches = []
            remaining = total
            # Split MCQ and Numerical proportionally across sub-batches
            mcq_left = mcq_count
            num_left = numerical_count
            batch_idx = 0
            while remaining > 0:
                chunk = min(MAX_PER_CALL, remaining)
                # Proportional split for this chunk
                if total > 0:
                    c_mcq = min(mcq_left, round(mcq_count * chunk / total))
                    c_num = chunk - c_mcq
                    if c_num > num_left:
                        c_num = num_left
                        c_mcq = chunk - c_num
                else:
                    c_mcq, c_num = chunk, 0
                c_mcq = max(0, min(c_mcq, mcq_left))
                c_num = max(0, min(c_num, num_left))
                # Ensure chunk is filled
                actual_chunk = c_mcq + c_num
                if actual_chunk < chunk:
                    if mcq_left > c_mcq:
                        c_mcq += min(chunk - actual_chunk, mcq_left - c_mcq)
                    elif num_left > c_num:
                        c_num += min(chunk - actual_chunk, num_left - c_num)
                sub_batches.append((c_mcq, c_num))
                mcq_left -= c_mcq
                num_left -= c_num
                remaining -= (c_mcq + c_num)
                batch_idx += 1

            print(f"[{difficulty_label}] Splitting {total} into {len(sub_batches)} sub-batches: {sub_batches}")

            # Run sub-batches SEQUENTIALLY to avoid rate limits
            combined = []
            for sb_mcq, sb_num in sub_batches:
                if sb_mcq + sb_num > 0:
                    try:
                        sr = await self._generate_batch_for_difficulty(
                            subject=subject, topic=topic,
                            mcq_count=sb_mcq, numerical_count=sb_num,
                            level=level, difficulty_label=difficulty_label,
                            level_prompt=level_prompt, **kwargs
                        )
                        if isinstance(sr, list):
                            combined.extend(sr)
                    except Exception as e:
                        print(f"[{difficulty_label}] Sub-batch failed: {e}")
            return combined

        # Small batch (<=7): request exact count + 1 extra for safety
        request_total = total + 1

        # Difficulty-specific instructions — these are much more descriptive
        # than a single line, forcing the LLM to truly calibrate
        difficulty_descriptions = {
            "Easy": f"""DIFFICULTY: EASY (Generate {request_total} questions, ALL must be EASY)
WHAT EASY MEANS — follow these rules strictly:
- Direct formula application with ONE step of calculation
- The student should be able to solve each question in under 2 minutes
- No hidden traps, no multi-concept integration
- Values should be simple integers (not complex decimals)
- Standard textbook-style questions that test basic understanding
- Example calibration: "A ball is thrown upward with velocity 20 m/s. Find max height." (single formula: h = v²/2g)
- DO NOT make these conceptually tricky. These should be confidence-builders.""",

            "Medium": f"""DIFFICULTY: MEDIUM (Generate {request_total} questions, ALL must be MEDIUM)
WHAT MEDIUM MEANS — follow these rules strictly:
- Requires 2-3 steps of reasoning, NOT just plug-and-chug
- Combines 2 concepts from the topic (e.g., energy conservation + kinematics)
- Moderate calculations — may involve fractions or decimals
- The student should need 3-5 minutes per question
- Should require some critical thinking but no unusual tricks
- Example calibration: "A block slides down a rough incline of angle 30° and length 2m. If μ=0.2, find the speed at the bottom."
- These should be standard competitive exam level questions.""",

            "Hard": self._get_hard_difficulty_prompt(request_total, level)
        }

        diff_instruction = difficulty_descriptions.get(difficulty_label, difficulty_descriptions["Medium"])

        # Temperature varies by difficulty for better results
        temp_map = {"Easy": 0.5, "Medium": 0.7, "Hard": 0.95}
        temperature = temp_map.get(difficulty_label, 0.7)

        # Build the prompt for this difficulty batch
        num_msq = kwargs.get("num_msq", 0) or 0
        # Scale multi-correct proportionally to this batch
        if mcq_count > 0 and num_msq > 0:
            original_mcq = kwargs.get("_original_mcq_count", mcq_count)
            batch_msq = max(0, round(num_msq * mcq_count / original_mcq)) if original_mcq > 0 else 0
        else:
            batch_msq = 0
        batch_single = max(0, mcq_count - batch_msq)

        # Construct breakdown
        req_list = []
        if batch_single > 0:
            req_list.append(f"- {batch_single} Single Correct MCQs (Type: 'mcq')")
        if batch_msq > 0:
            req_list.append(f"- {batch_msq} Multiple Correct MCQs (Type: 'mcq_multi', one or more correct options)")
        if numerical_count > 0:
            req_list.append(f"- {numerical_count} Numerical Type Questions (Type: 'numerical')")
        req_str = "\n".join(req_list)

        # Numerical answer instruction
        if level in ("JEE Mains", "Mains"):
            num_ans_inst = "NUMERICAL ANSWERS: Must be INTEGERS ONLY (0-999). NO decimals."
        else:
            num_ans_inst = "NUMERICAL ANSWERS: Must be integers or decimals. NO formulas."

        # ---- NTA-STYLE DIAGRAM INSTRUCTION ----
        # Chapters that commonly need diagrams (used to decide when to add SVG)
        DIAGRAM_CHAPTERS = [
            # Physics
            "optics", "lens", "mirror", "prism", "refraction", "reflection",
            "circuit", "resistor", "capacitor", "current", "kirchhoff",
            "mechanics", "block", "pulley", "incline", "projectile", "free body",
            "wave", "interference", "diffraction", "em wave", "field line",
            "magnetic", "lorentz", "ray", "snell",
            # Maths
            "parabola", "ellipse", "hyperbola", "circle", "graph", "coordinate",
            "triangle", "polygon", "vector", "angle", "area",
            # Chemistry
            "apparatus", "distillation", "titration", "cell", "electrolysis",
            "organic", "structural", "benzene", "reaction vessel",
            # Biology
            "cell", "organelle", "heart", "kidney", "neuron", "plant", "anatomy",
        ]
        topic_lower = topic.lower()
        subject_lower = subject.lower()
        needs_diagrams = any(kw in topic_lower or kw in subject_lower for kw in DIAGRAM_CHAPTERS)

        if needs_diagrams:
            diagram_instruction = """

DIAGRAM RULES (IMPORTANT):
- If a question cannot be understood without a figure, add a "diagram_svg" field with a compact NTA-style SVG.
- NTA Style: black strokes only (#000), white background, no CSS classes, no external fonts.
- Use only: <line>, <circle>, <rect>, <path>, <text>, <arrow>, <polyline>. viewBox="0 0 400 280".
- Label key parts with <text font-family="Arial" font-size="12">.
- Keep SVG under 2500 characters. Start SVG with: <svg viewBox="0 0 400 280" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="#000" stroke-width="1.5">
- For questions that need NO diagram (pure calculation, theory), OMIT the "diagram_svg" field entirely.

EXAMPLE 1 (Convex Lens Ray Diagram):
"diagram_svg": "<svg viewBox='0 0 400 280' xmlns='http://www.w3.org/2000/svg' fill='none' stroke='#000' stroke-width='1.5'><line x1='200' y1='20' x2='200' y2='260'/><ellipse cx='200' cy='140' rx='15' ry='90' fill='#eef'/><line x1='20' y1='140' x2='380' y2='140'/><line x1='60' y1='80' x2='60' y2='180' stroke-width='2'/><text x='62' y='78' font-family='Arial' font-size='11' fill='#000'>O</text><line x1='60' y1='80' x2='240' y2='210' stroke='#c00'/><line x1='60' y1='80' x2='380' y2='80' stroke='#090'/><text x='185' y='18' font-family='Arial' font-size='11'>Principal Axis</text><text x='120' y='135' font-family='Arial' font-size='11'>F</text><text x='275' y='135' font-family='Arial' font-size='11'>F</text></svg>"

EXAMPLE 2 (Simple Resistor Circuit):
"diagram_svg": "<svg viewBox='0 0 400 280' xmlns='http://www.w3.org/2000/svg' fill='none' stroke='#000' stroke-width='1.5'><rect x='50' y='110' width='300' height='60' rx='4'/><line x1='50' y1='140' x2='20' y2='140'/><line x1='350' y1='140' x2='380' y2='140'/><rect x='155' y='120' width='90' height='40' fill='white'/><text x='185' y='145' font-family='Arial' font-size='12' fill='#000'>R</text><text x='15' y='155' font-family='Arial' font-size='11'>+</text><text x='370' y='155' font-family='Arial' font-size='11'>-</text><text x='180' y='105' font-family='Arial' font-size='11'>Battery</text></svg>"

EXAMPLE 3 (Parabola Graph):
"diagram_svg": "<svg viewBox='0 0 400 280' xmlns='http://www.w3.org/2000/svg' fill='none' stroke='#000' stroke-width='1.5'><line x1='40' y1='140' x2='360' y2='140'/><line x1='200' y1='260' x2='200' y2='20'/><path d='M 80 240 Q 200 40 320 240' stroke='#00c' fill='none' stroke-width='2'/><text x='355' y='145' font-family='Arial' font-size='12'>x</text><text x='205' y='18' font-family='Arial' font-size='12'>y</text><text x='200' y='155' font-family='Arial' font-size='11'>O</text><text x='130' y='110' font-family='Arial' font-size='11' fill='#00c'>y=ax&#178;</text></svg>"
"""
        else:
            diagram_instruction = ""

        # Single strict prompt
        # Build JEE reference block (only when real archive data is available)
        if jee_reference:
            ref_block = f"""
REAL JEE MAINS 2025/2026 REFERENCE QUESTIONS FOR {topic.upper()}:
(Study these real exam questions to calibrate difficulty, phrasing and diagram style EXACTLY)
---
{jee_reference}
---
IMPORTANT: Generate NEW original questions at the SAME difficulty and style as the real JEE questions above.
Do NOT copy any question verbatim. Use them only as style and difficulty reference.
"""
        else:
            ref_block = ""

        prompt = f"""You are an expert question paper setter for competitive exams like FIITJEE, Allen, Resonance.

{diff_instruction}

GENERATE EXACTLY:
{req_str}

SUBJECT: {subject}
TOPIC: {topic}
EXAM LEVEL: {level_prompt}
{ref_block}{diagram_instruction}
STRICT REQUIREMENTS:
1. You MUST generate EXACTLY {request_total} questions. Do NOT stop early.
2. Every question MUST be {difficulty_label.upper()} difficulty as defined above.
3. {num_ans_inst}
4. Use LaTeX math mode: $...$ for inline, $$...$$ for display equations.
5. Provide a "solution" for EVERY question.
   - For each question, write a CONCISE solution (3-5 steps, 50-80 words).
   - Use \\\\textbf{{Step 1:}} format.
   - End with \\\\textbf{{Final Answer:}} Option X or value.
   - Keep solutions SHORT so you can generate ALL {request_total} questions.
6. For mcq_multi: answer as "A, C" or "A, B, D".


Return EXACTLY this JSON format:
{{"questions": [
  {{"type": "mcq", "text": "...", "options": ["A","B","C","D"], "answer": "A", "difficulty": "{difficulty_label.lower()}", "solution": "..."}},
  {{"type": "mcq", "text": "A convex lens of focal length 20 cm...", "options": ["A","B","C","D"], "answer": "B", "difficulty": "{difficulty_label.lower()}", "solution": "...", "diagram_svg": "<svg viewBox='0 0 400 280' ...>...</svg>"}},
  {{"type": "numerical", "text": "...", "answer": "42", "difficulty": "{difficulty_label.lower()}", "solution": "..."}}
]}}
"""

        # Anti-repetition
        past_questions = kwargs.get("past_questions")
        if past_questions and len(past_questions) > 0:
            past_qs_formatted = "\n".join([f"{i+1}. {q[:200]}" for i, q in enumerate(past_questions[:30])])
            prompt += f"\n\nAVOID REPETITION — do NOT generate questions similar to:\n{past_qs_formatted}\n"

        # SINGLE LLM call — no full retries
        try:
            print(f"[{difficulty_label}] Requesting EXACTLY {request_total} questions from LLM...")
            # Use a higher max_tokens to ensure the LLM has enough room to finish
            response = await litellm.acompletion(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_message(subject, difficulty_label, level)},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=32768
            )

            import asyncio as _asyncio
            _asyncio.create_task(self._log_usage(
                response, feature="question_gen",
                user_id=kwargs.get("user_id"),
                subject=subject, level=level
            ))
            response_text = response.choices[0].message.content or ""  # type: ignore[union-attr]
            cleaned_json = self._clean_json_response(response_text)
            data = json.loads(cleaned_json)

            if "questions" not in data:
                print(f"[{difficulty_label}] No 'questions' key in response")
                return []

            questions = self._process_questions(data["questions"])
            questions = self._deduplicate_questions(questions)

            # Stamp difficulty on each question
            for q in questions:
                q["difficulty"] = difficulty_label.lower()

            # Trim to EXACT count needed (we over-requested)
            if len(questions) > total:
                import random
                random.shuffle(questions)  # Shuffle before trimming for variety
                questions = questions[:total]
            
            if len(questions) < total:
                print(f"[{difficulty_label}] WARNING: Got {len(questions)}/{total} even after over-requesting {request_total}. No top-up call — accepting what we have.")

            print(f"[{difficulty_label}] Final: {len(questions)}/{total} questions (requested {request_total} from LLM)")
            return questions

        except json.JSONDecodeError as e:
            print(f"[{difficulty_label}] JSON parse failed: {e}")
            # TRUNCATED JSON REPAIR: Try to salvage questions from partial response
            try:
                salvaged = self._repair_truncated_json(cleaned_json)
                if salvaged:
                    salvaged_qs = self._process_questions(salvaged)
                    for q in salvaged_qs:
                        q["difficulty"] = difficulty_label.lower()
                    print(f"[{difficulty_label}] Salvaged {len(salvaged_qs)} questions from truncated JSON")
                    return salvaged_qs
            except Exception as repair_err:
                print(f"[{difficulty_label}] JSON repair also failed: {repair_err}")
            return []
        except Exception as e:
            print(f"[{difficulty_label}] LLM call failed: {e}")
            return []

    async def generate_questions_async(
        self,
        subject: str,
        topic: str,
        mcq_count: int,
        numerical_count: int,
        level: str = "JEE Mains",
        difficulty: str = "Medium",
        **kwargs
    ) -> Dict[str, Any]:
        """
        ASYNC version of generate_questions using litellm.acompletion.
        Allows true parallel execution when used with asyncio.gather.
        """
        # Normalize level string from API formats (e.g. "JEE_MAINS") to standard prompts (e.g. "JEE Mains")
        level = self._normalize_level(level)
        
        total_requested = mcq_count + numerical_count
        
        # Get difficulty percentages from kwargs (default: 20-50-30)
        easy_percent = kwargs.get('easy_percent', 20)
        medium_percent = kwargs.get('medium_percent', 50)
        hard_percent = kwargs.get('hard_percent', 30)
        
        # Calculate exact counts for each difficulty level
        easy_count = max(1, round(total_requested * easy_percent / 100)) if easy_percent > 0 else 0
        hard_count = max(1, round(total_requested * hard_percent / 100)) if hard_percent > 0 else 0
        medium_count = total_requested - easy_count - hard_count
        if medium_count < 0:
            medium_count = 0
            if easy_count > hard_count:
                easy_count = total_requested - hard_count
            else:
                hard_count = total_requested - easy_count
        
        # Build difficulty distribution prompt with EXACT COUNTS
        difficulty_prompt = f"""DIFFICULTY DISTRIBUTION (STRICT):
Generate EXACTLY:
- {easy_count} EASY questions: Straightforward, simple calculations
- {medium_count} MEDIUM questions: Standard exam-level, 2-3 step problems
- {hard_count} HARD questions: Challenging, multi-step with conceptual twists
TOTAL: {total_requested} questions. This is MANDATORY."""
        
        # Level prompts (simplified for async)
        level_prompts = {
            "CBSE Board": "CBSE/State Board Level - Direct application. Use [DIAGRAM: description] for questions needing figures.",
            "JEE Mains": "JEE Main Level - Application-based. Use [DIAGRAM: description] for Optics/Mechanics/Circuits.",
            "Mains": "JEE Main Level - Application-based. Use [DIAGRAM: description] for Optics/Mechanics/Circuits.",
            "JEE Advanced": "JEE Advanced Level - Multi-concept. Use [DIAGRAM: description] where relevant.",
            "Advanced": "JEE Advanced Level - Multi-concept. Use [DIAGRAM: description] where relevant.",
            "Olympiad": "Olympiad Level - Research-level. Use [DIAGRAM: description] for geometry/physics setups.",
            "NEET": "NEET Level - Biology/Medical focus. Use [DIAGRAM: description] for Biology/Anatomy questions.",
            "GATE": "GATE Level - High conceptual depth. Use [DIAGRAM: description] for circuits/structures."
        }
        level_prompt = level_prompts.get(level, level_prompts.get("JEE Mains"))
        
        # Special handling for CBSE Board - generate CBSE pattern questions
        if level == "CBSE Board":
            total_cbse_theory = mcq_count
            total_numericals = numerical_count
            
            # Check if specific counts were provided via kwargs
            if kwargs.get('cbse_vsa') is not None:
                mcq_cbse_count = kwargs.get('cbse_mcq') or 0
                vsa_count = kwargs.get('cbse_vsa')
                sa_count = kwargs.get('cbse_sa') or 0
                la_count = kwargs.get('cbse_la') or 0
                case_count = kwargs.get('cbse_case') or 0
                print(f"[DEBUG] Using explicit CBSE Board counts: MCQ={mcq_cbse_count}, VSA={vsa_count}, SA={sa_count}, LA={la_count}, Case={case_count}")
            elif total_cbse_theory > 0:
                mcq_cbse_count = max(1, int(total_cbse_theory * 0.25))
                vsa_count = max(1, int(total_cbse_theory * 0.3))
                sa_count = max(1, int(total_cbse_theory * 0.25))
                la_count = max(1, int(total_cbse_theory * 0.1))
                case_count = max(0, total_cbse_theory - mcq_cbse_count - vsa_count - sa_count - la_count)
            else:
                mcq_cbse_count = 0
                vsa_count = 0
                sa_count = 0
                la_count = 0
                case_count = 0
            
            prompt = f"""You are a CBSE Board exam setter. Generate CBSE pattern questions.

SUBJECT: {subject}
TOPIC: {topic}
{difficulty_prompt}

GENERATE EXACTLY:
- {mcq_cbse_count} MCQs (1 mark each, type: "mcq", 4 options A/B/C/D, one correct answer)
- {vsa_count} Very Short Answer (1-2 marks, type: "short_answer", marks: 1 or 2)
- {sa_count} Short Answer (2-3 marks, type: "short_answer", marks: 2 or 3)
- {la_count} Long Answer (5 marks, type: "long_answer", marks: 5)
- {case_count} Case-Based (4 marks, type: "case_based" with passage and 4 sub_questions)
- {total_numericals} Numerical (3-5 marks, type: "numerical", marks: 3 or 5)

Use LaTeX: $F = ma$, $\\\\frac{{a}}{{b}}$

REQUIREMENTS FOR SOLUTIONS:
- Provide DETAILED STEP-BY-STEP SOLUTIONS for every question in the "solution" field.
- DO NOT WRITE HUGE PARAGRAPHS using continuous text.
- Use \\textbf{{Step 1:}} format or bullet points.
- INSERT DOUBLE NEWLINE (\\n\\n) BETWEEN STEPS/POINTS.
- Ensure each step starts on a new line.
- Center ALL equations using $$...$$ display math.

Return ONLY JSON:
{{
  "questions": [
  {{"type": "mcq", "marks": 1, "text": "Which of the following is correct?", "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"], "answer": "B", "solution": "The correct answer is B because..."}},
  {{"type": "short_answer", "marks": 2, "text": "Define electric flux.", "answer": "Electric flux is...", "solution": "\\textbf{{Step 1:}} Electric flux is defined as... \\n\\n\\textbf{{Step 2:}} It is a scalar quantity..."}},
  {{"type": "long_answer", "marks": 5, "text": "State and prove Gauss's law.", "answer": "Gauss's law states...", "solution": "\\textbf{{Step 1:}} Statement: The total electric flux... \\n\\n\\textbf{{Proof:}} Consider a sphere..."}},
  {{"type": "case_based", "marks": 4, "passage": "EM induction paragraph...", "sub_questions": [
    {{"text": "Q1?", "options": ["A", "B", "C", "D"], "answer": "B"}},
    {{"text": "Q2?", "options": ["A", "B", "C", "D"], "answer": "C"}},
    {{"text": "Q3?", "options": ["A", "B", "C", "D"], "answer": "A"}},
    {{"text": "Q4?", "options": ["A", "B", "C", "D"], "answer": "D"}}
  ], "answer": "B, C, A, D", "solution": "1) Explanation for Q1... \\n\\n2) Explanation for Q2..."}},
  {{"type": "numerical", "marks": 3, "text": "Find resistance...", "answer": "5", "solution": "\\textbf{{Step 1:}} Given V=10V, I=2A... \\n\\n\\textbf{{Step 2:}} By Ohm's law, R = V/I = 5 Ohms"}}
]
}}
"""
            # ---- CBSE: Send prompt to LLM ----
            max_retries = 1
            for attempt in range(max_retries + 1):
                try:
                    response = await litellm.acompletion(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": f"Expert CBSE Board {subject} question setter. Return ONLY valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7
                    )
                    import asyncio as _asyncio
                    _asyncio.create_task(self._log_usage(
                        response, feature="question_gen",
                        user_id=kwargs.get("user_id"),
                        subject=subject, level=level
                    ))
                    response_text = response.choices[0].message.content or ""  # type: ignore[union-attr]
                    cleaned_json = self._clean_json_response(response_text)
                    data = json.loads(cleaned_json)
                    if "questions" in data:
                        data["questions"] = self._process_questions(data["questions"])
                        data["questions"] = self._deduplicate_questions(data["questions"])
                        if len(data["questions"]) > total_requested:
                            data["questions"] = data["questions"][:total_requested]
                    return {
                        "success": True,
                        "subject": subject,
                        "topic": topic,
                        "questions": data.get("questions", [])
                    }
                except Exception as e:
                    if attempt < max_retries:
                        continue
                    return {"success": False, "error": f"CBSE LLM call failed: {str(e)}"}
            return {"success": True, "subject": subject, "topic": topic, "questions": []}

        elif level == "GATE":
            gate_paper = kwargs.get("gate_paper", "CSE")
            gate_subset = kwargs.get("gate_subset", "ALL")  # NEW: Support partial generation
            
            num_msq = kwargs.get("num_msq", 0)
            num_nat = kwargs.get("num_nat", 0)
            num_ga = kwargs.get("num_ga", 0)
            num_mcq = mcq_count
            
            # Adjust counts based on subset
            if gate_subset == "GA":
                prompt_type = f"{num_ga} General Aptitude (GA) Questions"
                req_list = f"- {num_ga} General Aptitude (GA) Questions (Verbal/Quant)"
                total_q = num_ga
            elif gate_subset == "MCQ":
                prompt_type = f"{num_mcq} MCQs (Single Correct)"
                req_list = f"- {num_mcq} MCQs (Single Correct) on Core Subject"
                total_q = num_mcq
            elif gate_subset == "MSQ":
                prompt_type = f"{num_msq} MSQs (Multiple Select)"
                req_list = f"- {num_msq} MSQs (Multiple Select) on Core Subject (type: \"mcq_multi\")"
                total_q = num_msq
            elif gate_subset == "NAT":
                prompt_type = f"{num_nat} NATs (Numerical Answer)"
                req_list = f"- {num_nat} NATs (Numerical Answer) on Core Subject (type: \"numerical\")"
                total_q = num_nat
            else:
                # Default ALL
                prompt_type = "GATE pattern questions"
                req_list = f"""- {num_ga} General Aptitude (GA) Questions (Verbal/Quant)
- {num_mcq} MCQs (Single Correct) on Core Subject
- {num_msq} MSQs (Multiple Select) on Core Subject (type: "mcq_multi")
- {num_nat} NATs (Numerical Answer) on Core Subject (type: "numerical")"""
                total_q = num_ga + num_mcq + num_msq + num_nat

            prompt = f"""You are a GATE Exam Setter for {gate_paper}. Generate {prompt_type}.

SUBJECT: {gate_paper} (GATE)
TOPIC: {topic}
{difficulty_prompt}

GENERATE EXACTLY:
{req_list}

TOTAL: {total_q} Questions

Use LaTeX: $...$

Return ONLY JSON:
{{"questions": ["""
            # ---- GATE: Send prompt to LLM ----
            max_retries = 1
            for attempt in range(max_retries + 1):
                try:
                    response = await litellm.acompletion(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": f"Expert GATE {gate_paper} question setter. Return ONLY valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7
                    )
                    import asyncio as _asyncio
                    _asyncio.create_task(self._log_usage(
                        response, feature="question_gen",
                        user_id=kwargs.get("user_id"),
                        subject=subject, level=level
                    ))
                    response_text = response.choices[0].message.content or ""  # type: ignore[union-attr]
                    cleaned_json = self._clean_json_response(response_text)
                    data = json.loads(cleaned_json)
                    if "questions" in data:
                        data["questions"] = self._process_questions(data["questions"])
                        data["questions"] = self._deduplicate_questions(data["questions"])
                    return {
                        "success": True,
                        "subject": subject,
                        "topic": topic,
                        "questions": data.get("questions", [])
                    }
                except Exception as e:
                    if attempt < max_retries:
                        continue
                    return {"success": False, "error": f"GATE LLM call failed: {str(e)}"}
            return {"success": True, "subject": subject, "topic": topic, "questions": []}

        else:
            # ============== PER-DIFFICULTY GENERATION (3 separate calls) ==============
            import random
            print(f"[PER-DIFFICULTY] Generating {easy_count} Easy + {medium_count} Medium + {hard_count} Hard = {total_requested} questions")

            # Split MCQ and Numerical counts proportionally per difficulty
            def split_counts(total_mcq, total_num, diff_count, total_all):
                """Split MCQ and Numerical proportionally for a difficulty bucket."""
                if total_all == 0:
                    return 0, 0
                ratio = diff_count / total_all
                d_mcq = round(total_mcq * ratio)
                d_num = round(total_num * ratio)
                # Ensure at least 1 MCQ if we have MCQs to distribute
                if d_mcq == 0 and diff_count > 0 and total_mcq > 0:
                    d_mcq = 1
                if d_num == 0 and diff_count > 0 and total_num > 0:
                    d_num = 1
                return d_mcq, d_num

            e_mcq, e_num = split_counts(mcq_count, numerical_count, easy_count, total_requested)
            h_mcq, h_num = split_counts(mcq_count, numerical_count, hard_count, total_requested)
            # Medium gets the remainder to ensure totals match exactly
            m_mcq = mcq_count - e_mcq - h_mcq
            m_num = numerical_count - e_num - h_num
            # Clamp negatives
            if m_mcq < 0: m_mcq = 0
            if m_num < 0: m_num = 0

            print(f"[PER-DIFFICULTY] Easy: {e_mcq}M+{e_num}N, Medium: {m_mcq}M+{m_num}N, Hard: {h_mcq}M+{h_num}N")

            # Pass original MCQ count so the helper can scale MSQ proportionally
            batch_kwargs = {**kwargs, "_original_mcq_count": mcq_count}

            all_questions = []

            # Run difficulty batches in PARALLEL for faster generation
            _lp: str = level_prompt or "JEE Mains"
            difficulty_batches = []
            if easy_count > 0:
                difficulty_batches.append(("Easy", e_mcq, e_num))
            if medium_count > 0:
                difficulty_batches.append(("Medium", m_mcq, m_num))
            if hard_count > 0:
                difficulty_batches.append(("Hard", h_mcq, h_num))

            import asyncio as _diff_asyncio

            async def _run_difficulty_batch(diff_label, d_mcq, d_num):
                try:
                    batch_result = await self._generate_batch_for_difficulty(
                        subject=subject, topic=topic,
                        mcq_count=d_mcq, numerical_count=d_num,
                        level=level, difficulty_label=diff_label,
                        level_prompt=_lp, **batch_kwargs
                    )
                    if isinstance(batch_result, list):
                        print(f"[PER-DIFFICULTY] {diff_label} batch done: {len(batch_result)} questions")
                        return batch_result
                    else:
                        print(f"[PER-DIFFICULTY] {diff_label} batch returned unexpected type")
                        return []
                except Exception as batch_err:
                    print(f"[PER-DIFFICULTY] {diff_label} batch FAILED: {batch_err}")
                    return []

            # Run ALL difficulty batches in parallel (Easy + Medium + Hard simultaneously)
            batch_tasks = [_run_difficulty_batch(dl, dm, dn) for dl, dm, dn in difficulty_batches]
            batch_results = await _diff_asyncio.gather(*batch_tasks)
            for result in batch_results:
                all_questions.extend(result)

            # Deduplicate across all batches
            all_questions = self._deduplicate_questions(all_questions)

            # TOP-UP LOOP: Keep making small API calls until we hit exact count
            top_up_attempts = 0
            max_top_ups = 3  # Up to 3 retry rounds (reduced to limit cascading)
            while len(all_questions) < total_requested and top_up_attempts < max_top_ups:
                deficit = total_requested - len(all_questions)
                # Cap each top-up request at 5 to keep it small and reliable
                batch_size = min(deficit, 5)
                print(f"[TOP-UP] Need {deficit} more, requesting {batch_size} (attempt {top_up_attempts + 1}/{max_top_ups})")
                try:
                    top_up_qs = await self._generate_batch_for_difficulty(
                        subject=subject, topic=topic,
                        mcq_count=batch_size, numerical_count=0,
                        level=level, difficulty_label="Medium",
                        level_prompt=_lp, **batch_kwargs
                    )
                    if top_up_qs:
                        all_questions.extend(top_up_qs)
                        all_questions = self._deduplicate_questions(all_questions)
                        print(f"[TOP-UP] Got {len(top_up_qs)} more, total now: {len(all_questions)}")
                    else:
                        print(f"[TOP-UP] Got 0 questions, retrying...")
                except Exception as top_up_err:
                    print(f"[TOP-UP] Failed: {top_up_err}")
                top_up_attempts += 1

            # Shuffle so Easy/Medium/Hard aren't grouped together
            random.shuffle(all_questions)

            # Trim if we got too many
            if len(all_questions) > total_requested:
                all_questions = all_questions[:total_requested]

            print(f"[PER-DIFFICULTY] Final total: {len(all_questions)} questions")

            return {
                "success": True,
                "subject": subject,
                "topic": topic,
                "questions": all_questions
            }



    async def verify_numerical_batch_async(self, questions: List[Dict[str, str]], subject: str) -> List[Dict[str, Any]]:
        """
        Verify a batch of numerical questions in a single LLM call.
        Reduces API calls by 5x (verifying 5-10 questions at once).
        """
        import asyncio
        import json
        
        if not questions:
            return []
            
        # Prepare batch prompt
        items_str = ""
        for i, q in enumerate(questions):
            items_str += f"""
ITEM {i+1}:
Question: {q['text']}
Proposed Answer: {q['answer']}
"""

        prompt = f"""You are an expert {subject} teacher. Verify these {len(questions)} numerical questions.
Solve each one step-by-step and check if the proposed answer is correct.

{items_str}

Return a single JSON object with a "verifications" array:
{{
  "verifications": [
    {{
      "item_id": 1,
      "verified_answer": "5",
      "matches": true,
      "solution": "\\\\textbf{{Solution:}} ...step by step..."
    }},
    {{
      "item_id": 2,
      "verified_answer": "10.5", 
      "matches": false,
      "solution": "\\\\textbf{{Correction:}} ...calculation..."
    }}
  ]
}}

RULES:
1. Verify strictly. Precision matters.
2. If the proposed answer matches your calculation, set "matches": true.
3. If valid range (e.g. 5.1 vs 5.12), treat as match.
4. "verified_answer" should be the correct numerical value.
5. "solution" should be a short LaTeX explanation.
"""
        
        try:
            response = await litellm.acompletion(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Batch Verification Agent. Return JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            import asyncio as _asyncio
            _asyncio.create_task(self._log_usage(
                response, feature="verify_numerical",
                user_id=self._current_user_id,
                subject=subject
            ))
            response_text = response.choices[0].message.content or ""  # type: ignore[union-attr]
            cleaned = self._clean_json_response(response_text)
            data = json.loads(cleaned)
            
            results = []
            verifs = data.get("verifications", [])
            
            # Map back to original order
            # Create a map by item_id
            verif_map = {v.get("item_id"): v for v in verifs}
            
            for i in range(len(questions)):
                item_id = i + 1
                verif = verif_map.get(item_id)
                
                if verif:
                    results.append({
                        "success": True,
                        "original_answer": questions[i]['answer'],
                        "verified_answer": str(verif.get("verified_answer")),
                        "matches": verif.get("matches"),
                        "solution": verif.get("solution")
                    })
                else:
                    # Fallback if specific item missing
                    results.append({
                        "success": False,
                        "error": "Item missing in batch response",
                        "matches": True
                    })
            
            return results
            
        except Exception as e:
            print(f"Batch verification failed: {e}")
            # Fallback: mark all as verified/matching to avoid breaking flow
            return [{"success": False, "matches": True, "error": str(e)} for _ in questions]

    async def generate_questions_with_verification_async(
        self,
        subject: str,
        topic: str,
        mcq_count: int,
        numerical_count: int,
        level: str = "JEE Mains",
        difficulty: str = "Medium",
        include_solutions: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate questions and verify numerical answers in PARALLEL.
        If include_solutions=True, also generate solutions for MCQs.
        """
        # Generate a unique ID for this entire generation session
        import uuid
        self._current_generation_id = str(uuid.uuid4())
        # Store user_id for verify/solution log calls
        self._current_user_id = kwargs.get("user_id")
        # First, generate questions normally
        result = await self.generate_parallel(subject, topic, mcq_count, numerical_count, level, difficulty, **kwargs)
        
        if not result.get("success"):
            return result
        
        questions = result.get("questions", [])
        
        # Run verifications in BATCHES (Chunk size 5)
        # Identify numerical questions
        numerical_qs = []
        numerical_indices = []
        
        for i, q in enumerate(questions):
            if q.get("type") == "numerical":
                numerical_indices.append(i)
                numerical_qs.append({
                    "text": q.get("text", ""),
                    "answer": str(q.get("answer", ""))
                })
        
        if numerical_qs:
            # Create chunks of 10 (optimized for Gemini 3.0 Flash large context)
            chunk_size = 10
            batches = [numerical_qs[i:i + chunk_size] for i in range(0, len(numerical_qs), chunk_size)]
            
            # Create batch tasks
            batch_tasks = []
            for batch in batches:
                batch_tasks.append(self.verify_numerical_batch_async(batch, subject))
            
            # Run batches in parallel
            batch_results_list = await asyncio.gather(*batch_tasks)
            
            # Flatten results
            all_verification_results = []
            for res_list in batch_results_list:
                all_verification_results.extend(res_list)
            
            verified_count: int = 0
            corrected_count: int = 0
            
            # Apply results
            for i, verif_result in enumerate(all_verification_results):
                if i >= len(numerical_indices): break # Safety check
                
                q_index = numerical_indices[i]
                q = questions[q_index]
                
                if isinstance(verif_result, dict) and verif_result.get("success"):
                    verified_count += 1
                    if not verif_result.get("matches"):
                        # Answer mismatch - use verified answer
                        q["original_answer"] = q.get("answer")
                        q["answer"] = verif_result.get("verified_answer")
                        q["answer_corrected"] = True
                        q["solution"] = verif_result.get("solution")
                        corrected_count += 1
                    else:
                        q["answer_verified"] = True
                        q["solution"] = verif_result.get("solution")
            
            result["verification_stats"] = {
                "total_numerical": numerical_count,
                "verified": verified_count,
                "corrected": corrected_count
            }
        else:
            result["verification_stats"] = {
                "total_numerical": numerical_count,
                "verified": 0,
                "corrected": 0
            }
        
        # Always flag solutions as included — the initial prompt generates them inline.
        result["include_solutions"] = True
        
        # MCQ Solution Fallback: Generate solutions for MCQs that are missing them
        mcqs_missing_solutions: List[Dict[str, Any]] = []
        mcqs_missing_indices: List[int] = []
        for i, q in enumerate(questions):
            if q.get("type") in ["mcq", "mcq_multi"]:
                sol = q.get("solution", "")
                # Check for empty or placeholder solutions (relaxed: prompt now demands detailed solutions)
                if not sol or len(sol.strip()) < 20 or sol.strip().lower().startswith("the correct"):
                    mcqs_missing_indices.append(i)
                    mcqs_missing_solutions.append({
                        "text": q.get("text", ""),
                        "options": q.get("options", []),
                        "answer": q.get("answer", "")
                    })
        
        if mcqs_missing_solutions:
            print(f"[Solution Fallback] {len(mcqs_missing_solutions)} MCQs missing detailed solutions. Generating...")
            try:
                # Use batch solution generation for efficiency (optimized batch size)
                chunk_size = 10
                for batch_start in range(0, len(mcqs_missing_solutions), chunk_size):
                    batch: List[Dict[str, Any]] = list(mcqs_missing_solutions[batch_start:batch_start + chunk_size])
                    batch_indices: List[int] = list(mcqs_missing_indices[batch_start:batch_start + chunk_size])
                    solutions = await self._generate_mcq_solution_batch_async(batch, subject)
                    for j, sol in enumerate(solutions):
                        if j < len(batch_indices):
                            questions[batch_indices[j]]["solution"] = sol
                print(f"[Solution Fallback] Generated {len(mcqs_missing_solutions)} solutions successfully.")
            except Exception as e:
                print(f"[Solution Fallback] Failed: {e}")
        
        # ---- Aggregate all per-call logs into total_api_usage ----
        asyncio.create_task(self._save_total_usage(
            generation_id=self._current_generation_id,
            user_id=self._current_user_id,
            subject=subject,
            level=level,
        ))

        return result
    
    async def _save_total_usage(self, generation_id: str, user_id: Optional[str] = None,
                                subject: Optional[str] = None, level: Optional[str] = None):
        """
        Aggregate all api_usage_logs for this generation_id into one total_api_usage row.
        Called fire-and-forget after every test generation completes.
        """
        try:
            import asyncio as _asyncio
            # Small delay so all fire-and-forget _log_usage tasks can commit first
            await _asyncio.sleep(3)
            from database import SessionLocal
            from models import APIUsageLog, TotalAPIUsage  # type: ignore[attr-defined]
            from sqlalchemy import func as sqlfunc
            db = SessionLocal()
            try:
                # Aggregate all logs for this generation_id
                agg = db.query(
                    sqlfunc.sum(APIUsageLog.input_tokens).label("inp"),
                    sqlfunc.sum(APIUsageLog.output_tokens).label("out"),
                    sqlfunc.sum(APIUsageLog.total_tokens).label("tot"),
                    sqlfunc.count(APIUsageLog.id).label("cnt"),
                ).filter(APIUsageLog.generation_id == generation_id).one()

                if agg.tot and agg.tot > 0:
                    summary = TotalAPIUsage(
                        generation_id=generation_id,
                        user_id=user_id,
                        feature="question_gen",
                        subject=subject,
                        level=level,
                        model_name=str(self.model),
                        total_input_tokens=int(agg.inp or 0),
                        total_output_tokens=int(agg.out or 0),
                        total_tokens=int(agg.tot or 0),
                        api_call_count=int(agg.cnt or 0),
                    )
                    db.add(summary)
                    db.commit()
                    print(f"[TotalUsage] Saved: {agg.tot} tokens across {agg.cnt} calls for gen {generation_id[:8]}")
            finally:
                db.close()
        except Exception as e:
            print(f"[TotalUsage] Failed to save total usage: {e}")

    async def _generate_mcq_solution_batch_async(self, items: List[Dict], subject: str) -> List[str]:
        """
        Generate detailed step-by-step solutions for a batch of MCQs.
        Reduces API calls by 5x.
        """
        import asyncio
        import json
        
        if not items:
            return []
            
        # Prepare batch prompt
        items_str = ""
        for i, item in enumerate(items):
            options_text = ""
            if item.get("options"):
                letters = ["A", "B", "C", "D"]
                opts = item["options"]
                for j, opt in enumerate(opts):
                    if j < 4:
                        options_text += f"({letters[j]}) {opt} "
            
            items_str += f"""
ITEM {i+1}:
Question: {item['text']}
Options: {options_text}
Correct Answer: {item['answer']}
"""

        prompt = f"""Generate concise hint-style solutions for these {len(items)} {subject} questions.
Each solution must be SHORT: 2-3 key steps only. No verbose explanations. Exam-hint style.

{items_str}

Return JSON:
{{
  "solutions": [
    {{"item_id": 1, "solution text": "Hint: [key concept]. $[key equation]$. \\\\textbf{{Ans:}} Option X."}}
  ]
}}

RULES:
1. Max 3 steps per solution.
2. Use $...$ for inline math only.
3. End with \\\\textbf{{Ans:}} Option X.
4. NO lengthy derivations — just the KEY insight and answer.
"""

        try:
            response = await litellm.acompletion(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Solution Generator Agent. Return JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            import asyncio as _asyncio
            _asyncio.create_task(self._log_usage(
                response, feature="mcq_solution",
                user_id=self._current_user_id
            ))
            response_text = response.choices[0].message.content or ""  # type: ignore[union-attr]
            cleaned = self._clean_json_response(response_text)
            data = json.loads(cleaned)
            
            solutions_list = data.get("solutions", [])
            sol_map = {s.get("item_id"): s.get("solution text") for s in solutions_list}
            
            results = []
            for i in range(len(items)):
                item_id = i + 1
                sol = sol_map.get(item_id)
                if sol:
                    results.append(self._fix_spacing(sol))
                else:
                    results.append(f"Correct Answer: {items[i]['answer']}")
            
            return results
            
        except Exception as e:
            print(f"Batch solution generation failed: {e}")
            return [f"Correct Answer: {item['answer']}" for item in items]

    async def _generate_mcq_solution_async(
        self,
        question: str,
        options: list,
        answer: str,
        subject: str
    ) -> str:
        """Generate step-by-step solution for an MCQ question."""
        import asyncio
        
        prompt = f"""You are an expert {subject} teacher. Generate a clear, step-by-step solution.

QUESTION: {question}
OPTIONS: (A) {options[0] if len(options) > 0 else ''} (B) {options[1] if len(options) > 1 else ''} (C) {options[2] if len(options) > 2 else ''} (D) {options[3] if len(options) > 3 else ''}
CORRECT ANSWER: {answer}

FORMAT YOUR SOLUTION LIKE THIS:

\\\\textbf{{Step 1: Identify the concept}}

[Explain the key concept or formula in 1-2 lines]

\\\\textbf{{Step 2: Apply the formula}}

[Show the main equation with substitution]
$$[equation]$$

\\\\textbf{{Step 3: Calculate}}

[Show calculation steps, each on new line]
$$[result]$$

\\\\textbf{{Final Answer:}} Option {answer}

RULES:
1. Use \\\\textbf{{Step N:}} for each step header
2. Put each equation on its own line using $$ $$ for display math
3. Leave blank lines between steps for spacing
4. Use LaTeX: $F = ma$, $\\\\frac{{a}}{{b}}$, $\\\\sqrt{{x}}$
5. Be clear but not too lengthy (3-5 steps max)
6. End with \\\\textbf{{Final Answer:}} Option X

Generate the solution now:"""

        try:
            response = await litellm.acompletion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            solution = (response.choices[0].message.content or "").strip()  # type: ignore[union-attr]
            return self._fix_spacing(solution)
        except Exception as e:
            print(f"MCQ solution generation failed: {e}")
            return f"Correct answer: {answer}"


# Singleton instance
llm_engine = LLMEngine()
