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
FALLBACK_MODELS = [
    "gemini/gemini-2.5-flash",
    "gemini/gemini-2.0-flash",
    "gemini/gemini-2.0-flash-exp",
]


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
    from models import UserQuestionHistory
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
    from models import UserQuestionHistory, generate_uuid
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
                    question_text=q_text[:2000],  # Limit text length
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
        self.primary_model = os.getenv("ACTIVE_MODEL", "gemini/gemini-1.5-flash")
        self.model = self.primary_model
        self.fallback_models = FALLBACK_MODELS
        self._setup_api_keys()
    
    def _setup_api_keys(self):
        """Setup API keys for litellm based on the active model."""
        # litellm automatically picks up these environment variables
        # GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY
        pass
    
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
        chunk_size: int = 5,  # Smaller chunks = faster parallel
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate questions in PARALLEL for faster performance.
        Splits the request into multiple smaller chunks and runs them concurrently.
        This can reduce generation time by 50-70%.
        """
        import asyncio
        
        # If small enough, just do single call
        total_requested = mcq_count + numerical_count
        if total_requested <= chunk_size:
            return await self.generate_with_fallback_async(subject, topic, mcq_count, numerical_count, level, difficulty, **kwargs)
            
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
                subject, topic, mcq_cnt, num_cnt, level, difficulty
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
        
        # Run all in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        all_questions = []
        for result in results:
            if isinstance(result, Exception):
                print(f"Chunk failed: {result}")
                continue
            if result.get("success") and result.get("questions"):
                all_questions.extend(result["questions"])
        
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
            if isinstance(result, Exception):
                print(f"GATE Part failed: {result}")
                continue
            if result.get("success") and result.get("questions"):
                all_questions.extend(result["questions"])
                
        print(f"GATE Parallel complete: {len(all_questions)} questions")
        
        return {
            "success": len(all_questions) > 0,
            "subject": subject,
            "topic": topic,
            "questions": all_questions
        }

    def detect_subject(self, topic: str) -> Dict[str, str]:
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
            response_text = response.choices[0].message.content
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
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        
        cleaned = cleaned.strip()
        
        # Find the JSON object boundaries
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}") + 1
        
        if start_idx != -1 and end_idx > start_idx:
            candidate = cleaned[start_idx:end_idx]
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
            non_math_part = text[last_end:match.start()]
            if non_math_part:
                escaped = non_math_part.replace('&', r'\&').replace('%', r'\%')
                result.append(escaped)
            
            # Process the math block itself (preserve as is)
            result.append(match.group(0))  # group(0) is the full match, ignoring subgroups
            
            last_end = match.end()
            
        # Process remaining text after the last math block
        remaining_part = text[last_end:]
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
        
        # Clean up multiple spaces
        text = re.sub(r' +', ' ', text)
        
        return text.strip()
    
    def _process_questions(self, questions: List[Dict]) -> List[Dict]:
        """Process questions - preserve math mode, minimal escaping, fix spacing."""
        processed = []
        for q in questions:
            # Apply spacing fixes before LaTeX escaping
            text = self._fix_spacing(q.get("text", ""))
            text = self._escape_latex_outside_math(text)
            
            processed_q = {
                "type": q.get("type", "mcq"),
                "text": text,
                "answer": q.get("answer", ""),
                "diagram_tikz": q.get("diagram_tikz"),
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
            normalized = ' '.join(q.get('text', '').lower().split())
            
            # Only add if we haven't seen similar text
            if normalized not in seen_texts and len(normalized) > 10:
                seen_texts.add(normalized)
                unique_questions.append(q)
        
        return unique_questions

    def generate_questions(
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
            level: Exam type (Boards, JEE Mains, JEE Advanced, Olympiad, NEET)
            difficulty: Difficulty within exam (Easy, Medium, Hard)
            
        Returns:
            Dictionary with questions data
        """
        total_requested = mcq_count + numerical_count

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
        ASYNC version of generate_questions.
        """
        total_requested = mcq_count + numerical_count
        
        # Difficulty modifiers for each toughness level
        difficulty_prompts = {
            "Easy": """TOUGHNESS: EASY
- Questions from frequently asked / common patterns
- Straightforward application of concepts
- Calculations should be simple with nice numbers
- Focus on fundamental understanding
- These are the questions that most students should be able to solve
- Typical time: 1-2 minutes per question""",
            
            "Medium": """TOUGHNESS: MEDIUM
