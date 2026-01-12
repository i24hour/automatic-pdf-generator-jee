"""
LLM Engine Service
Uses litellm for provider-agnostic LLM calls.
Switch between Gemini, OpenAI, or Claude by changing ACTIVE_MODEL in .env
"""

import os
import json
import re
from typing import Dict, List, Any
from dotenv import load_dotenv
import litellm

# Load environment variables
load_dotenv()


class LLMEngine:
    """LLM-agnostic engine for generating test questions."""
    
    def __init__(self):
        self.model = os.getenv("ACTIVE_MODEL", "gemini/gemini-1.5-flash")
        self._setup_api_keys()
    
    def _setup_api_keys(self):
        """Setup API keys for litellm based on the active model."""
        # litellm automatically picks up these environment variables
        # GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY
        pass

    def detect_subject(self, topic: str) -> Dict[str, str]:
        """Classify a topic into a subject with confidence using the LLM."""
        prompt = f"""
You are a subject classifier for exam topics. Given the topic text, return a JSON with:
- \"subject\": one of [\"Physics\", \"Chemistry\", \"Maths\", \"Biology\"]
- \"confidence\": \"high\", \"medium\", or \"low\"

Topic: \"{topic}\"

Return ONLY JSON, no extra text.
Example: {{\"subject\":\"Physics\",\"confidence\":\"high\"}}
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
            subject_map = {s.lower(): s for s in ["Physics", "Chemistry", "Maths", "Biology"]}
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
    
    def _process_questions(self, questions: List[Dict]) -> List[Dict]:
        """Process questions - preserve math mode, minimal escaping."""
        processed = []
        for q in questions:
            processed_q = {
                "type": q.get("type", "mcq"),
                "text": self._escape_latex_outside_math(q.get("text", "")),
                "answer": q.get("answer", ""),
                "diagram_tikz": q.get("diagram_tikz"),
            }
            
            if q.get("options"):
                processed_q["options"] = [self._escape_latex_outside_math(opt) for opt in q["options"]]
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
            "Boards": """EXAM TYPE: CBSE/State Board Level
CHARACTERISTICS:
- Direct application of formulas and concepts
- Single-step or simple two-step problems
- No complex calculations or multi-concept integration
- Focus on definitions, basic numericals, and theorem applications

EXAMPLE BOARD-LEVEL QUESTIONS:
- "State Coulomb's law and calculate force between two charges of 2μC separated by 10cm"
- "What is the SI unit of electric potential?"
- "Calculate the resistance of a wire with resistivity ρ, length l, and area A"
- Numerical answers are typically round numbers or simple fractions""",

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
        
        prompt = f"""You are an expert exam setter with 20+ years of experience setting {level} level examination papers.

TASK: Generate exactly {mcq_count} MCQs and {numerical_count} Numerical questions on "{topic}" for {subject}.

{level_prompt}

{difficulty_prompt}

STRICT REQUIREMENTS:
1. Generate EXACTLY {mcq_count} MCQs and {numerical_count} Numerical questions - NO MORE, NO LESS
2. Each question MUST be UNIQUE - no duplicate or similar questions allowed
3. Questions MUST match the specified difficulty level EXACTLY - not easier, not harder
4. Each question should be solvable only by students who have mastered that level
5. Use proper LaTeX math mode: $...$ for inline math (e.g., $F = ma$, $\\frac{{a}}{{b}}$, $\\sqrt{{x}}$)
6. {mcq_instruction}
{numerical_answer_instruction}
8. NO explanations or solutions

QUALITY CHECK: Before finalizing, verify:
- Total questions = {total_requested} (exactly {mcq_count} MCQs + {numerical_count} Numerical)
- No duplicate questions
- Each question truly represents {level} difficulty

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
                
                return {
                    "success": True,
                    "subject": subject,
                    "topic": topic,
                    "questions": data.get("questions", [])
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


# Singleton instance
llm_engine = LLMEngine()

