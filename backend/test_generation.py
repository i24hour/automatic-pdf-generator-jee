import asyncio
from services.llm_engine import LLMEngine

async def test():
    engine = LLMEngine()
    result = await engine._generate_batch_for_difficulty(
        subject="Physics",
        topic="Kinematics",
        mcq_count=5,
        numerical_count=3,
        level="JEE Mains",
        difficulty_label="Medium",
        level_prompt="JEE Mains"
    )
    print("Done")

if __name__ == "__main__":
    asyncio.run(test())