- Standard exam-level questions
- May require 2-3 step problem solving
- Some conceptual depth required
- Mix of direct and application-based questions
- These separate average students from good students
- Typical time: 2-3 minutes per question""",
            
            "Hard": """TOUGHNESS: HARD
- Challenging questions that require deep understanding
- Multi-step problems with conceptual twists
- Tricky calculations or non-obvious approaches
- These are the questions that differentiate toppers
- May combine multiple concepts
- Typical time: 3-5 minutes per question"""
        }
        
        difficulty_prompt = difficulty_prompts.get(difficulty, difficulty_prompts["Medium"])
        
        # Detailed level-specific prompts with examples
        level_prompts = {
            "Boards": """EXAM TYPE: CBSE Board Pattern
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
- DO NOT generate only MCQs for Boards
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
- Use simple lists if needed, not complex formatting

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
        
        level_prompt = level_prompts.get(level, level_prompts["JEE Mains"])
        
        # JEE Mains uses integer-type numerical questions (0-999)
        if level == "JEE Mains":
            numerical_answer_instruction = "7. NUMERICAL ANSWERS: Must be INTEGERS ONLY (whole numbers like 42, 150, 0, 999). NO decimals, NO formulas, NO fractions, NO symbols. Design questions so answers fall in range 0-999."
        elif level == "GATE":
            numerical_answer_instruction = "7. NUMERICAL ANSWERS: Can be integers or decimals (e.g., 25, 3.14, -1.5). NO formulas, NO fractions."
        else:
            numerical_answer_instruction = "7. NUMERICAL ANSWERS: Must be ONLY integers or decimals (e.g., \"42\", \"3.14\", \"-5.5\"). NO formulas, NO fractions, NO symbols."
        
        # JEE Advanced: first 20% of MCQs should be multi-correct
        if level == "JEE Advanced":
            multi_correct_count = max(1, int(mcq_count * 0.2))  # At least 1 multi-correct
            single_correct_count = mcq_count - multi_correct_count
            mcq_instruction = f"""FOR MCQs:
- Generate {multi_correct_count} MULTI-CORRECT MCQs FIRST (type: "mcq_multi", answer like "AB", "ACD", "BC")
- Then generate {single_correct_count} SINGLE-CORRECT MCQs (type: "mcq", answer like "A", "B", "C", "D")
- Multi-correct questions should have 2-3 correct options out of 4"""
            json_example = """{{
    "questions": [
        {{
            "type": "mcq_multi",
            "text": "Which of the following are correct for an isothermal process?",
            "options": ["$\\\\Delta U = 0$", "$PV = constant$", "$\\\\Delta T = 0$", "$Q = 0$"],
            "answer": "ABC",
            "diagram_tikz": null
        }},
        {{
            "type": "mcq",
            "text": "Single correct question with $math$ notation",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "answer": "A",
            "diagram_tikz": null
        }},
        {{
            "type": "numerical", 
            "text": "Numerical question with $math$",
            "options": [],
            "answer": "3.14",
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
        else:
            mcq_instruction = "FOR MCQs: All MCQs should be single-correct (type: \"mcq\", answer: \"A\", \"B\", \"C\", or \"D\")"
            json_example = """{
    "questions": [
        {
            "type": "mcq",
            "text": "Question with $math$ notation",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "answer": "A",
            "diagram_tikz": null
        },
        {
            "type": "numerical", 
            "text": "Numerical question with $math$",
            "options": [],
            "answer": "numerical_value",
            "diagram_tikz": null
        }
    ]
}"""
        
        # Special handling for Boards - generate CBSE pattern questions, not just MCQs
        if level == "Boards":
            # Calculate CBSE question distribution based on totals
            total_cbse_theory = mcq_count  # VSA+SA+LA+Case from frontend
            total_numericals = numerical_count
            
            # Approximate distribution
            # Approximate distribution
            if total_cbse_theory > 0:
                vsa_count = max(1, int(total_cbse_theory * 0.4))
                sa_count = max(1, int(total_cbse_theory * 0.3))
                la_count = max(1, int(total_cbse_theory * 0.15))
                case_count = max(0, total_cbse_theory - vsa_count - sa_count - la_count)
            else:
                vsa_count = 0
                sa_count = 0
                la_count = 0
                case_count = 0
            
            boards_json_example = """{
    "questions": [
        {"type": "short_answer", "marks": 1, "text": "Define electric flux.", "answer": "Electric flux is..."},
        {"type": "short_answer", "marks": 2, "text": "State the principle of superposition.", "answer": "When two waves..."},
        {"type": "short_answer", "marks": 3, "text": "Derive E = -dV/dr.", "answer": "Work done = qE.dr..."},
        {"type": "long_answer", "marks": 5, "text": "State and prove Gauss's law.", "answer": "Gauss's law states..."},
        {"type": "case_based", "marks": 4, "passage": "Electromagnetic induction...", "sub_questions": [
            {"text": "Who discovered it?", "options": ["Newton", "Faraday", "Maxwell", "Ampere"], "answer": "B"},
            {"text": "What is required?", "options": ["Static field", "Changing flux", "Electric field", "Gravity"], "answer": "B"},
            {"text": "Which device uses it?", "options": ["Capacitor", "Resistor", "Transformer", "Diode"], "answer": "C"},
            {"text": "In which year?", "options": ["1820", "1831", "1840", "1850"], "answer": "B"}
        ], "answer": "B, B, C, B"},
        {"type": "numerical", "marks": 3, "text": "A wire of resistance $10\\\\Omega$...", "answer": "2.5"}
    ]
}"""
            
            prompt = f"""You are an expert CBSE Board exam setter. Generate CBSE pattern questions on "{topic}" for {subject}.

