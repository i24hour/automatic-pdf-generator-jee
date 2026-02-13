from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from database import get_db
from auth import get_current_user_required
from models import User
from diagram_engine.generator import DiagramGenerator

router = APIRouter(
    prefix="/api/diagram",
    tags=["diagram"],
    responses={404: {"description": "Not found"}},
)

class RenderRequest(BaseModel):
    diagram_type: str
    params: Dict[str, Any]

class RenderResponse(BaseModel):
    success: bool
    svg: Optional[str] = None
    error: Optional[str] = None

@router.post("/render", response_model=RenderResponse)
async def render_diagram(
    request: RenderRequest,
    current_user: User = Depends(get_current_user_required)
):
    """
    Render a diagram to SVG based on type and parameters.
    """
    try:
        generator = DiagramGenerator()
        
        # 1. Validate params (using schemas in registry)
        # This is implicitly done inside generator (if valid pydantic model exists)
        
        # 2. Convert to SVG
        # We need to implement render_to_svg in DiagramGenerator
        svg_content = generator.render_to_svg(request.diagram_type, request.params)
        
        return RenderResponse(success=True, svg=svg_content)
    
    except ValueError as e:
        return RenderResponse(success=False, error=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        return RenderResponse(success=False, error="Internal Server Error during rendering")
