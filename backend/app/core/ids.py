"""
Deterministic External ID generator - creates stable, collision-safe identifiers.

Key principles:
- Same input data = same XID (deterministic)
- Collision-safe with short hash fallback
- Namespaced by model type
- Human-readable when possible
"""
import hashlib
import re
from typing import Optional


def slug(s: str) -> str:
    """
    Convert string to URL-safe slug.

    Examples:
        "John Smith" -> "john_smith"
        "Acme Corp!!!" -> "acme_corp"
        "test@email.com" -> "test_email_com"
    """
    if not s:
        return "x"

    # Convert to lowercase and replace non-alphanumeric with underscore
    s = re.sub(r"[^A-Za-z0-9]+", "_", s.lower()).strip("_")

    # Collapse multiple underscores
    s = re.sub(r"_+", "_", s)

    # Limit length and ensure we have something
    return s[:48] or "x"


def shash(*vals: str) -> str:
    """
    Generate short hash from values for collision resolution.

    Args:
        *vals: Values to hash together

    Returns:
        6-character hex hash
    """
    combined = "|".join(v or "" for v in vals)
    return hashlib.md5(combined.encode()).hexdigest()[:6]


def partner_xid(
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    address: Optional[str] = None
) -> str:
    """
    Generate external ID for res.partner (contact/customer).

    Priority order:
    1. Email (most stable)
    2. Phone (if normalized to E.164)
    3. Name + Address hash (for disambiguation)
    4. Name only
    5. Fallback hash

    Examples:
        email="john@acme.com" -> "partner_john_acme_com"
        name="John Smith", address="123 Main" -> "partner_john_smith_a3f2c1"
        phone="+15551234567" -> "partner_15551234567"
    """
    if email:
        return f"partner_{slug(email)}"
    if phone:
        return f"partner_{slug(phone)}"
    if name and address:
        return f"partner_{slug(name)}_{shash(address)}"
    if name:
        return f"partner_{slug(name)}"

    # Last resort - hash all available data
    return f"partner_{shash(name or 'unknown', email or '', phone or '')}"


def product_xid(
    name: Optional[str] = None,
    sku: Optional[str] = None,
    default_code: Optional[str] = None
) -> str:
    """
    Generate external ID for product.template / product.product.

    Priority:
    1. SKU/default_code (most stable)
    2. Name
    3. Fallback hash

    Examples:
        default_code="WIDGET-001" -> "product_widget_001"
        name="Blue Widget" -> "product_blue_widget"
    """
    code = sku or default_code
    if code:
        return f"product_{slug(code)}"
    if name:
        return f"product_{slug(name)}"

    return f"product_{shash(name or 'unknown')}"


def sale_order_xid(order_number: Optional[str] = None) -> str:
    """
    Generate external ID for sale.order.

    Examples:
        "SO-2024-001" -> "so_so_2024_001"
        "12345" -> "so_12345"
    """
    if not order_number:
        return f"so_{shash('unknown')}"

    return f"so_{slug(order_number)}"


def sale_order_line_xid(order_number: Optional[str] = None, line_idx: int = 0) -> str:
    """
    Generate external ID for sale.order.line.

    Examples:
        order_number="SO-001", line_idx=0 -> "sol_so_001_0"
        order_number="SO-001", line_idx=2 -> "sol_so_001_2"
    """
    if not order_number:
        return f"sol_{shash('unknown')}_{line_idx}"

    return f"sol_{slug(order_number)}_{line_idx}"


def invoice_xid(invoice_number: Optional[str] = None) -> str:
    """
    Generate external ID for account.move (invoice).

    Examples:
        "INV-2024-001" -> "inv_inv_2024_001"
        "12345" -> "inv_12345"
    """
    if not invoice_number:
        return f"inv_{shash('unknown')}"

    return f"inv_{slug(invoice_number)}"


def invoice_line_xid(invoice_number: Optional[str] = None, line_idx: int = 0) -> str:
    """
    Generate external ID for account.move.line (invoice line).

    Examples:
        invoice_number="INV-001", line_idx=0 -> "invl_inv_001_0"
    """
    if not invoice_number:
        return f"invl_{shash('unknown')}_{line_idx}"

    return f"invl_{slug(invoice_number)}_{line_idx}"


def project_xid(name: Optional[str] = None, code: Optional[str] = None) -> str:
    """
    Generate external ID for project.project.

    Examples:
        code="PROJ-001" -> "project_proj_001"
        name="New Office Build" -> "project_new_office_build"
    """
    if code:
        return f"project_{slug(code)}"
    if name:
        return f"project_{slug(name)}"

    return f"project_{shash('unknown')}"


def task_xid(
    project_name: Optional[str] = None,
    task_name: Optional[str] = None,
    task_idx: Optional[int] = None
) -> str:
    """
    Generate external ID for project.task.

    Examples:
        project="Website", task="Design mockups" -> "task_website_design_mockups"
        project="Website", task_idx=5 -> "task_website_5"
    """
    if project_name and task_name:
        return f"task_{slug(project_name)}_{slug(task_name)}"
    if project_name and task_idx is not None:
        return f"task_{slug(project_name)}_{task_idx}"
    if task_name:
        return f"task_{slug(task_name)}"

    return f"task_{shash('unknown')}"


def vehicle_xid(vin: Optional[str] = None, plate: Optional[str] = None) -> str:
    """
    Generate external ID for fleet.vehicle.

    Priority:
    1. VIN (most stable)
    2. License plate
    3. Fallback hash

    Examples:
        vin="1HGBH41JXMN109186" -> "veh_1hgbh41jxmn109186"
        plate="ABC-1234" -> "veh_abc_1234"
    """
    if vin:
        return f"veh_{slug(vin)}"
    if plate:
        return f"veh_{slug(plate)}"

    return f"veh_{shash('unknown')}"


def lead_xid(
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None
) -> str:
    """
    Generate external ID for crm.lead.

    Similar to partner but with lead prefix.

    Examples:
        email="prospect@company.com" -> "lead_prospect_company_com"
        name="Jane Doe", phone="+15551234567" -> "lead_jane_doe_a3f2c1"
    """
    if email:
        return f"lead_{slug(email)}"
    if phone:
        return f"lead_{slug(phone)}"
    if name:
        return f"lead_{slug(name)}"

    return f"lead_{shash(name or 'unknown', email or '', phone or '')}"


def generic_xid(model: str, *values: Optional[str]) -> str:
    """
    Generate external ID for any model using provided values.

    Args:
        model: Model name (e.g., "res.partner")
        *values: Values to use for ID generation

    Returns:
        External ID in format: "model_prefix_slugged_values"

    Examples:
        ("res.partner", "Acme") -> "res_partner_acme"
        ("custom.model", "ABC", "123") -> "custom_model_abc_123"
    """
    # Create prefix from model name
    prefix = slug(model.replace(".", "_"))

    # Filter out None/empty values and slug them
    slugged = [slug(v) for v in values if v]

    if not slugged:
        return f"{prefix}_{shash('unknown')}"

    # Combine prefix with slugged values
    combined = "_".join([prefix] + slugged)

    # If too long, use hash of later values
    if len(combined) > 64:
        return f"{prefix}_{slugged[0]}_{shash(*values)}"

    return combined