{level_prompt}

{difficulty_prompt}

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
            # mcq_count contains (Single Correct + Multi Correct)
            num_single = max(0, mcq_count - num_msq)
            
            prompt = f"""You are an expert JEE Advanced question setter.
            
Generate exactly:
- {num_single} Single Correct MCQ(s) (Type: "mcq", 4 options only 1 correct, Marks: 3)
- {num_msq} Multi Correct MCQ(s) (Type: "mcq_multi", 4 options 1 or more correct, Marks: 4)
- {numerical_count} Integer Type Question(s) (Type: "numerical", answer is an integer, Marks: 3)

Topic: "{topic}" for {subject}

{level_prompt}

{difficulty_prompt}

TOTAL: {num_single + num_msq + numerical_count} Questions

REQUIREMENTS:
- For multi-correct: "answer" field should be comma separated like "A, C"
- For integer type: "answer" field should be a number string like "5"
- Use LaTeX for math: $...$, $$...$$
- NO explanations, just question, options, and answer

Return ONLY valid JSON:
{json_example}"""
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

GENERATE EXACTLY:
{req_list}

TOTAL: {total_q} Questions

REQUIREMENTS:
- All questions should be MCQ format with 4 options (A, B, C, D)
- Questions should match GATE {gate_paper} difficulty and syllabus
- Use LaTeX for math: $...$, $\\frac{{a}}{{b}}$
- Each question must have exactly one correct answer for MCQs
- NO explanations, just question, options, and answer

Return ONLY valid JSON:
{json_example}"""
        else:
            prompt = f"""You are an expert exam setter with 20+ years of experience setting {level} level examination papers for top coaching institutes like FIITJEE, Allen, and Resonance.

TASK: Generate exactly {mcq_count} MCQs and {numerical_count} Numerical questions on "{topic}" for {subject}.

{level_prompt}

{difficulty_prompt}

STRICT REQUIREMENTS:
1. Generate EXACTLY {mcq_count} MCQs and {numerical_count} Numerical questions - NO MORE, NO LESS
2. Each question MUST be UNIQUE - no duplicate or similar questions allowed
3. Questions MUST match the specified difficulty level EXACTLY - not easier, not harder
4. Each question should be solvable only by students who have mastered that level
5. {mcq_instruction}
{numerical_answer_instruction}
7. NO explanations or solutions

FORMATTING REQUIREMENTS (VERY IMPORTANT):
- Use proper spacing between words and sentences
- Write complete, grammatically correct sentences
- Use LaTeX math mode for ALL mathematical expressions: $...$
  Examples: $F = ma$, $\\frac{{a}}{{b}}$, $\\sqrt{{x}}$, $\\int_0^1 f(x) dx$
- FOR CHEMICAL REACTIONS OR LONG EQUATIONS:
  - MUST use double dollar signs $$...$$ for block display
  - Example: $$2H_2 + O_2 \\rightarrow 2H_2O$$
  - This ensures proper centered alignment and spacing on new lines
