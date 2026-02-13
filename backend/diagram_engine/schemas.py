from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal

class DiagramParams(BaseModel):
    """Base class for all diagram parameters."""
    caption: Optional[str] = None
    width_check: Optional[float] = Field(default=0.8, description="Scale factor for linewidth")

# --- Physics Schemas ---

class FreeBodyParams(DiagramParams):
    """Parameters for a block on an inclined plane FBD."""
    mass: float = Field(..., description="Mass of the block in kg")
    angle: float = Field(..., description="Incline angle in degrees")
    friction_coefficient: Optional[float] = Field(default=None, description="Mu value. If present, draws friction vector.")
    force_applied: Optional[float] = Field(default=None, description="External force applied up the incline")
    show_components: bool = Field(default=True, description="Whether to show mg sin/cos components")

class ProjectileParams(DiagramParams):
    """Parameters for projectile motion."""
    velocity: float = Field(..., description="Initial velocity")
    angle: float = Field(..., description="Launch angle")
    height: float = Field(default=0, description="Initial height")

# --- Registry Map (to be imported by registry.py) ---
# We will populate this as we add more schemas.
