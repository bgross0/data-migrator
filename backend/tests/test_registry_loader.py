"""
Tests for registry loader.

Validates:
- YAML parsing to dataclasses
- Field validation
- Import order validation
- Seed resolution with synonyms
- FK precedence checks
"""
import pytest
from pathlib import Path
from app.registry.loader import (
    RegistryLoader,
    Registry,
    ModelSpec,
    FieldSpec,
    SeedSpec,
)


@pytest.fixture
def registry_path():
    """Path to test registry file."""
    return Path(__file__).parent.parent / "registry" / "odoo.yaml"


@pytest.fixture
def registry_loader(registry_path):
    """Registry loader fixture."""
    return RegistryLoader(registry_path)


@pytest.fixture
def registry(registry_loader):
    """Loaded and validated registry."""
    return registry_loader.load()


def test_registry_loads_successfully(registry):
    """Test that registry loads without errors."""
    assert registry is not None
    assert registry.version == 1
    assert len(registry.import_order) > 0
    assert len(registry.models) > 0


def test_import_order_structure(registry):
    """Test import order contains expected models."""
    expected_models = ["res.partner", "crm.lead"]

    for model in expected_models:
        assert model in registry.import_order, f"Model {model} missing from import_order"


def test_import_order_precedence(registry):
    """Test that parent models come before children."""
    # res.partner should come before crm.lead (FK dependency)
    partner_idx = registry.import_order.index("res.partner")
    lead_idx = registry.import_order.index("crm.lead")

    assert partner_idx < lead_idx, "res.partner must come before crm.lead"


def test_res_partner_model_spec(registry):
    """Test res.partner model specification."""
    partner = registry.models["res.partner"]

    assert partner.name == "res.partner"
    assert partner.csv == "export_res_partner.csv"
    assert "id" in partner.headers
    assert "name" in partner.headers
    assert "email" in partner.headers

    # Check field specs
    assert "name" in partner.fields
    name_field = partner.fields["name"]
    assert name_field.required is True
    assert name_field.type == "string"

    # Check email field has transform
    email_field = partner.fields["email"]
    assert email_field.transform == "normalize_email"


def test_crm_lead_model_spec(registry):
    """Test crm.lead model specification."""
    lead = registry.models["crm.lead"]

    assert lead.name == "crm.lead"
    assert lead.csv == "export_crm_lead.csv"
    assert "stage_id/id" in lead.headers
    assert "partner_id/id" in lead.headers

    # Check FK field
    partner_field = lead.fields["partner_id/id"]
    assert partner_field.type == "m2o"
    assert partner_field.target == "res.partner"

    # Check enum field
    stage_field = lead.fields["stage_id/id"]
    assert stage_field.type == "enum"
    assert stage_field.map_from_seed == "crm_stages"


def test_headers_unique(registry):
    """Test that all model headers are unique."""
    for model_name, model_spec in registry.models.items():
        headers = model_spec.headers
        assert len(headers) == len(set(headers)), (
            f"Model {model_name} has duplicate headers"
        )


def test_all_fields_in_headers_or_derived(registry):
    """Test that all fields are either in headers or marked as derived."""
    for model_name, model_spec in registry.models.items():
        for field_name, field_spec in model_spec.fields.items():
            if not field_spec.derived:
                assert field_name in model_spec.headers, (
                    f"Model {model_name}: Field {field_name} not in headers and not derived"
                )


def test_fk_targets_exist(registry):
    """Test that all FK targets exist in import_order."""
    for model_name, model_spec in registry.models.items():
        for field_name, field_spec in model_spec.fields.items():
            if field_spec.type == "m2o" and field_spec.target:
                assert field_spec.target in registry.import_order, (
                    f"FK target {field_spec.target} not in import_order"
                )


def test_fk_precedence(registry):
    """Test that FK targets come before dependent models."""
    for model_name, model_spec in registry.models.items():
        if model_name not in registry.import_order:
            continue

        model_idx = registry.import_order.index(model_name)

        for field_name, field_spec in model_spec.fields.items():
            if field_spec.type == "m2o" and field_spec.target:
                if field_spec.target in registry.import_order:
                    target_idx = registry.import_order.index(field_spec.target)
                    assert target_idx < model_idx, (
                        f"FK target {field_spec.target} must come before {model_name}"
                    )


