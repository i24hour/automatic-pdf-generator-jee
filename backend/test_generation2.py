import asyncio
from services.llm_engine import LLMEngine

async def test():
    engine = LLMEngine()
    result = await engine.generate_questions_with_verification_async(
        subject="Physics",
        topic="Kinematics",
        mcq_count=10,
        numerical_count=5,
        level="JEE Mains",
        difficulty="Medium"
    )
    if result.get("success"):
        print(f"Generated {len(result['questions'])} questions successfully")
        mcq = sum(1 for q in result['questions'] if q['type'] in ('mcq', 'mcq_multi'))
        num = sum(1 for q in result['questions'] if q['type'] == 'numerical')
        print(f"MCQs: {mcq}, Numericals: {num}")
    else:
        print("Failed:", result.get("error"))

if __name__ == "__main__":
    asyncio.run(test())
