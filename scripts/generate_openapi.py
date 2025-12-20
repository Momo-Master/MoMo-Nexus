#!/usr/bin/env python3
"""
Generate OpenAPI specification from Nexus API.

Usage:
    python scripts/generate_openapi.py
    python scripts/generate_openapi.py --output docs/openapi.json
    python scripts/generate_openapi.py --format yaml --output docs/openapi.yaml
"""

import argparse
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def generate_openapi(output_path: Path | None = None, format: str = "json") -> dict:
    """
    Generate OpenAPI spec from FastAPI app.
    
    Args:
        output_path: Path to save the spec (optional)
        format: Output format (json or yaml)
        
    Returns:
        OpenAPI spec as dict
    """
    from nexus.api.app import create_app
    
    # Create app instance
    app = create_app()
    
    # Get OpenAPI spec
    openapi_spec = app.openapi()
    
    # Add servers
    openapi_spec["servers"] = [
        {
            "url": "http://localhost:8080",
            "description": "Local development",
        },
        {
            "url": "http://nexus.local:8080",
            "description": "Nexus on local network",
        },
        {
            "url": "https://nexus.example.com",
            "description": "Production (replace with actual URL)",
        },
    ]
    
    # Add security schemes
    openapi_spec["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "API Key",
            "description": "Enter your API key",
        },
        "ApiKeyHeader": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key in header",
        },
    }
    
    # Apply security globally
    openapi_spec["security"] = [
        {"BearerAuth": []},
        {"ApiKeyHeader": []},
    ]
    
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "yaml":
            try:
                import yaml
                with open(output_path, "w") as f:
                    yaml.dump(openapi_spec, f, default_flow_style=False, sort_keys=False)
            except ImportError:
                print("PyYAML not installed, falling back to JSON")
                format = "json"
                output_path = output_path.with_suffix(".json")
        
        if format == "json":
            with open(output_path, "w") as f:
                json.dump(openapi_spec, f, indent=2)
        
        print(f"OpenAPI spec saved to: {output_path}")
    
    return openapi_spec


def main():
    parser = argparse.ArgumentParser(description="Generate OpenAPI specification")
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="docs/openapi.json",
        help="Output file path",
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["json", "yaml"],
        default="json",
        help="Output format",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        help="Print to stdout instead of file",
    )
    
    args = parser.parse_args()
    
    if args.print:
        spec = generate_openapi()
        print(json.dumps(spec, indent=2))
    else:
        generate_openapi(Path(args.output), args.format)


if __name__ == "__main__":
    main()