- For subscripts use: $W_0$, $v_1$, $x_2$ (NOT W₀, v₁, x₂)
- For superscripts use: $x^2$, $10^3$ (NOT x², 10³)
- For Greek letters use: $\\alpha$, $\\beta$, $\\theta$, $\\omega$ (NOT α, β, θ, ω)
- For special symbols: $\\times$ (multiplication), $\\div$ (division), $\\pm$ (plus-minus)
- Separate distinct concepts with proper punctuation and spacing
- DO NOT concatenate words or run sentences together

QUALITY CHECK: Before finalizing, verify:
- Total questions = {total_requested} (exactly {mcq_count} MCQs + {numerical_count} Numerical)
- No duplicate questions
- Each question truly represents {level} difficulty
- All mathematical expressions are in $...$ LaTeX format
- Proper spacing between all words

Return ONLY valid JSON:
{json_example}"""

        max_retries = 2
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
                
                response_text = response.choices[0].message.content
                
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
                    "raw_response": response_text if 'response_text' in locals() else None
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
            "questions": data.get("questions", []) if 'data' in locals() else []
        }

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
        total_requested = mcq_count + numerical_count
        
        # Difficulty modifiers
        difficulty_prompts = {
            "Easy": "TOUGHNESS: EASY - Questions from common patterns, straightforward application, simple calculations.",
            "Medium": "TOUGHNESS: MEDIUM - Standard exam-level, 2-3 step problems, some conceptual depth.",
            "Hard": "TOUGHNESS: HARD - Challenging questions, multi-step with conceptual twists, non-obvious approaches."
        }
        difficulty_prompt = difficulty_prompts.get(difficulty, difficulty_prompts["Medium"])
        
        # Level prompts (simplified for async)
        level_prompts = {
            "Boards": "CBSE/State Board Level - Direct application, single-step problems.",
            "JEE Mains": "JEE Main Level - Application-based, 2-3 step solutions. NUMERICAL answers must be INTEGERS 0-999.",
            "Mains": "JEE Main Level - Application-based, 2-3 step solutions. NUMERICAL answers must be INTEGERS 0-999.",
            "JEE Advanced": "JEE Advanced Level - Multi-concept, 4-5 step solutions, ~20% MCQs should be multi-correct.",
            "Advanced": "JEE Advanced Level - Multi-concept, 4-5 step solutions, ~20% MCQs should be multi-correct.",
            "Olympiad": "Olympiad Level - Research-level problem-solving, creative approaches.",
            "NEET": "NEET Level - Biology/Medical focus, emphasis on conceptual understanding and factual recall.",
            "GATE": "GATE Level - High conceptual depth, mix of MCQ (Negative), MSQ (No Negative), NAT (No Negative), and GA."
        }
        level_prompt = level_prompts.get(level, level_prompts.get("JEE Mains"))
        
        # Special handling for Boards - generate CBSE pattern questions
        if level == "Boards":
            total_cbse_theory = mcq_count
            total_numericals = numerical_count
            
            if total_cbse_theory > 0:
                vsa_count = max(1, int(total_cbse_theory * 0.4))
                sa_count = max(1, int(total_cbse_theory * 0.3))
                la_count = max(1, int(total_cbse_theory * 0.15))
                case_count = max(0, total_cbse_theory - vsa_count - sa_count - la_count)
            else:
                vsa_count = 0
                sa_count = 0
                la_count = 0
                case_count = 0
            
            prompt = f"""You are a CBSE Board exam setter. Generate CBSE pattern questions.

SUBJECT: {subject}
TOPIC: {topic}
{difficulty_prompt}

GENERATE EXACTLY:
- {vsa_count} Very Short Answer (1-2 marks, type: "short_answer", marks: 1 or 2)
- {sa_count} Short Answer (2-3 marks, type: "short_answer", marks: 2 or 3)
- {la_count} Long Answer (5 marks, type: "long_answer", marks: 5)
- {case_count} Case-Based (4 marks, type: "case_based" with passage and 4 sub_questions)
- {total_numericals} Numerical (3-5 marks, type: "numerical", marks: 3 or 5)

Use LaTeX: $F = ma$, $\\\\frac{{a}}{{b}}$

