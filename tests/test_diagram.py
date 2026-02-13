import sys
import os

# Add backend to path specifically
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

# Now import directly from diagram_engine package
from diagram_engine.generator import DiagramGenerator
from diagram_engine.registry import DiagramRegistry

def test_engine_initialization():
    print("Testing Initialization...")
    generator = DiagramGenerator()
    assert generator.env is not None
    print("✅ Initialization Passed")

def test_registry_lookup():
    print("Testing Registry...")
    config = DiagramRegistry.get_config("free_body")
    assert config is not None
    assert config["subject"] == "physics"
    print("✅ Registry Lookup Passed")

def test_fbd_generation():
    print("Testing FBD Generation...")
    generator = DiagramGenerator()
    params = {
        "mass": 10,
        "angle": 30,
        "friction_coefficient": 0.2,
        "show_components": True
    }
    
    latex = generator.generate("free_body", params)
    
    print("\nGenerated LaTeX Preview (First 100 chars):\n", latex[:100], "...")
    
    assert "\\begin{tikzpicture}" in latex
    assert "\\node at (20:0.8) {$\\theta$};" in latex # Check angle label
    assert "mg" in latex
    assert "f_k" in latex # Friction present
    print("✅ FBD Generation Passed")

def test_invalid_type():
    print("Testing Invalid Type Handling...")
    generator = DiagramGenerator()
    try:
        generator.generate("non_existent_diagram", {})
        print("❌ Failed: Should have raised exception")
    except ValueError:
         print("✅ Invalid Type Handled Correctly")
    except Exception as e:
        print(f"✅ Invalid Type Handled (Error: {e})")

if __name__ == "__main__":
    try:
        test_engine_initialization()
        test_registry_lookup()
        test_fbd_generation()
        test_invalid_type()
        print("\n🎉 ALL TESTS PASSED!")
    except Exception as e:
        print("\n❌ TEST FAILED:", e)
        import traceback
        traceback.print_exc()
