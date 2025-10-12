"""
Comprehensive Odoo field mappings based on Odoo 18 documentation.
This module provides accurate field mappings for data migration.
"""

# Comprehensive field mappings for major Odoo models
ODOO_FIELD_MAPPINGS = {
    # ===================== CONTACTS (res.partner) =====================
    "res.partner": {
        # Basic Information
        "name": ["name", "customer", "client", "vendor", "supplier", "partner", "company", "business", "contact", "account", "party"],
        "display_name": ["display name", "full name", "complete name"],
        "email": ["email", "e-mail", "mail", "email address", "contact email", "business email"],
        "phone": ["phone", "telephone", "tel", "phone number", "contact phone", "business phone", "primary phone"],
        "mobile": ["mobile", "cell", "cellular", "mobile phone", "cell phone"],
        "website": ["website", "web", "url", "site", "homepage", "web address"],
        "function": ["job", "position", "title", "job title", "role", "function", "designation"],

        # Address Fields
        "street": ["street", "address", "street address", "address 1", "address line 1", "street 1"],
        "street2": ["street2", "address 2", "address line 2", "street 2", "apt", "suite", "unit"],
        "city": ["city", "town", "municipality", "locality"],
        "state_id": ["state", "province", "region", "state/province"],
        "zip": ["zip", "postal", "postcode", "postal code", "zip code"],
        "country_id": ["country", "nation", "country code"],

        # Company/Organization
        "is_company": ["is company", "company flag", "organization", "is organization"],
        "company_name": ["company name", "business name", "organization name", "firm name"],
        "parent_id": ["parent", "parent company", "parent organization", "holding company"],
        "company_id": ["company", "organization", "entity", "business unit"],

        # Sales/Purchase
        "customer_rank": ["customer", "is customer", "client", "buyer", "customer status", "customer flag"],
        "supplier_rank": ["supplier", "vendor", "is vendor", "is supplier", "provider", "vendor status"],
        "user_id": ["salesperson", "sales rep", "account manager", "sales person", "assigned to", "owner"],

        # Financial
        "property_account_receivable_id": ["receivable account", "ar account", "customer account"],
        "property_account_payable_id": ["payable account", "ap account", "vendor account"],
        "credit_limit": ["credit limit", "credit line", "max credit"],

        # Other
        "active": ["active", "status", "enabled", "is active"],
        "comment": ["notes", "comments", "remarks", "internal notes", "memo"],
        "vat": ["vat", "tax id", "tax number", "tin", "vat number", "tax identification"],
        "ref": ["reference", "code", "customer code", "vendor code", "partner ref", "external ref", "customer id", "vendor id"],
        "lang": ["language", "lang", "locale", "preferred language"],
        "tz": ["timezone", "time zone", "tz"],
        "industry_id": ["segment", "market segment", "customer segment", "industry", "business segment", "market", "sector"],

        # Custom Fields (commonly used)
        "x_annual_revenue": ["annual revenue", "yearly revenue", "annual sales", "revenue", "yearly sales"],
    },

    # ===================== PRODUCTS (product.product / product.template) =====================
    "product.product": {
        # Basic Information
        "name": ["product", "item", "article", "product name", "item name", "description", "product description"],
        "default_code": ["sku", "code", "product code", "item code", "reference", "internal reference", "part number", "product ref", "item number"],
        "barcode": ["barcode", "ean", "ean13", "upc", "gtin", "bar code", "product barcode"],

        # Pricing - Sales
        "list_price": ["price", "sale price", "selling price", "retail price", "list price", "unit price", "sales price"],

        # Pricing - Cost
        "standard_price": ["cost", "cost price", "purchase price", "standard price", "unit cost", "buying price", "manufacturing price", "production cost", "production price", "manufacturing cost", "cogs", "cost of goods sold", "cost of sales", "product cost"],

        # Product Details
        "type": ["type", "product type", "item type"],
        "categ_id": ["category", "product category", "item category", "product group", "item group", "segment"],
        "uom_id": ["uom", "unit", "unit of measure", "measurement", "unit of measurement"],
        "uom_po_id": ["purchase uom", "purchase unit", "vendor uom", "buying unit"],

        # Stock
        "qty_available": ["quantity", "qty", "stock", "on hand", "quantity on hand", "available qty", "units sold"],
        "virtual_available": ["forecasted", "forecasted quantity", "projected qty", "future stock"],

        # Sales/Purchase
        "sale_ok": ["can be sold", "sellable", "for sale", "saleable"],
        "purchase_ok": ["can be purchased", "purchasable", "for purchase"],
        "active": ["active", "enabled", "status", "is active"],

        # Other
        "weight": ["weight", "product weight", "item weight", "mass"],
        "volume": ["volume", "product volume", "item volume"],
        "description": ["description", "long description", "detailed description"],
        "description_sale": ["sale description", "customer description", "sales description"],
        "description_purchase": ["purchase description", "vendor description", "supplier description"],
    },

    # ===================== SALES ORDERS (sale.order) =====================
    "sale.order": {
        # Basic Information
        "name": ["order", "order number", "so number", "reference", "order reference", "sale order", "order no"],
        "date_order": ["date", "order date", "sale date", "created date", "order created", "transaction date", "date order", "sales date"],
        "state": ["status", "state", "order status", "order state"],

        # Customer
        "partner_id": ["customer", "client", "buyer", "partner", "customer name", "client name", "account"],
        "partner_invoice_id": ["invoice address", "billing address", "bill to", "invoice to"],
        "partner_shipping_id": ["delivery address", "shipping address", "ship to", "deliver to"],

        # Sales Info
        "user_id": ["salesperson", "sales rep", "account manager", "sales person", "assigned to"],
        "team_id": ["sales team", "team", "sales channel", "department"],
        "pricelist_id": ["pricelist", "price list", "pricing"],

        # Terms
        "payment_term_id": ["payment terms", "payment term", "terms", "payment conditions"],
        "validity_date": ["validity", "expiry", "expiration", "valid until", "quote validity"],
        "commitment_date": ["delivery date", "commitment", "promised date", "expected delivery"],

        # Financial
        "amount_untaxed": ["subtotal", "net amount", "untaxed amount", "amount before tax"],
        "amount_tax": ["tax", "tax amount", "vat", "taxes"],
        "amount_total": ["total", "grand total", "total amount", "gross amount"],

        # Other
        "note": ["notes", "comments", "remarks", "internal notes"],
        "client_order_ref": ["customer po", "customer reference", "client reference", "po number"],
        "tag_ids": ["tags", "labels", "categories"],
        "campaign_id": ["campaign", "marketing campaign"],
        "source_id": ["source", "lead source", "origin"],
        "medium_id": ["medium", "channel"],
    },

    "sale.order.line": {
        # Order Reference
        "order_id": ["order", "order number", "so number", "sale order", "order reference", "order no"],

        # Product Information
        "product_id": ["product", "item", "sku", "article", "product name"],
        "name": ["description", "line description", "item description"],

        # Quantity & Unit
        "product_uom_qty": ["quantity", "qty", "amount", "units", "ordered qty", "units sold", "quantity sold", "sales quantity", "volume sold"],
        "product_uom": ["uom", "unit", "unit of measure"],
        "qty_delivered": ["delivered qty", "shipped qty", "quantity delivered"],

        # Pricing
        "price_unit": ["unit price", "price", "rate", "unit cost", "sale price", "selling price"],
        "discount": ["discount", "disc", "reduction", "discount %", "discount amount", "discounts", "total discounts", "discount value", "discount band"],

        # Amounts
        "price_subtotal": ["subtotal", "line total", "amount", "line amount", "gross sales", "total sales", "sales amount", "revenue", "gross revenue", "net sales", "sales after discount"],
        "price_total": ["total", "line total with tax", "gross total"],

        # Cost & Margin
        "purchase_price": ["cost", "purchase price", "cost price", "manufacturing price", "production cost", "cogs", "cost of goods sold"],
        "margin": ["margin", "profit", "gross profit", "profit margin"],

        # Tax
        "tax_id": ["tax", "taxes", "vat", "tax rate"],
    },

    # ===================== INVOICES (account.move) =====================
    "account.move": {
        # Basic Information
        "name": ["invoice", "invoice number", "bill number", "reference", "number", "invoice no"],
        "move_type": ["type", "invoice type", "document type"],
        "date": ["date", "invoice date", "bill date", "document date"],
        "invoice_date": ["invoice date", "date issued", "issue date"],
        "invoice_date_due": ["due date", "payment due", "maturity date", "payment date"],
        "state": ["status", "state", "invoice status", "payment status"],

        # Partner
        "partner_id": ["customer", "vendor", "partner", "supplier", "client"],
        "commercial_partner_id": ["commercial partner", "commercial entity"],

        # Financial
        "amount_untaxed": ["subtotal", "net amount", "untaxed amount", "amount before tax"],
        "amount_tax": ["tax", "tax amount", "vat", "taxes"],
        "amount_total": ["total", "grand total", "total amount", "gross amount"],
        "amount_residual": ["amount due", "balance", "outstanding", "remaining"],

        # References
        "ref": ["reference", "description", "communication", "memo"],
        "invoice_origin": ["origin", "source", "source document", "sale order"],
        "payment_reference": ["payment reference", "payment ref", "payment communication"],

        # Terms & Conditions
        "invoice_payment_term_id": ["payment terms", "payment term", "terms"],
        "currency_id": ["currency", "curr", "invoice currency"],

        # Other
        "narration": ["notes", "comments", "internal notes", "remarks"],
        "invoice_user_id": ["salesperson", "responsible", "account manager"],
    },

    # ===================== LEADS/OPPORTUNITIES (crm.lead) =====================
    "crm.lead": {
        # Basic Information
        "name": ["opportunity", "lead", "title", "opportunity name", "lead name", "deal name", "opportunity title"],
        "type": ["type", "lead type", "opportunity type"],
        "stage_id": ["stage", "pipeline stage", "sales stage", "lead stage", "lead status", "status"],

        # Contact Information
        "partner_id": ["customer", "contact", "partner", "account", "client"],
        "contact_name": ["contact name", "contact person", "contact"],
        "email_from": ["email", "contact email", "lead email", "from email"],
        "phone": ["phone", "telephone", "contact phone"],
        "mobile": ["mobile", "cell", "mobile phone"],

        # Address
        "street": ["street", "address", "street address"],
        "city": ["city", "town", "municipality"],
        "state_id": ["state", "province", "region"],
        "zip": ["zip", "postal code", "postcode"],
        "country_id": ["country", "nation"],

        # Sales Info
        "user_id": ["salesperson", "sales rep", "assigned to", "owner", "responsible"],
        "team_id": ["sales team", "team", "department"],
        "date_deadline": ["deadline", "expected closing", "close date", "expected close"],
        "priority": ["priority", "importance", "rating"],

        # Opportunity Details
        "expected_revenue": ["revenue", "expected revenue", "amount", "value", "deal value"],
        "recurring_revenue": ["recurring revenue", "mrr", "arr"],
        "probability": ["probability", "chance", "win probability", "success rate"],

        # Source
        "source_id": ["source", "lead source", "origin", "channel"],
        "campaign_id": ["campaign", "marketing campaign"],
        "medium_id": ["medium", "marketing medium"],
        "tag_ids": ["tags", "labels", "categories"],

        # Other
        "description": ["description", "notes", "details", "comments"],
        "date_open": ["open date", "created date", "opportunity date"],
        "day_open": ["days open", "age", "lead age"],
    },

    # ===================== PROJECTS (project.project) =====================
    "project.project": {
        "name": ["project", "project name", "title", "project title"],
        "partner_id": ["customer", "client", "partner"],
        "user_id": ["manager", "project manager", "responsible", "owner"],
        "date_start": ["start date", "start", "beginning date"],
        "date": ["end date", "deadline", "due date", "finish date"],
        "description": ["description", "notes", "details"],
        "active": ["active", "status", "enabled"],
    },

    "project.task": {
        "name": ["task", "task name", "title", "task title"],
        "project_id": ["project", "project name"],
        "user_id": ["assigned to", "assignee", "responsible", "owner"],
        "partner_id": ["customer", "client"],
        "date_deadline": ["deadline", "due date", "due"],
        "description": ["description", "notes", "details"],
        "priority": ["priority", "importance"],
        "kanban_state": ["status", "state", "kanban status"],
    },

    # ===================== ANALYTIC ACCOUNTING (account.analytic.line) =====================
    # Used for segment analysis, profit/margin tracking, cost center reporting
    "account.analytic.line": {
        # Basic Information
        "name": ["description", "name", "label", "entry", "reference"],
        "date": ["date", "transaction date", "entry date", "posting date", "period date", "reporting date"],

        # Segmentation & Cost Centers
        "account_id": ["account", "analytic account", "cost center", "segment", "market segment", "customer segment", "business segment", "market", "sector", "division"],
        "general_account_id": ["general account", "gl account", "account"],
        "partner_id": ["partner", "customer", "vendor", "supplier", "country"],

        # Financial Data - Revenue & Profit Analysis
        "amount": ["amount", "value", "total", "sales", "revenue", "gross sales", "net sales", "earnings", "net revenue", "sales after discount"],
        "unit_amount": ["quantity", "qty", "units", "units sold", "volume", "quantity sold", "sales quantity", "volume sold"],

        # Product Information
        "product_id": ["product", "item", "sku", "article"],
        "product_uom_id": ["uom", "unit", "unit of measure"],

        # Categorization & Tags
        "tag_ids": ["tags", "labels", "segment", "category", "market segment", "discount band", "discount tier", "discount level", "discount category"],

        # Company & Currency
        "company_id": ["company", "entity", "organization"],
        "currency_id": ["currency", "curr"],
        "user_id": ["user", "employee", "responsible"],

        # Custom Fields for Financial Reporting (commonly used)
        "x_cogs": ["cogs", "cost of goods sold", "cost of sales", "product cost", "manufacturing cost", "production cost"],
        "x_profit": ["profit", "net profit", "gross profit", "margin", "earnings"],

        # Note: For detailed financial reporting (COGS, discounts, prices), map to product.product or sale.order.line
        # Note: For time-based analysis (month, year), use 'date' field and transform in reporting layer
    },

    # ===================== FLEET MANAGEMENT (fleet.vehicle) =====================
    "fleet.vehicle": {
        # Vehicle Identification
        "vin": ["vin", "vehicle identification number", "chassis number", "serial number"],
        "license_plate": ["license", "license plate", "plate", "registration", "registration number", "license number", "plate number", "reg", "tag"],
        "model_id": ["model", "vehicle model", "car model", "make model", "vehicle type", "model name"],

        # Assignment
        "driver_id": ["driver", "assigned driver", "assigned to", "operator", "driver name"],

        # Dates & Tracking
        "acquisition_date": ["acquisition date", "purchase date", "bought", "bought date", "acquired", "date purchased", "purchase"],
        "odometer": ["odometer", "mileage", "miles", "km", "kilometers", "distance", "meter reading"],
        "odometer_unit": ["odometer unit", "mileage unit", "distance unit"],

        # Status & Info
        "active": ["active", "in service", "status", "enabled", "operational"],
        "state": ["state", "vehicle state", "condition"],

        # Financial
        "model_year": ["year", "model year", "year of manufacture", "manufacturing year"],
        "value": ["value", "vehicle value", "book value", "worth"],

        # Other
        "color": ["color", "colour", "vehicle color"],
        "doors": ["doors", "number of doors", "door count"],
        "seats": ["seats", "seating", "passengers", "capacity"],
        "fuel_type": ["fuel", "fuel type", "gas type", "power type"],
        "transmission": ["transmission", "gearbox", "gear type"],
        "location": ["location", "parking", "garage", "depot"],
        "notes": ["notes", "comments", "remarks", "description"],
    },
}

