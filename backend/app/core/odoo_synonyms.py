"""
Odoo field synonyms and common mappings for header matching.
"""

# Model synonyms - help identify which Odoo model a sheet represents
MODEL_HINTS = {
    "res.partner": [
        "customer", "customers", "client", "clients", "contact", "contacts",
        "partner", "partners", "vendor", "vendors", "supplier", "suppliers",
        "company", "companies", "account", "accounts"
    ],
    "crm.lead": [
        "lead", "leads", "opportunity", "opportunities", "prospect", "prospects",
        "inquiry", "inquiries", "quote", "quotes", "estimate", "estimates"
    ],
    "project.project": [
        "project", "projects", "job", "jobs", "contract", "contracts",
        "work order", "work orders"
    ],
    "project.task": [
        "task", "tasks", "activity", "activities", "todo", "todos",
        "action", "actions", "item", "items"
    ],
    "sale.order": [
        "order", "orders", "sale", "sales", "purchase order", "po", "sales order"
    ],
    "sale.order.line": [
        "order line", "order lines", "sale line", "sales line", "line item", "line items",
        "order item", "order items"
    ],
    "product.template": [
        "product", "products", "item", "items", "material", "materials",
        "service", "services", "inventory", "stock", "catalog"
    ],
    "account.move": [
        "invoice", "invoices", "bill", "bills", "credit note", "debit note",
        "payment", "vendor bill", "customer invoice"
    ],
    "account.move.line": [
        "invoice line", "invoice lines", "bill line", "line item"
    ],
    "purchase.order": [
        "purchase", "purchases", "po", "purchase order", "purchase orders",
        "procurement", "requisition"
    ],
    "purchase.order.line": [
        "purchase line", "purchase lines", "po line", "po lines"
    ],
    "hr.employee": [
        "employee", "employees", "worker", "workers", "staff", "personnel",
        "subcontractor", "subcontractors", "crew", "labor"
    ],
    "account.analytic.line": [
        "timesheet", "timesheets", "time entry", "time entries", "hours",
        "labor hours", "work log"
    ],
    "stock.picking": [
        "delivery", "deliveries", "shipment", "shipments", "receipt", "receipts",
        "transfer", "transfers", "picking"
    ],
    "res.users": [
        "user", "users", "login", "logins", "access"
    ],
    "account.payment": [
        "payment", "payments", "receipt", "disbursement"
    ],
}