def test_seed_loading(registry):
    """Test that seeds are loaded."""
    assert len(registry.seeds) > 0
    assert "crm_stages" in registry.seeds


def test_seed_canonical_values(registry):
    """Test that seed canonical values are correct."""
    stages = registry.seeds["crm_stages"]

    assert "stage_open_qualification" in stages.canonical
    assert "stage_won" in stages.canonical
    assert stages.canonical["stage_won"] == "stage_won"


def test_seed_synonym_resolution(registry):
    """Test that seed synonyms resolve correctly."""
    stages = registry.seeds["crm_stages"]

    # Test synonym resolution
    assert stages.resolve("won") == "stage_won"
    assert stages.resolve("open") == "stage_open_qualification"
    assert stages.resolve("closed_won") == "stage_won"

    # Test canonical key resolution
    assert stages.resolve("stage_won") == "stage_won"

    # Test unknown value
    assert stages.resolve("unknown_stage") is None


def test_lost_reasons_synonyms(registry):
    """Test lost reasons synonym mappings."""
    lost_reasons = registry.seeds["crm_lost_reasons"]

    assert lost_reasons.resolve("spam") == "lost_spam"
    assert lost_reasons.resolve("no_response") == "lost_no_response"
    assert lost_reasons.resolve("too small") == "lost_too_small"


def test_utm_seeds_nested_structure(registry):
    """Test UTM seeds with nested structure (sources/mediums)."""
    # UTM should be split into sources and mediums
    assert "utm_sources" in registry.seeds or "sources" in registry.seeds

    # Check if we can resolve UTM values
    # Note: Implementation may vary based on nested structure handling


def test_registry_caching(registry_loader):
    """Test that registry is cached after first load."""
    reg1 = registry_loader.load()
    reg2 = registry_loader.load()

    assert reg1 is reg2, "Registry should be cached"

    # Test force reload
    reg3 = registry_loader.load(force_reload=True)
    assert reg3 is not reg1, "Force reload should create new instance"


def test_external_id_template(registry):
    """Test that external ID templates are defined."""
    partner = registry.models["res.partner"]
    assert partner.id_template is not None
    assert "slug" in partner.id_template
    assert "or" in partner.id_template

    lead = registry.models["crm.lead"]
    assert lead.id_template is not None


def test_field_types_valid(registry):
    """Test that field types are from expected set."""
    valid_types = {
        "string",
        "email",
        "phone",
        "date",
        "datetime",
        "bool",
        "int",
        "float",
        "enum",
        "m2o",
        None,  # Optional for some fields
    }

    for model_name, model_spec in registry.models.items():
        for field_name, field_spec in model_spec.fields.items():
            assert field_spec.type in valid_types, (
                f"Invalid field type '{field_spec.type}' for {model_name}.{field_name}"
            )


def test_import_order_vs_import_graph(registry):
    """Test that import order matches ImportGraph topological sort."""
    from app.importers.graph import ImportGraph

    graph = ImportGraph.from_default()
    canonical_order = graph.topological_sort()

    # Filter to models present in registry
    registry_models = [m for m in registry.import_order if m in registry.models]
    canonical_filtered = [m for m in canonical_order if m in registry_models]

    assert canonical_filtered == registry_models, (
        f"Import order mismatch.\nExpected: {canonical_filtered}\nGot: {registry_models}"
    )


def test_get_model_by_name(registry_loader):
    """Test retrieving model spec by name."""
    partner = registry_loader.get_model("res.partner")
    assert partner.name == "res.partner"

    with pytest.raises(ValueError, match="not found in registry"):
        registry_loader.get_model("nonexistent.model")


def test_get_seed_by_name(registry_loader):
    """Test retrieving seed spec by name."""
    stages = registry_loader.get_seed("crm_stages")
    assert stages is not None
    assert "stage_won" in stages.canonical

    with pytest.raises(ValueError, match="not found in registry"):
        registry_loader.get_seed("nonexistent_seed")