# Common field name normalizations
def normalize_field_name(field_name: str) -> str:
    """Normalize field names for better matching."""
    if not field_name:
        return ""

    # Convert to lowercase
    normalized = field_name.lower().strip()

    # Remove common prefixes/suffixes
    normalized = normalized.replace("_", " ")
    normalized = normalized.replace("-", " ")
    normalized = normalized.replace(".", " ")

    # Remove parentheses and their contents
    import re
    normalized = re.sub(r'\([^)]*\)', '', normalized).strip()

    # Common abbreviations
    abbreviations = {
        "amt": "amount",
        "qty": "quantity",
        "desc": "description",
        "addr": "address",
        "tel": "telephone",
        "num": "number",
        "ref": "reference",
        "cust": "customer",
        "prod": "product",
    }

    for abbr, full in abbreviations.items():
        if abbr in normalized.split():
            normalized = normalized.replace(abbr, full)

    return normalized.strip()


def get_best_match(header: str, model: str) -> tuple[str, float, str]:
    """
    Find the best matching field for a given header in a specific model.

    Returns: (field_name, confidence, rationale)
    """
    header_normalized = normalize_field_name(header)

    if not header_normalized or model not in ODOO_FIELD_MAPPINGS:
        return None, 0.0, "No suitable mapping found"

    model_fields = ODOO_FIELD_MAPPINGS[model]
    best_match = None
    best_score = 0.0
    best_rationale = ""

    for field_name, patterns in model_fields.items():
        for pattern in patterns:
            pattern_normalized = normalize_field_name(pattern)

            # Exact match
            if header_normalized == pattern_normalized:
                return field_name, 1.0, f"Exact match: '{header}' maps directly to {model}.{field_name}"

            # Contains match
            if pattern_normalized in header_normalized or header_normalized in pattern_normalized:
                score = 0.8
                if score > best_score:
                    best_score = score
                    best_match = field_name
                    best_rationale = f"Strong match: '{header}' contains pattern for {model}.{field_name}"

            # Word overlap
            header_words = set(header_normalized.split())
            pattern_words = set(pattern_normalized.split())
            common_words = header_words & pattern_words

            if common_words:
                score = len(common_words) / max(len(header_words), len(pattern_words))
                if score > best_score:
                    best_score = score
                    best_match = field_name
                    best_rationale = f"Partial match: '{header}' shares keywords with {model}.{field_name}"

    if best_match:
        return best_match, best_score, best_rationale

    return None, 0.0, "No suitable mapping found"


