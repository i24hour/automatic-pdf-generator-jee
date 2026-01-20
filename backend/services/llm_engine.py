"""
LLM Engine Service
Uses litellm for provider-agnostic LLM calls.
Switch between Gemini, OpenAI, or Claude by changing ACTIVE_MODEL in .env
"""

import os
import json
import re
import asyncio
from typing import Dict, List, Any
from dotenv import load_dotenv
import litellm

# Load environment variables
load_dotenv()
print("DEBUG: Loading llm_engine module...")

# Fallback models for reliability - if primary fails, try these in order
FALLBACK_MODELS = [
    "gemini/gemini-2.0-flash",
    "gemini/gemini-1.5-flash",
    "gemini/gemini-1.5-pro",
]


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
        difficulty: str = "Medium"
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
                    difficulty=difficulty
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
        difficulty: str = "Medium"
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
                    difficulty=difficulty
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
        chunk_size: int = 5  # Smaller chunks = faster parallel
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
            return self.generate_with_fallback(subject, topic, mcq_count, numerical_count, level, difficulty)
        
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
            cleaned = cleaned[start_idx:end_idx]
        
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
        Only escapes text that is OUTSIDE of $...$ delimiters.
        """
        if not text:
            return text
        
        # Split by $ to separate math and non-math parts
        parts = text.split('$')
        result = []
        
        for i, part in enumerate(parts):
            if i % 2 == 0:
                # This is outside math mode - escape special chars
                # Only escape & and % which are problematic outside math
                # Don't escape _ { } as they might be in chemical formulas etc.
                escaped = part.replace('&', r'\&').replace('%', r'\%')
                result.append(escaped)
            else:
                # This is inside math mode - keep as is
                result.append(part)
        
        return '$'.join(result)
    
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
        difficulty: str = "Medium"
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
- Questions from NEET, AIIMS, JIPMER past papers"""
        }
        
        level_prompt = level_prompts.get(level, level_prompts["JEE Mains"])
        
        # JEE Mains uses integer-type numerical questions (0-999)
        if level == "JEE Mains":
            numerical_answer_instruction = "7. NUMERICAL ANSWERS: Must be INTEGERS ONLY (whole numbers like 42, 150, 0, 999). NO decimals, NO formulas, NO fractions, NO symbols. Design questions so answers fall in range 0-999."
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
        else:
            mcq_instruction = "FOR MCQs: All MCQs should be single-correct (type: \"mcq\", answer: \"A\", \"B\", \"C\", or \"D\")"
            json_example = """{{
    "questions": [
        {{
            "type": "mcq",
            "text": "Question with $math$ notation",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "answer": "A",
            "diagram_tikz": null
        }},
        {{
            "type": "numerical", 
            "text": "Numerical question with $math$",
            "options": [],
            "answer": "numerical_value",
            "diagram_tikz": null
        }}
    ]
}}"""
        
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
                
                # Clean and parse JSON
                cleaned_json = self._clean_json_response(response_text)
                data = json.loads(cleaned_json)
                
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
                    supplement_result = self.generate_questions(
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
        difficulty: str = "Medium"
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
            "NEET": "NEET Level - Biology/Medical focus, emphasis on conceptual understanding and factual recall."
        }
        level_prompt = level_prompts.get(level, level_prompts.get("JEE Mains"))
        
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
- For Greek letters: $\\alpha$, $\\beta$, $\\theta$ (NOT α, β, θ)
- For fractions: $\\frac{{a}}{{b}}$ 
- DO NOT concatenate words or run sentences together

Return ONLY valid JSON:
{{"questions": [
  {{"type": "mcq", "text": "A body of mass $m$ is dropped from height $h$. What is the velocity?", "options": ["$\\sqrt{{2gh}}$", "$\\sqrt{{gh}}$", "$2gh$", "$gh$"], "answer": "A"}},
  {{"type": "numerical", "text": "If $F = 10$ N and $m = 2$ kg, find acceleration in m/s$^2$.", "answer": "5"}}
]}}
"""
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
        prompt = f"""You are a {subject} expert. Solve this numerical problem step-by-step.

QUESTION: {question_text}

INSTRUCTIONS:
1. Show your complete working/solution
2. At the end, clearly state: FINAL ANSWER: [your numerical answer]
3. The answer should be a number (integer or decimal)
4. Be very careful with calculations

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
        include_solutions: bool = False
    ) -> Dict[str, Any]:
        """
        Generate questions and verify numerical answers in PARALLEL.
        If include_solutions=True, also generate solutions for MCQs.
        """
        # First, generate questions normally
        result = await self.generate_parallel(subject, topic, mcq_count, numerical_count, level, difficulty)
        
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
        
        prompt = f"""You are an expert {subject} teacher. Generate a concise but complete solution for this MCQ.

QUESTION: {question}

OPTIONS:
(A) {options[0] if len(options) > 0 else ''}
(B) {options[1] if len(options) > 1 else ''}
(C) {options[2] if len(options) > 2 else ''}
(D) {options[3] if len(options) > 3 else ''}

CORRECT ANSWER: {answer}

Generate a step-by-step solution that:
1. Identifies the key concept being tested
2. Shows the reasoning or calculation to arrive at the answer
3. Uses LaTeX math mode ($...$) for formulas
4. Is concise - max 3-4 steps

Return ONLY the solution text, no JSON or extra formatting."""

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

