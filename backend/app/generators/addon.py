"""
Odoo addon generator - creates custom field addons from YAML specs using Jinja2.
"""
from typing import Dict, List, Any
from pathlib import Path
import zipfile
from jinja2 import Environment, FileSystemLoader
from app.core.config import settings


class AddonGenerator:
    """Generates Odoo addons for custom fields."""

    def __init__(self):
        template_path = Path(settings.STORAGE_PATH).parent / "templates" / "addon_templates"
        self.env = Environment(loader=FileSystemLoader(str(template_path)))

    def generate(self, spec: Dict[str, Any]) -> Path:
        """
        Generate an Odoo addon from a specification.

        Args:
            spec: Addon specification
                {
                    "name": "axsys_custom_fields",
                    "display_name": "Axsys Custom Fields",
                    "version": "1.0.0",
                    "models": {
                        "res.partner": [
                            {"name": "x_ax_buildertrend_id", "type": "char", "string": "Buildertrend ID"}
                        ]
                    }
                }

        Returns:
            Path to generated .zip file
        """
        addon_name = spec["name"]
        output_dir = Path(settings.STORAGE_PATH) / "addons" / addon_name
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate __manifest__.py
        self._generate_manifest(output_dir, spec)

        # Generate __init__.py
        self._generate_init(output_dir, spec)

        # Generate models files
        self._generate_models(output_dir, spec)

        # Generate security files
        self._generate_security(output_dir, spec)

        # Zip it up
        zip_path = self._create_zip(output_dir)

        return zip_path

    def _generate_manifest(self, output_dir: Path, spec: Dict[str, Any]):
        """Generate __manifest__.py file."""
        manifest_template = self.env.get_template("__manifest__.py.j2")
        content = manifest_template.render(spec)
        (output_dir / "__manifest__.py").write_text(content)

    def _generate_init(self, output_dir: Path, spec: Dict[str, Any]):
        """Generate __init__.py file."""
        init_template = self.env.get_template("__init__.py.j2")
        content = init_template.render(spec)
        (output_dir / "__init__.py").write_text(content)

    def _generate_models(self, output_dir: Path, spec: Dict[str, Any]):
        """Generate model extension files."""
        models_dir = output_dir / "models"
        models_dir.mkdir(exist_ok=True)

        # models/__init__.py
        model_imports = []
        for model_name in spec.get("models", {}).keys():
            safe_name = model_name.replace(".", "_")
            model_imports.append(f"from . import {safe_name}")

        (models_dir / "__init__.py").write_text("\n".join(model_imports) + "\n")

        # Generate each model file
        model_template = self.env.get_template("models/model.py.j2")
        for model_name, fields in spec.get("models", {}).items():
            safe_name = model_name.replace(".", "_")
            content = model_template.render(
                model_name=model_name,
                model_class=safe_name.title().replace("_", ""),
                fields=fields,
            )
            (models_dir / f"{safe_name}.py").write_text(content)

    def _generate_security(self, output_dir: Path, spec: Dict[str, Any]):
        """Generate security/ir.model.access.csv file."""
        security_dir = output_dir / "security"
        security_dir.mkdir(exist_ok=True)

        # TODO: Generate proper access rules
        # For now, just create an empty file
        (security_dir / "ir.model.access.csv").write_text(
            "id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink\n"
        )

    def _create_zip(self, addon_dir: Path) -> Path:
        """Create a .zip file of the addon."""
        zip_path = addon_dir.parent / f"{addon_dir.name}.zip"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file in addon_dir.rglob("*"):
                if file.is_file():
                    arcname = file.relative_to(addon_dir.parent)
                    zipf.write(file, arcname)

        return zip_path