# Model detection based on sheet/context
def detect_model_from_context(sheet_name: str, column_names: list) -> str:
    """Detect the most likely Odoo model based on sheet name and column names."""
    sheet_lower = sheet_name.lower() if sheet_name else ""

    # Direct sheet name mapping
    sheet_model_map = {
        "customers": "res.partner",
        "contacts": "res.partner",
        "vendors": "res.partner",
        "suppliers": "res.partner",
        "partners": "res.partner",
        "products": "product.product",
        "items": "product.product",
        "inventory": "product.product",
        "sales": "sale.order",
        "orders": "sale.order",
        "sales orders": "sale.order",
        "invoices": "account.move",
        "bills": "account.move",
        "leads": "crm.lead",
        "opportunities": "crm.lead",
        "deals": "crm.lead",
        "projects": "project.project",
        "tasks": "project.task",
        "financial": "account.analytic.line",
        "analysis": "account.analytic.line",
        "report": "account.analytic.line",
        "sample": "account.analytic.line",  # For "Financial Sample" sheets
    }

    for pattern, model in sheet_model_map.items():
        if pattern in sheet_lower:
            return model

    # Analyze column names to detect model
    column_lower = [c.lower() for c in column_names if c]

    # Count model indicators
    model_scores = {}

    # Check for partner/contact indicators
    partner_indicators = ["customer", "vendor", "supplier", "partner", "contact", "company name", "email", "phone", "address", "street", "city", "state", "zip"]
    partner_score = sum(1 for col in column_lower for ind in partner_indicators if ind in col)
    if partner_score > 0:
        model_scores["res.partner"] = partner_score

    # Check for product indicators
    product_indicators = ["product", "sku", "barcode", "price", "cost", "unit", "quantity", "stock", "category"]
    product_score = sum(1 for col in column_lower for ind in product_indicators if ind in col)
    if product_score > 0:
        model_scores["product.product"] = product_score

    # Check for sales order indicators
    sale_indicators = ["order", "sale", "customer", "total", "subtotal", "tax", "delivery", "payment term"]
    sale_score = sum(1 for col in column_lower for ind in sale_indicators if ind in col)
    if sale_score > 0:
        model_scores["sale.order"] = sale_score

    # Check for lead/opportunity indicators
    lead_indicators = ["lead", "opportunity", "pipeline", "stage", "probability", "revenue", "campaign", "source"]
    lead_score = sum(1 for col in column_lower for ind in lead_indicators if ind in col)
    if lead_score > 0:
        model_scores["crm.lead"] = lead_score

    # Check for invoice indicators
    invoice_indicators = ["invoice", "bill", "due date", "payment", "amount due", "balance"]
    invoice_score = sum(1 for col in column_lower for ind in invoice_indicators if ind in col)
    if invoice_score > 0:
        model_scores["account.move"] = invoice_score

    # Check for financial analysis/reporting indicators (analytic accounting)
    financial_indicators = ["gross sales", "cogs", "profit", "margin", "discount band", "manufacturing price", "units sold", "segment", "month number", "month name", "year", "revenue", "cost of goods"]
    financial_score = sum(1 for col in column_lower for ind in financial_indicators if ind in col)
    if financial_score > 2:  # Need at least 3 indicators for financial analysis
        model_scores["account.analytic.line"] = financial_score * 1.5  # Prioritize analytic accounting for financial reporting

    # Return model with highest score
    if model_scores:
        return max(model_scores, key=model_scores.get)

    # Default to res.partner if no clear match
    return "res.partner"