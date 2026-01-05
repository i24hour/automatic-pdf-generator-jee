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
    
    def _clean_json_response(self, response_text: str) -> str:
        """
        Clean the LLM response to extract valid JSON.
        Handles markdown code blocks, extra text, and invalid escape sequences.
        """
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
        
        # Fix common invalid escape sequences in JSON
        # LLMs sometimes use \frac, \sqrt, etc. which are invalid JSON escapes
        # We need to escape single backslashes that aren't valid JSON escapes
        import re
        
        # Valid JSON escape sequences: \", \\, \/, \b, \f, \n, \r, \t, \uXXXX
        # Replace single backslashes that are not part of valid escapes
        def fix_escapes(match):
            char = match.group(1)
            valid_escapes = ['"', '\\', '/', 'b', 'f', 'n', 'r', 't', 'u']
            if char in valid_escapes:
                return match.group(0)  # Keep valid escape
            else:
                return '\\\\' + char  # Double the backslash for invalid escapes
        
        # Match backslash followed by any character
        cleaned = re.sub(r'\\(.)', fix_escapes, cleaned)
        
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
        level: str = "JEE Mains"
    ) -> Dict[str, Any]:
        """
        Generate test questions using the configured LLM.
        
        Args:
            subject: The subject (Physics, Chemistry, Maths)
            topic: The specific topic
            mcq_count: Number of MCQ questions
            numerical_count: Number of numerical questions
            level: Difficulty level (Boards, JEE Mains, JEE Advanced, Olympiad)
            
        Returns:
            Dictionary with questions data
        """
        total_requested = mcq_count + numerical_count
        
        # Detailed level-specific prompts with examples
        level_prompts = {
            "Boards": """DIFFICULTY: CBSE/State Board Level
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

            "JEE Mains": """DIFFICULTY: JEE Main Level (Moderate-Hard)
CHARACTERISTICS:
- Application-based problems requiring 2-3 step solutions
- Conceptual twists and common misconception traps
- Integration of 2 related concepts
- Moderate calculation complexity
- Questions similar to NTA JEE Main papers

EXAMPLE JEE MAINS-LEVEL QUESTIONS:
- "A capacitor is charged to V volts and then connected to an inductor. Find maximum current"
- "Two blocks connected by spring on frictionless surface - find oscillation frequency"
- "In Young's double slit, if one slit is covered with thin film, find fringe shift"
- Distractors should include common calculation errors""",

            "JEE Advanced": """DIFFICULTY: JEE Advanced Level (Hard-Very Hard)
CHARACTERISTICS:
- Multi-concept problems requiring 4-5 step solutions
- Non-obvious approach needed, lateral thinking required
- Integration of 3+ concepts from different subtopics
- Complex mathematical manipulation
- Questions similar to actual IIT JEE Advanced papers
- May have multiple correct options (but format as single correct for this paper)
- Paragraph-based or assertion-reason style thinking

EXAMPLE JEE ADVANCED-LEVEL QUESTIONS:
- "A conducting sphere in non-uniform electric field - find induced dipole moment and force"
- "Thermodynamic cycle with adiabatic, isothermal, and polytropic processes - find efficiency"
- "Block on accelerating wedge with friction - find condition for relative motion"
- Problems that test edge cases and deep understanding""",

            "Olympiad": """DIFFICULTY: Physics/Chemistry/Math Olympiad Level (Extremely Hard)
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

            "NEET": """DIFFICULTY: NEET Level (Medical Entrance Exam)
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
        
        prompt = f"""You are an expert exam setter with 20+ years of experience setting {level} level examination papers.

TASK: Generate exactly {mcq_count} MCQs and {numerical_count} Numerical questions on "{topic}" for {subject}.

{level_prompt}

STRICT REQUIREMENTS:
1. Generate EXACTLY {mcq_count} MCQs and {numerical_count} Numerical questions - NO MORE, NO LESS
2. Each question MUST be UNIQUE - no duplicate or similar questions allowed
3. Questions MUST match the specified difficulty level EXACTLY - not easier, not harder
4. Each question should be solvable only by students who have mastered that level
5. Use proper LaTeX math mode: $...$ for inline math (e.g., $F = ma$, $\\frac{{a}}{{b}}$, $\\sqrt{{x}}$)
6. MCQs must have exactly 4 options with plausible distractors
7. NUMERICAL ANSWERS: Must be ONLY integers or decimals (e.g., "42", "3.14", "-5.5"). NO formulas, NO fractions, NO symbols.
8. NO explanations or solutions

QUALITY CHECK: Before finalizing, verify:
- Total questions = {total_requested} (exactly {mcq_count} MCQs + {numerical_count} Numerical)
- No duplicate questions
- Each question truly represents {level} difficulty

Return ONLY valid JSON:
{{
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

