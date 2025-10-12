"""
Ground Truth Mappings for MESSY Matcher Validation

This file defines the expected (correct) field mappings for test cases with MESSY column names.
This represents real-world data quality issues like:
- Parenthetical suffixes: " (Contact)", " (All)", " (Opp)"
- Special characters: *, ?, #, ...
- Extra whitespace
- Mixed formatting

Format:
    GROUND_TRUTH_MESSY = {
        "test_case_name": {
            "Column Name (Messy)": ("odoo.model", "field_name"),
            ...
        }
    }
"""

GROUND_TRUTH_MESSY = {
    # ===================== CUSTOMERS TEST (WITH MESSY NAMES) =====================
    "customers_messy": {
        "Customer Name*": ("res.partner", "name"),
        "Contact Email...": ("res.partner", "email"),
        "Phone #": ("res.partner", "phone"),
        "Street Address (Main)": ("res.partner", "street"),
        "City (Billing)": ("res.partner", "city"),
        "State?": ("res.partner", "state_id"),
        "Zip Code...": ("res.partner", "zip"),
        "Annual Revenue (USD)": ("res.partner", "x_annual_revenue"),
        "Customer ID*": ("res.partner", "ref"),
    },

    # ===================== PRODUCTS TEST (WITH MESSY NAMES) =====================
    "products_messy": {
        "Product Name...": ("product.product", "name"),
        "SKU*": ("product.product", "default_code"),
        "Sale Price?": ("product.product", "list_price"),
        "Cost Price (Internal)": ("product.product", "standard_price"),
        "Category*": ("product.product", "categ_id"),
        "Barcode #": ("product.product", "barcode"),
        "Active?": ("product.product", "active"),
    },

    # ===================== SALES ORDERS TEST (WITH MESSY NAMES) =====================
    "sales_orders_messy": {
        "Order Number*": ("sale.order", "name"),
        "Customer (Main)": ("sale.order", "partner_id"),
        "Order Date...": ("sale.order", "date_order"),
        "Total Amount?": ("sale.order", "amount_total"),
        "Status (Current)": ("sale.order", "state"),
        "Salesperson (Assigned)": ("sale.order", "user_id"),
    },

    # ===================== INVOICES TEST (WITH MESSY NAMES) =====================
    "invoices_messy": {
        "Invoice Number*": ("account.move", "name"),
        "Customer (Billing)": ("account.move", "partner_id"),
        "Invoice Date...": ("account.move", "invoice_date"),
        "Due Date (Payment)": ("account.move", "invoice_date_due"),
        "Subtotal?": ("account.move", "amount_untaxed"),
        "Tax Amount*": ("account.move", "amount_tax"),
        "Total...": ("account.move", "amount_total"),
        "Status (Current)": ("account.move", "state"),
    },

    # ===================== LEADS TEST (WITH MESSY NAMES) =====================
    "leads_messy": {
        "Opportunity Title*": ("crm.lead", "name"),
        "Email (Contact)": ("crm.lead", "email_from"),
        "Phone #": ("crm.lead", "phone"),
        "Street Address (Contact)": ("crm.lead", "street"),
        "City (Contact)": ("crm.lead", "city"),
        "Zip (Contact)": ("crm.lead", "zip"),
        "Lead Status...": ("crm.lead", "stage_id"),
        "Salesperson (Owner)": ("crm.lead", "user_id"),
        "Source?": ("crm.lead", "source_id"),
        "Expected Revenue (USD)": ("crm.lead", "expected_revenue"),
    },

    # ===================== PROJECTS TEST (WITH MESSY NAMES) =====================
    "projects_messy": {
        "Project Name*": ("project.project", "name"),
        "Customer (Main)": ("project.project", "partner_id"),
        "Project Manager (Assigned)": ("project.project", "user_id"),
        "Start Date...": ("project.project", "date_start"),
        "Deadline (Target)": ("project.project", "date"),
        "Active?": ("project.project", "active"),
    },

    # ===================== TASKS TEST (WITH MESSY NAMES) =====================
    "tasks_messy": {
        "Task Title...": ("project.task", "name"),
        "Project (Parent)": ("project.task", "project_id"),
        "Assigned To (User)": ("project.task", "user_id"),
        "Due Date*": ("project.task", "date_deadline"),
        "Priority Level?": ("project.task", "priority"),
        "Status (Kanban)": ("project.task", "kanban_state"),
    },

    # ===================== VEHICLES TEST (WITH MESSY NAMES) =====================
    "vehicles_messy": {
        "VIN #": ("fleet.vehicle", "vin"),
        "License Plate...": ("fleet.vehicle", "license_plate"),
        "Vehicle Model (Year)": ("fleet.vehicle", "model_id"),
        "Driver (Assigned)": ("fleet.vehicle", "driver_id"),
        "Acquisition Date*": ("fleet.vehicle", "acquisition_date"),
        "Odometer Reading (Miles)": ("fleet.vehicle", "odometer"),
        "Active?": ("fleet.vehicle", "active"),
    },

    # ===================== SALE ORDER LINES TEST (WITH MESSY NAMES) =====================
    "sale_order_lines_messy": {
        "Order Number*": ("sale.order.line", "order_id"),
        "Product (Item)": ("sale.order.line", "product_id"),
        "Description...": ("sale.order.line", "name"),
        "Quantity (Ordered)": ("sale.order.line", "product_uom_qty"),
        "Unit Price?": ("sale.order.line", "price_unit"),
        "Discount %*": ("sale.order.line", "discount"),
        "Subtotal (Net)": ("sale.order.line", "price_subtotal"),
    },

    # ===================== FINANCIAL ANALYSIS TEST (WITH MESSY NAMES) =====================
    "financial_analysis_messy": {
        "Date (Transaction)": ("account.analytic.line", "date"),
        "Product*": ("account.analytic.line", "product_id"),
        "Segment (Market)": ("account.analytic.line", "account_id"),
        "Country (Region)": ("account.analytic.line", "partner_id"),
        "Units Sold...": ("account.analytic.line", "unit_amount"),
        "Revenue (Gross)?": ("account.analytic.line", "amount"),
        "COGS*": ("account.analytic.line", "x_cogs"),
        "Profit (Net)": ("account.analytic.line", "x_profit"),
        "Discount Band (Tier)": ("account.analytic.line", "tag_ids"),
    },
}


# Import clean ground truth for comparison
from ground_truth import ACCURACY_THRESHOLDS, get_threshold, is_critical

# Messy tests use same thresholds but with "_messy" suffix
def get_messy_threshold(test_case_name: str) -> float:
    """Get the accuracy threshold for a messy test case."""
    # Remove "_messy" suffix if present
    clean_name = test_case_name.replace("_messy", "")
    return get_threshold(clean_name)


def is_messy_critical(test_case_name: str) -> bool:
    """Check if a messy test case is critical."""
    clean_name = test_case_name.replace("_messy", "")
    return is_critical(clean_name)