# Field synonyms - common header names → Odoo field names
FIELD_SYNONYMS = {
    # res.partner fields
    "res.partner": {
        "name": [
            "name", "company name", "customer name", "client name", "contact name",
            "account name", "business name", "organization", "company", "customer",
            "client", "contact", "full name", "partner name"
        ],
        "email": [
            "email", "e-mail", "email address", "e-mail address", "mail",
            "contact email", "customer email", "primary email", "business email"
        ],
        "phone": [
            "phone", "telephone", "tel", "phone number", "telephone number",
            "contact phone", "business phone", "office phone", "work phone",
            "primary phone"
        ],
        "mobile": [
            "mobile", "cell", "cell phone", "mobile phone", "cellular",
            "contact mobile", "personal phone"
        ],
        "street": [
            "street", "address", "address 1", "address line 1", "street address",
            "address1", "addr1", "street 1", "location", "physical address"
        ],
        "street2": [
            "street2", "address 2", "address line 2", "address2", "addr2",
            "suite", "apartment", "apt", "unit", "floor"
        ],
        "city": [
            "city", "town", "municipality", "locality"
        ],
        "state_id": [
            "state", "province", "region", "state/province", "st"
        ],
        "zip": [
            "zip", "zipcode", "zip code", "postal", "postal code", "postcode"
        ],
        "country_id": [
            "country", "nation"
        ],
        "website": [
            "website", "web site", "url", "web", "homepage", "site"
        ],
        "vat": [
            "vat", "tax id", "tax number", "ein", "federal id", "tin"
        ],
        "ref": [
            "ref", "reference", "customer ref", "account ref", "external id", "code"
        ],
        "function": [
            "function", "job position", "title", "job title", "position", "role"
        ],
        "comment": [
            "comment", "notes", "internal notes", "memo", "remarks"
        ],
        "lang": [
            "lang", "language", "preferred language"
        ],
        "tz": [
            "tz", "timezone", "time zone"
        ],
        "title": [
            "title", "salutation", "prefix"
        ],
        "parent_id": [
            "parent", "parent company", "parent account", "related company"
        ],
        "user_id": [
            "salesperson", "sales rep", "account manager", "assigned to"
        ],
        "category_id": [
            "tags", "categories", "groups"
        ],
        "company_registry": [
            "company registry", "company id", "registration number"
        ],
        "active": [
            "active", "enabled", "status", "is active"
        ],
        "is_company": [
            "is company", "company", "type"
        ],
        "company_id": [
            "company"
        ],
        "company_name": [
            "company name", "business name"
        ],
        "industry_id": [
            "industry", "sector", "business type"
        ],
        "credit_limit": [
            "credit limit", "credit"
        ],
        "barcode": [
            "barcode", "customer barcode"
        ],
        "type": [
            "type", "address type", "contact type"
        ],
    },

    # crm.lead fields
    "crm.lead": {
        "name": [
            "name", "title", "lead title", "opportunity title", "subject",
            "lead name", "opportunity name", "description", "summary"
        ],
        "partner_name": [
            "partner name", "customer name", "contact name", "client name",
            "company name", "account name"
        ],
        "email_from": [
            "email", "contact email", "customer email", "lead email",
            "email address", "from email"
        ],
        "phone": [
            "phone", "telephone", "contact phone", "lead phone", "tel"
        ],
        "mobile": [
            "mobile", "cell", "cell phone", "mobile phone"
        ],
        "street": [
            "street", "address", "street address"
        ],
        "city": [
            "city", "town"
        ],
        "state_id": [
            "state", "province"
        ],
        "zip": [
            "zip", "postal code", "zipcode"
        ],
        "country_id": [
            "country"
        ],
        "priority": [
            "priority", "lead priority", "rating", "score", "lead score",
            "importance", "rank"
        ],
        "stage_id": [
            "stage", "status", "lead status", "opportunity status", "state"
        ],
        "user_id": [
            "salesperson", "sales rep", "owner", "assigned to", "responsible",
            "account manager", "sales manager"
        ],
        "team_id": [
            "sales team", "team"
        ],
        "source_id": [
            "source", "lead source", "campaign", "referral source", "origin"
        ],
        "description": [
            "description", "notes", "comments", "details", "memo"
        ],
        "expected_revenue": [
            "expected revenue", "estimated value", "opportunity value",
            "deal size", "revenue", "value"
        ],
        "probability": [
            "probability", "confidence", "likelihood", "win probability"
        ],
        "referred": [
            "referred", "referred by", "referral"
        ],
        "tag_ids": [
            "tags", "labels", "categories"
        ],
        "recurring_revenue": [
            "recurring revenue", "arr", "recurring", "subscription revenue"
        ],
        "recurring_plan": [
            "recurring plan", "subscription plan", "plan"
        ],
        "recurring_revenue_monthly": [
            "mrr", "monthly recurring revenue", "monthly revenue"
        ],
        "company_id": [
            "company"
        ],
        "color": [
            "color", "color index"
        ],
    },

    # project.project fields
    "project.project": {
        "name": [
            "name", "project name", "job name", "project title", "title",
            "job title", "project", "job"
        ],
        "partner_id": [
            "customer", "client", "customer name", "client name", "partner",
            "account", "company"
        ],
        "user_id": [
            "project manager", "manager", "owner", "responsible", "assigned to",
            "lead", "pm"
        ],
        "date_start": [
            "start date", "date start", "begin date", "start", "commenced"
        ],
        "date": [
            "end date", "date end", "completion date", "deadline", "due date",
            "finish date", "target date", "expiration date"
        ],
        "description": [
            "description", "notes", "details", "scope", "summary"
        ],
        "company_id": [
            "company"
        ],
        "tag_ids": [
            "tags", "labels", "categories"
        ],
        "privacy_visibility": [
            "visibility", "privacy", "access level"
        ],
        "color": [
            "color", "color index"
        ],
        "allow_task_dependencies": [
            "task dependencies", "dependencies"
        ],
        "allow_milestones": [
            "milestones"
        ],
        "label_tasks": [
            "task label", "use tasks as"
        ],
    },

    # project.task fields
    "project.task": {
        "name": [
            "name", "task name", "title", "subject", "task", "activity"
        ],
        "project_id": [
            "project", "project name", "job", "job name"
        ],
        "user_ids": [
            "assigned to", "assignee", "assignees", "owner", "responsible", "assigned"
        ],
        "date_deadline": [
            "deadline", "due date", "target date", "completion date", "due"
        ],
        "description": [
            "description", "notes", "details", "task details"
        ],
        "priority": [
            "priority", "importance", "urgency"
        ],
        "stage_id": [
            "stage", "status", "state"
        ],
        "partner_id": [
            "customer", "client", "customer name"
        ],
        "company_id": [
            "company"
        ],
        "parent_id": [
            "parent", "parent task"
        ],
        "child_ids": [
            "subtasks", "sub-tasks", "child tasks"
        ],
        "tag_ids": [
            "tags", "labels"
        ],
        "allocated_hours": [
            "allocated hours", "estimated hours", "planned hours", "hours"
        ],
        "milestone_id": [
            "milestone"
        ],
        "date_assign": [
            "assigned date", "date assigned", "assignment date"
        ],
        "date_end": [
            "end date", "date end", "completion date"
        ],
        "recurring_task": [
            "recurring", "recurrent", "repeating"
        ],
    },

    # sale.order fields
    "sale.order": {
        "name": [
            "name", "order reference", "order number", "order ref", "so number", "reference"
        ],
        "partner_id": [
            "customer", "client", "customer name", "client name", "partner"
        ],
        "state": [
            "state", "status", "order status"
        ],
        "locked": [
            "locked", "is locked"
        ],
        "client_order_ref": [
            "client order ref", "customer reference", "po number", "customer po"
        ],
        "date_order": [
            "order date", "date", "date order", "created date"
        ],
        "commitment_date": [
            "commitment date", "delivery date", "promised date"
        ],
        "validity_date": [
            "validity date", "expiration", "expiration date", "valid until"
        ],
        "user_id": [
            "salesperson", "sales rep", "sales person", "assigned to"
        ],
        "team_id": [
            "sales team", "team"
        ],
        "partner_invoice_id": [
            "invoice address", "billing address", "bill to"
        ],
        "partner_shipping_id": [
            "shipping address", "delivery address", "ship to"
        ],
        "payment_term_id": [
            "payment terms", "payment term", "terms"
        ],
        "pricelist_id": [
            "pricelist", "price list"
        ],
        "currency_id": [
            "currency"
        ],
        "currency_rate": [
            "currency rate", "exchange rate"
        ],
        "company_id": [
            "company"
        ],
        "origin": [
            "origin", "source document", "source"
        ],
        "reference": [
            "reference", "payment ref"
        ],
        "note": [
            "note", "notes", "terms and conditions", "terms", "comments"
        ],
        "amount_untaxed": [
            "subtotal", "amount before tax", "net amount"
        ],
        "amount_tax": [
            "tax", "tax amount"
        ],
        "amount_total": [
            "total", "total amount", "grand total"
        ],
        "require_signature": [
            "require signature", "online signature", "signature required"
        ],
        "require_payment": [
            "require payment", "online payment", "payment required"
        ],
        "prepayment_percent": [
            "prepayment percent", "deposit percent", "down payment"
        ],
        "signed_by": [
            "signed by", "signer"
        ],
        "signed_on": [
            "signed on", "signature date"
        ],
        "fiscal_position_id": [
            "fiscal position", "tax position"
        ],
        "journal_id": [
            "journal", "invoicing journal"
        ],
        "campaign_id": [
            "campaign", "marketing campaign", "utm campaign"
        ],
        "medium_id": [
            "medium", "utm medium"
        ],
        "source_id": [
            "source", "utm source", "lead source"
        ],
        "tag_ids": [
            "tags", "labels"
        ],
        "invoice_status": [
            "invoice status", "invoicing status"
        ],
    },

    # sale.order.line fields
    "sale.order.line": {
        "order_id": [
            "order", "sales order", "so", "order reference"
        ],
        "product_id": [
            "product", "item", "material", "service", "sku", "product code"
        ],
        "name": [
            "name", "description", "item description", "product description", "line description"
        ],
        "product_uom_qty": [
            "quantity", "qty", "amount", "order quantity", "ordered qty"
        ],
        "price_unit": [
            "price", "unit price", "rate", "cost", "price each"
        ],
        "discount": [
            "discount", "discount %", "discount percent"
        ],
        "tax_id": [
            "tax", "taxes", "tax rate", "vat"
        ],
        "price_subtotal": [
            "subtotal", "line total", "amount", "total"
        ],
        "product_uom": [
            "uom", "unit", "unit of measure", "um"
        ],
        "sequence": [
            "sequence", "line number", "order", "position"
        ],
    },

    # product.template fields
    "product.template": {
        "name": [
            "name", "product name", "item name", "title", "description", "product"
        ],
        "type": [
            "type", "product type", "item type"
        ],
        "categ_id": [
            "category", "product category", "item category", "group"
        ],
        "list_price": [
            "list price", "sale price", "selling price", "price", "retail price", "unit price"
        ],
        "standard_price": [
            "cost", "cost price", "standard price", "unit cost", "purchase price"
        ],
        "description": [
            "description", "long description", "details", "notes"
        ],
        "description_sale": [
            "sales description", "description for sales", "sale description"
        ],
        "description_purchase": [
            "purchase description", "description for purchase", "vendor description"
        ],
        "uom_id": [
            "uom", "unit", "unit of measure", "um"
        ],
        "uom_po_id": [
            "purchase uom", "po uom", "purchase unit"
        ],
        "sale_ok": [
            "can be sold", "saleable", "for sale"
        ],
        "purchase_ok": [
            "can be purchased", "purchaseable", "for purchase"
        ],
        "weight": [
            "weight", "unit weight"
        ],
        "volume": [
            "volume", "cubic volume"
        ],
        "barcode": [
            "barcode", "ean", "upc", "scan code"
        ],
        "default_code": [
            "internal reference", "sku", "item code", "product code", "reference"
        ],
        "active": [
            "active", "enabled", "status", "is active"
        ],
        "sequence": [
            "sequence", "order", "sort order", "priority"
        ],
        "company_id": [
            "company"
        ],
        "taxes_id": [
            "customer taxes", "sales taxes", "taxes"
        ],
        "supplier_taxes_id": [
            "vendor taxes", "purchase taxes", "supplier taxes"
        ],
        "service_tracking": [
            "service tracking", "tracking"
        ],
        "rental": [
            "rental", "is rental", "rent"
        ],
    },

    # account.move fields
    "account.move": {
        "name": [
            "name", "number", "invoice number", "bill number", "reference"
        ],
        "ref": [
            "ref", "reference", "vendor reference", "customer ref"
        ],
        "date": [
            "date", "accounting date", "entry date"
        ],
        "invoice_date": [
            "invoice date", "bill date", "document date"
        ],
        "invoice_date_due": [
            "due date", "payment due", "date due"
        ],
        "partner_id": [
            "partner", "customer", "vendor", "supplier", "contact"
        ],
        "commercial_partner_id": [
            "commercial partner", "parent partner", "main partner"
        ],
        "move_type": [
            "type", "move type", "document type", "invoice type"
        ],
        "state": [
            "state", "status"
        ],
        "amount_total": [
            "total", "total amount", "grand total", "amount"
        ],
        "amount_untaxed": [
            "subtotal", "amount untaxed", "net amount", "before tax"
        ],
        "amount_tax": [
            "tax", "tax amount", "total tax"
        ],
        "invoice_origin": [
            "origin", "source document", "order reference"
        ],
        "invoice_payment_term_id": [
            "payment terms", "payment term", "terms"
        ],
        "journal_id": [
            "journal", "accounting journal"
        ],
        "company_id": [
            "company"
        ],
        "currency_id": [
            "currency"
        ],
        "fiscal_position_id": [
            "fiscal position", "tax position"
        ],
        "invoice_user_id": [
            "salesperson", "invoice user", "sales rep"
        ],
        "partner_bank_id": [
            "bank account", "partner bank", "payment account"
        ],
        "payment_reference": [
            "payment reference", "payment ref", "check number"
        ],
        "invoice_incoterm_id": [
            "incoterm", "shipping terms"
        ],
        "narration": [
            "notes", "internal notes", "narration", "memo"
        ],
        "invoice_source_email": [
            "source email", "from email"
        ],
        "partner_shipping_id": [
            "shipping address", "delivery address", "ship to"
        ],
        "auto_post": [
            "auto post", "automatic posting"
        ],
        "to_check": [
            "to check", "needs review"
        ],
    },

    # account.move.line fields
    "account.move.line": {
        "move_id": [
            "move", "invoice", "bill", "document"
        ],
        "product_id": [
            "product", "item", "material", "service"
        ],
        "name": [
            "name", "description", "label", "line description"
        ],
        "quantity": [
            "quantity", "qty", "amount"
        ],
        "price_unit": [
            "price", "unit price", "rate", "cost"
        ],
        "price_subtotal": [
            "subtotal", "amount", "line total"
        ],
        "account_id": [
            "account", "gl account", "ledger account"
        ],
        "tax_ids": [
            "tax", "taxes", "tax codes"
        ],
        "discount": [
            "discount", "discount %"
        ],
    },

    # purchase.order fields
    "purchase.order": {
        "name": [
            "name", "po number", "purchase order", "reference", "number"
        ],
        "partner_id": [
            "vendor", "supplier", "partner", "contact"
        ],
        "partner_ref": [
            "vendor reference", "supplier ref", "vendor po"
        ],
        "date_order": [
            "order date", "date", "po date", "purchase date"
        ],
        "date_approve": [
            "approval date", "approved date", "date approved"
        ],
        "date_planned": [
            "planned date", "expected date", "delivery date"
        ],
        "state": [
            "state", "status", "po status"
        ],
        "origin": [
            "origin", "source document", "reference"
        ],
        "notes": [
            "notes", "terms", "remarks", "comments"
        ],
        "amount_total": [
            "total", "total amount", "grand total"
        ],
        "amount_untaxed": [
            "subtotal", "amount before tax", "net amount"
        ],
        "currency_id": [
            "currency"
        ],
        "user_id": [
            "buyer", "purchaser", "responsible", "assigned to"
        ],
    },

    # purchase.order.line fields
    "purchase.order.line": {
        "order_id": [
            "order", "po", "purchase order"
        ],
        "product_id": [
            "product", "item", "material", "service"
        ],
        "name": [
            "name", "description", "product description"
        ],
        "product_qty": [
            "quantity", "qty", "ordered qty", "amount"
        ],
        "price_unit": [
            "price", "unit price", "cost", "rate"
        ],
        "price_subtotal": [
            "subtotal", "line total", "amount"
        ],
        "product_uom": [
            "uom", "unit", "unit of measure"
        ],
        "date_planned": [
            "planned date", "expected date", "delivery date", "receipt date"
        ],
        "taxes_id": [
            "tax", "taxes", "tax rate"
        ],
    },

    # hr.employee fields
    "hr.employee": {
        "name": [
            "name", "employee name", "full name"
        ],
        "user_id": [
            "user", "login", "system user"
        ],
        "department_id": [
            "department", "dept", "division"
        ],
        "job_id": [
            "job", "job position", "title", "role"
        ],
        "work_email": [
            "email", "work email", "business email", "company email"
        ],
        "work_phone": [
            "phone", "work phone", "office phone", "business phone"
        ],
        "mobile_phone": [
            "mobile", "cell", "mobile phone", "cell phone"
        ],
        "work_location": [
            "location", "work location", "office", "site"
        ],
        "employee_type": [
            "type", "employee type", "employment type"
        ],
        "company_id": [
            "company"
        ],
        "country_id": [
            "country", "nationality"
        ],
        "identification_id": [
            "id", "employee id", "badge", "identification"
        ],
        "passport_id": [
            "passport", "passport number"
        ],
        "gender": [
            "gender", "sex"
        ],
        "birthday": [
            "birthday", "birth date", "date of birth", "dob"
        ],
        "coach_id": [
            "manager", "supervisor", "coach", "reports to"
        ],
    },

    # account.analytic.line (timesheets) fields
    "account.analytic.line": {
        "name": [
            "name", "description", "task description", "notes"
        ],
        "project_id": [
            "project", "job"
        ],
        "task_id": [
            "task", "activity"
        ],
        "employee_id": [
            "employee", "worker", "staff", "resource"
        ],
        "user_id": [
            "user", "assigned to"
        ],
        "date": [
            "date", "work date", "timesheet date"
        ],
        "unit_amount": [
            "hours", "time", "duration", "qty", "quantity"
        ],
        "amount": [
            "amount", "cost", "total"
        ],
        "account_id": [
            "account", "analytic account"
        ],
    },

    # stock.picking fields
    "stock.picking": {
        "name": [
            "name", "reference", "delivery order", "receipt", "transfer"
        ],
        "partner_id": [
            "partner", "customer", "vendor", "contact"
        ],
        "location_id": [
            "source location", "from location", "origin"
        ],
        "location_dest_id": [
            "destination location", "to location", "destination"
        ],
        "scheduled_date": [
            "scheduled date", "expected date", "planned date", "delivery date"
        ],
        "date_done": [
            "done date", "completion date", "actual date"
        ],
        "state": [
            "state", "status"
        ],
        "picking_type_id": [
            "operation type", "picking type", "type"
        ],
        "origin": [
            "origin", "source document", "reference"
        ],
        "note": [
            "note", "notes", "remarks"
        ],
    },

    # res.users fields
    "res.users": {
        "name": [
            "name", "user name", "full name"
        ],
        "login": [
            "login", "username", "user id", "email"
        ],
        "email": [
            "email", "email address", "contact email"
        ],
        "phone": [
            "phone", "telephone", "contact phone"
        ],
        "mobile": [
            "mobile", "cell phone"
        ],
        "company_id": [
            "company"
        ],
        "company_ids": [
            "companies", "allowed companies"
        ],
        "lang": [
            "language", "lang"
        ],
        "tz": [
            "timezone", "time zone"
        ],
        "active": [
            "active", "enabled", "status"
        ],
    },

    # account.payment fields
    "account.payment": {
        "name": [
            "name", "number", "reference", "payment reference"
        ],
        "date": [
            "date", "payment date"
        ],
        "amount": [
            "amount", "payment amount", "total"
        ],
        "partner_id": [
            "partner", "customer", "vendor", "contact"
        ],
        "payment_type": [
            "type", "payment type"
        ],
        "journal_id": [
            "journal", "payment journal", "bank"
        ],
        "payment_method_id": [
            "payment method", "method"
        ],
        "ref": [
            "ref", "reference", "memo", "note"
        ],
        "state": [
            "state", "status"
        ],
        "currency_id": [
            "currency"
        ],
    },
}


def get_model_from_sheet_name(sheet_name: str) -> str:
    """Guess Odoo model from sheet name."""
    sheet_lower = sheet_name.lower()

    for model, hints in MODEL_HINTS.items():
        for hint in hints:
            if hint in sheet_lower:
                return model

    return "res.partner"  # Default fallback


def get_field_synonyms(model: str, field: str) -> list[str]:
    """Get list of synonyms for a given model.field."""
    if model in FIELD_SYNONYMS and field in FIELD_SYNONYMS[model]:
        return FIELD_SYNONYMS[model][field]
    return []


def get_all_fields_for_model(model: str) -> dict[str, list[str]]:
    """Get all field mappings for a model."""
    return FIELD_SYNONYMS.get(model, {})