Return ONLY JSON:
{{"questions": [
  {{"type": "short_answer", "marks": 2, "text": "Define electric flux.", "answer": "Electric flux is..."}},
  {{"type": "long_answer", "marks": 5, "text": "State and prove Gauss's law.", "answer": "Gauss's law states..."}},
  {{"type": "case_based", "marks": 4, "passage": "EM induction paragraph...", "sub_questions": [
    {{"text": "Q1?", "options": ["A", "B", "C", "D"], "answer": "B"}},
    {{"text": "Q2?", "options": ["A", "B", "C", "D"], "answer": "C"}},
    {{"text": "Q3?", "options": ["A", "B", "C", "D"], "answer": "A"}},
    {{"text": "Q4?", "options": ["A", "B", "C", "D"], "answer": "D"}}
  ], "answer": "B, C, A, D"}},
  {{"type": "numerical", "marks": 3, "text": "Find resistance...", "answer": "5"}}
]}}
"""
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
        else:
            prompt = f"""You are an expert question paper setter for competitive exams like FIITJEE, Allen, Resonance.

GENERATE EXACTLY:
- {mcq_count} MCQ questions (type "mcq", with options array and answer as A/B/C/D)
- {numerical_count} Numerical questions (type "numerical", answer as integer)

SUBJECT: {subject}
TOPIC: {topic}
EXAM LEVEL: {level_prompt}
{difficulty_prompt}

FORMATTING REQUIREMENTS (CRITICAL):
- Use proper spacing between ALL words and sentences
- Use LaTeX math mode for ALL mathematical expressions: $...$
- For subscripts: $W_0$, $v_1$ (NOT W₀, v₁)
- For superscripts: $x^2$, $10^3$ (NOT x², 10³)
- For Greek letters: $\\\\alpha$, $\\\\beta$, $\\\\theta$ (NOT α, β, θ)
- For fractions: $\\\\frac{{a}}{{b}}$ 
- DO NOT concatenate words or run sentences together

Return ONLY valid JSON:
{{"questions": [
  {{"type": "mcq", "text": "A body of mass $m$ is dropped from height $h$. What is the velocity?", "options": ["$\\\\sqrt{{2gh}}$", "$\\\\sqrt{{gh}}$", "$2gh$", "$gh$"], "answer": "A"}},
  {{"type": "numerical", "text": "If $F = 10$ N and $m = 2$ kg, find acceleration in m/s$^2$.", "answer": "5"}}
]}}
"""
        # Fresh Questions: Add anti-repetition instruction if past questions provided
        past_questions = kwargs.get("past_questions")
        if past_questions and len(past_questions) > 0:
            # Format past questions as a numbered list (limit to avoid token overflow)
            past_qs_formatted = "\n".join([f"{i+1}. {q[:200]}" for i, q in enumerate(past_questions[:30])])
            anti_repeat_instruction = f"""

IMPORTANT - AVOID REPETITION:
DO NOT generate any questions similar to these previously generated questions:
{past_qs_formatted}

Generate COMPLETELY DIFFERENT questions with different wording, scenarios, and values.
"""
            prompt += anti_repeat_instruction
            print(f"Added anti-repetition instruction with {len(past_questions)} past questions")
        
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                response = await litellm.acompletion(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": f"Expert {subject} question setter. Return ONLY valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7
                )
                
                response_text = response.choices[0].message.content
                cleaned_json = self._clean_json_response(response_text)
                data = json.loads(cleaned_json)
                
                if "questions" in data:
                    data["questions"] = self._process_questions(data["questions"])
                    data["questions"] = self._deduplicate_questions(data["questions"])
                    
                    actual_count = len(data["questions"])
                    if actual_count < total_requested and attempt < max_retries:
                        continue
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
                    print(f"Supplementing async: need {missing_mcq} more MCQs and {missing_num} more numericals")
                    # Recursive call for missing questions (ASYNC)
                    supplement_result = await self.generate_with_fallback_async(
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
                
            except Exception as e:
                if attempt < max_retries:
                    continue
                return {
                    "success": False,
                    "error": f"Async LLM call failed: {str(e)}"
                }
        
        return {
            "success": True,
            "subject": subject,
            "topic": topic,
            "questions": data.get("questions", []) if 'data' in locals() else []
        }

    async def verify_numerical_answer_async(self, question_text: str, original_answer: str, subject: str) -> Dict[str, Any]:
        """
        Verify a numerical answer by asking LLM to solve the question step-by-step (ASYNC).
        Returns the verified answer and whether it matches the original.
        """
        prompt = f"""Solve this {subject} numerical problem step-by-step.

