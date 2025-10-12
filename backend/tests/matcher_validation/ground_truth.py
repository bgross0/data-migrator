"""
Ground Truth Mappings for Matcher Validation

This file defines the expected (correct) field mappings for test cases.
Each test case maps column names to (model, field) tuples.

Format:
    GROUND_TRUTH = {
        "test_case_name": {
            "Column Name": ("odoo.model", "field_name"),
            ...
        }
    }
"""

GROUND_TRUTH = {
    # ===================== CUSTOMERS TEST =====================
    "customers": {
        "Customer Name": ("res.partner", "name"),
        "Contact Email": ("res.partner", "email"),
        "Phone": ("res.partner", "phone"),
        "Street Address": ("res.partner", "street"),
        "City": ("res.partner", "city"),
        "State": ("res.partner", "state_id"),
        "Zip Code": ("res.partner", "zip"),
        "Annual Revenue": ("res.partner", "x_annual_revenue"),  # Custom field
        "Customer ID": ("res.partner", "ref"),
    },

    # ===================== PRODUCTS TEST =====================
    "products": {
        "Product Name": ("product.product", "name"),
        "SKU": ("product.product", "default_code"),
        "Sale Price": ("product.product", "list_price"),
        "Cost Price": ("product.product", "standard_price"),
        "Category": ("product.product", "categ_id"),
        "Barcode": ("product.product", "barcode"),
        "Active": ("product.product", "active"),
    },

    # ===================== SALES ORDERS TEST =====================
    "sales_orders": {
        "Order Number": ("sale.order", "name"),
        "Customer": ("sale.order", "partner_id"),
        "Order Date": ("sale.order", "date_order"),
        "Total": ("sale.order", "amount_total"),
        "Status": ("sale.order", "state"),
        "Salesperson": ("sale.order", "user_id"),
    },

    # ===================== LEADS TEST =====================
    "leads": {
        "Opportunity Title": ("crm.lead", "name"),
        "Email": ("crm.lead", "email_from"),
        "Phone": ("crm.lead", "phone"),
        "Street Address (Contact)": ("crm.lead", "street"),
        "City (Contact)": ("crm.lead", "city"),
        "Zip (Contact)": ("crm.lead", "zip"),
        "Lead Status": ("crm.lead", "stage_id"),
        "Salesperson": ("crm.lead", "user_id"),
        "Source": ("crm.lead", "source_id"),
        "Expected Revenue": ("crm.lead", "expected_revenue"),
    },

    # ===================== INVOICES TEST =====================
    "invoices": {
        "Invoice Number": ("account.move", "name"),
        "Customer": ("account.move", "partner_id"),
        "Invoice Date": ("account.move", "invoice_date"),
        "Due Date": ("account.move", "invoice_date_due"),
        "Subtotal": ("account.move", "amount_untaxed"),
        "Tax": ("account.move", "amount_tax"),
        "Total": ("account.move", "amount_total"),
        "Status": ("account.move", "state"),
    },

    # ===================== PROJECTS TEST =====================
    "projects": {
        "Project Name": ("project.project", "name"),
        "Customer": ("project.project", "partner_id"),
        "Project Manager": ("project.project", "user_id"),
        "Start Date": ("project.project", "date_start"),
        "Deadline": ("project.project", "date"),
        "Active": ("project.project", "active"),
    },

    # ===================== TASKS TEST =====================
    "tasks": {
        "Task Title": ("project.task", "name"),
        "Project": ("project.task", "project_id"),
        "Assigned To": ("project.task", "user_id"),
        "Due Date": ("project.task", "date_deadline"),
        "Priority": ("project.task", "priority"),
        "Status": ("project.task", "kanban_state"),
    },

    # ===================== VEHICLES TEST (Fleet Management) =====================
    "vehicles": {
        "VIN": ("fleet.vehicle", "vin"),
        "License Plate": ("fleet.vehicle", "license_plate"),
        "Vehicle Model": ("fleet.vehicle", "model_id"),
        "Driver": ("fleet.vehicle", "driver_id"),
        "Acquisition Date": ("fleet.vehicle", "acquisition_date"),
        "Odometer": ("fleet.vehicle", "odometer"),
        "Active": ("fleet.vehicle", "active"),
    },

    # ===================== SALE ORDER LINES TEST =====================
    "sale_order_lines": {
        "Order Number": ("sale.order.line", "order_id"),
        "Product": ("sale.order.line", "product_id"),
        "Description": ("sale.order.line", "name"),
        "Quantity": ("sale.order.line", "product_uom_qty"),
        "Unit Price": ("sale.order.line", "price_unit"),
        "Discount": ("sale.order.line", "discount"),
        "Subtotal": ("sale.order.line", "price_subtotal"),
    },

    # ===================== FINANCIAL ANALYSIS TEST (Analytic Accounting) =====================
    "financial_analysis": {
        "Date": ("account.analytic.line", "date"),
        "Product": ("account.analytic.line", "product_id"),
        "Segment": ("account.analytic.line", "account_id"),
        "Country": ("account.analytic.line", "partner_id"),
        "Units Sold": ("account.analytic.line", "unit_amount"),
        "Revenue": ("account.analytic.line", "amount"),
        "COGS": ("account.analytic.line", "x_cogs"),  # Custom or computed field
        "Profit": ("account.analytic.line", "x_profit"),  # Custom or computed field
        "Discount Band": ("account.analytic.line", "tag_ids"),
    },
}


# Define which test cases are critical (must pass with high accuracy)
CRITICAL_TEST_CASES = [
    "customers",
    "products",
    "sales_orders",
]


# Define minimum accuracy thresholds per test case
ACCURACY_THRESHOLDS = {
    "customers": 0.90,  # 90% - critical, common use case
    "products": 0.90,  # 90% - critical, common use case
    "sales_orders": 0.85,  # 85% - critical but more complex
    "leads": 0.80,  # 80% - CRM is less standardized
    "invoices": 0.85,  # 85% - accounting needs precision
    "projects": 0.75,  # 75% - project management varies
    "tasks": 0.75,  # 75% - task fields can be ambiguous
    "vehicles": 0.80,  # 80% - fleet management is specialized
    "sale_order_lines": 0.85,  # 85% - important for transactions
    "financial_analysis": 0.70,  # 70% - complex analytical data
}


def get_threshold(test_case_name: str) -> float:
    """Get the accuracy threshold for a test case."""
    return ACCURACY_THRESHOLDS.get(test_case_name, 0.70)  # Default 70%


def is_critical(test_case_name: str) -> bool:
    """Check if a test case is critical."""
    return test_case_name in CRITICAL_TEST_CASES
