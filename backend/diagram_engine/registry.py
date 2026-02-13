from .schemas import FreeBodyParams, ProjectileParams

class DiagramRegistry:
    """
    Central registry for all supported diagram types.
    Maps: diagram_type_string -> (SchemaClass, TemplatePath)
    """
    
    _registry = {
        "free_body": {
            "schema": FreeBodyParams,
            "template": "physics/free_body.tex",
            "subject": "physics"
        },
        "projectile_motion": {
            "schema": ProjectileParams,
            "template": "physics/projectile.tex",
            "subject": "physics"
        }
        # Add more here as we implement them
    }

    @classmethod
    def get_config(cls, diagram_type: str):
        """Returns the config dict for a given diagram type."""
        return cls._registry.get(diagram_type)

    @classmethod
    def list_supported_diagrams(cls):
        return list(cls._registry.keys())