QUESTION: {question_text}

FORMAT:
\\\\textbf{{Step 1: Given}}
[List given values]

\\\\textbf{{Step 2: Formula}}
$$[formula]$$

\\\\textbf{{Step 3: Calculation}}
$$[substitute and calculate]$$

FINAL ANSWER: [numerical value]

Use LaTeX: $F = ma$, $\\\\frac{{a}}{{b}}$
Solve now:"""

        try:
            # Use acompletion for async call
            response = await litellm.acompletion(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"You are a precise {subject} solver. Show step-by-step working and give exact numerical answer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2  # Low temperature for consistent answers
            )
            
            response_text = response.choices[0].message.content
            
            # Extract the final answer
            import re
            # Look for "FINAL ANSWER: X" pattern
            match = re.search(r'FINAL ANSWER[:\s]*([+-]?\d*\.?\d+)', response_text, re.IGNORECASE)
            if match:
                verified_answer = match.group(1)
            else:
                # Try to find any number at the end
                numbers = re.findall(r'[+-]?\d*\.?\d+', response_text)
                verified_answer = numbers[-1] if numbers else original_answer
            
            # Compare answers (with tolerance for floating point)
            try:
                orig_num = float(original_answer)
                verif_num = float(verified_answer)
                # Allow 1% tolerance for floating point comparisons
                tolerance = max(abs(orig_num) * 0.01, 0.01)
                matches = abs(orig_num - verif_num) <= tolerance
            except (ValueError, TypeError):
                matches = original_answer.strip() == verified_answer.strip()
            
            return {
                "success": True,
                "original_answer": original_answer,
                "verified_answer": verified_answer,
                "matches": matches,
                "solution": response_text
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "original_answer": original_answer,
                "verified_answer": original_answer,
                "matches": True  # Assume original is correct if verification fails
            }

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
        # First, generate questions normally
        result = await self.generate_parallel(subject, topic, mcq_count, numerical_count, level, difficulty, **kwargs)
        
        if not result.get("success"):
            return result
        
        questions = result.get("questions", [])
        
        # Identify numerical questions to verify
        verification_tasks = []
        numerical_indices = []
        
        for i, q in enumerate(questions):
            if q.get("type") == "numerical":
                numerical_indices.append(i)
                verification_tasks.append(
                    self.verify_numerical_answer_async(
                        q.get("text", ""),
                        q.get("answer", ""),
                        subject
                    )
                )
        
        # Run all verifications in parallel
        if verification_tasks:
            verification_results = await asyncio.gather(*verification_tasks)
            
            verified_count = 0
            corrected_count = 0
            
            for i, verification in enumerate(verification_results):
                q_index = numerical_indices[i]
                q = questions[q_index]
                
                if verification.get("success"):
                    verified_count += 1
                    if not verification.get("matches"):
                        # Answer mismatch - use verified answer
                        q["original_answer"] = q.get("answer")
                        q["answer"] = verification.get("verified_answer")
                        q["answer_corrected"] = True
                        q["solution"] = verification.get("solution")
                        corrected_count += 1
                    else:
                        q["answer_verified"] = True
                        q["solution"] = verification.get("solution")
            
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
        
        # If include_solutions is True, generate solutions for MCQs
        if include_solutions:
            mcq_solution_tasks = []
            mcq_indices = []
            
            for i, q in enumerate(questions):
                if q.get("type") in ["mcq", "mcq_multi"] and not q.get("solution"):
                    mcq_indices.append(i)
                    mcq_solution_tasks.append(
                        self._generate_mcq_solution_async(
                            q.get("text", ""),
                            q.get("options", []),
                            q.get("answer", ""),
                            subject
                        )
                    )
            
            if mcq_solution_tasks:
                mcq_solutions = await asyncio.gather(*mcq_solution_tasks)
                for i, solution in enumerate(mcq_solutions):
                    q_index = mcq_indices[i]
                    questions[q_index]["solution"] = solution
            
            result["include_solutions"] = True
        
        return result
    
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
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: litellm.completion(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )
            )
            
            solution = response.choices[0].message.content.strip()
            return self._fix_spacing(solution)
        except Exception as e:
            print(f"MCQ solution generation failed: {e}")
            return f"Correct answer: {answer}"


# Singleton instance
llm_engine = LLMEngine()

