"""
jee_reference_loader.py
Loads JEE Mains 2025/2026 archive reference text for a given topic/chapter.
Used to inject real JEE questions as few-shot context into the LLM prompt.
"""

import os
import json
import re
from functools import lru_cache
from typing import Optional

# Path to extracted reference data
_ARCHIVE_DIR = os.path.join(os.path.dirname(__file__), "..", "reference_data", "jee_archive")
_INDEX_PATH  = os.path.join(_ARCHIVE_DIR, "_index.json")

# Synonym map: normalize topic names that differ from archive filenames
_OVERRIDES = {
    "current electricity": "current_electricity",
    "ray optics": "ray_optics",
    "wave optics": "wave_optics",
    "rotational motion": "rotational_motion",
    "laws of motion": "laws_of_motion",
    "work power energy": "work_power_energy",
    "work, power and energy": "work_power_energy",
    "thermodynamics": "thermodynamics",
    "thermal properties of matter": "thermal_properties_of_matter",
    "oscillations": "oscillations",
    "waves and sound": "waves_and_sound",
    "kinetic theory": "kinetic_theory_of_gases",
    "kinetic theory of gases": "kinetic_theory_of_gases",
    "electromagnetic induction": "electromagnetic_induction",
    "electrostatics": "electrostatics",
    "capacitance": "capacitance",
    "gravitation": "gravitation",
    "semiconductors": "semiconductors",
    "nuclear physics": "nuclear_physics",
    "atomic physics": "atomic_physics",
    "dual nature of matter": "dual_nature_of_matter",
    "alternating current": "alternating_current",
    "magnetic effects of current": "magnetic_effects_of_current",
    "center of mass": "center_of_mass_momentum_and_collision",
    "collision": "center_of_mass_momentum_and_collision",
    "projectile": "motion_in_two_dimensions",
    "circular motion": "rotational_motion",
    "fluid mechanics": "mechanical_properties_of_fluids",
    "fluids": "mechanical_properties_of_fluids",
    "solid mechanics": "mechanical_properties_of_solids",
    "elasticity": "mechanical_properties_of_solids",
    "motion in one dimension": "motion_in_one_dimension",
    "kinematics": "motion_in_one_dimension",
    "1d motion": "motion_in_one_dimension",
    "electromagnetic waves": "electromagnetic_waves",
    "units and dimensions": "units_and_dimensions",
    "experimental physics": "experimental_physics",
}


@lru_cache(maxsize=None)
def _load_index() -> dict:
    """Load topic-to-slug index (cached)."""
    if not os.path.exists(_INDEX_PATH):
        return {}
    with open(_INDEX_PATH, encoding="utf-8") as f:
        return json.load(f)


def _find_slug(topic: str) -> Optional[str]:
    """Find best matching slug for a topic name."""
    topic_lower = topic.lower().strip()

    # 1. Direct override map
    if topic_lower in _OVERRIDES:
        return _OVERRIDES[topic_lower]
    
    # 2. Check override map for partial matches
    for key, slug in _OVERRIDES.items():
        if key in topic_lower or topic_lower in key:
            return slug

    # 3. Try index (exact and partial)
    index = _load_index()
    for chapter_name, slug in index.items():
        if chapter_name.lower() == topic_lower:
            return slug
        if chapter_name.lower() in topic_lower or topic_lower in chapter_name.lower():
            return slug

    # 4. Try slug-based fuzzy match
    slug_guess = re.sub(r'[^a-z0-9 ]', '', topic_lower)
    slug_guess = re.sub(r'\s+', '_', slug_guess.strip())
    candidate = os.path.join(_ARCHIVE_DIR, f"{slug_guess}.txt")
    if os.path.exists(candidate):
        return slug_guess

    return None


def get_reference_context(topic: str, subject: str = "Physics", max_chars: int = 3000) -> str:
    """
    Returns JEE archive reference text for a topic, to be injected into the LLM prompt.
    Returns empty string if no match found (graceful fallback).

    Args:
        topic: Chapter/topic name (e.g. "Ray Optics")
        subject: Subject name — reference currently covers Physics only
        max_chars: Maximum characters to return (keep prompt size manageable)

    Returns:
        A formatted string with real JEE questions for the topic, or "".
    """
    # Currently only Physics archive available
    if "physics" not in subject.lower():
        return ""

    slug = _find_slug(topic)
    if not slug:
        return ""

    ref_path = os.path.join(_ARCHIVE_DIR, f"{slug}.txt")
    if not os.path.exists(ref_path):
        return ""

    try:
        with open(ref_path, encoding="utf-8") as f:
            content = f.read()

        # Strip the header lines (first 4 lines)
        lines = content.strip().split("\n")
        lines = [l for l in lines if not l.startswith("#")]
        text = "\n".join(lines).strip()

        # Trim to max_chars
        if len(text) > max_chars:
            text = text[:max_chars] + "\n...[truncated]"

        return text

    except Exception as e:
        print(f"[JEEReference] Failed to load reference for '{topic}': {e}")
        return ""
