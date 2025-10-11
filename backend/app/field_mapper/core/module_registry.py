"""
Odoo Module Registry - Defines module groups and their associated models.

This registry helps users pre-select relevant modules to dramatically improve
field mapping accuracy by reducing the search space.
"""
from typing import Dict, List, Set
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ModuleGroup:
    """Represents a group of related Odoo modules."""
    name: str
    display_name: str
    description: str
    models: List[str]
    icon: str = "📦"  # Default icon
    priority: int = 100  # Lower number = higher priority


class OdooModuleRegistry:
    """
    Registry of Odoo module groups and their associated models.

    This helps filter the 520+ Odoo models down to just the relevant ones
    based on the user's business needs.
    """

    # Define module groups with their associated models
    MODULE_GROUPS = [
        ModuleGroup(
            name="sales_crm",
            display_name="Sales & CRM",
            description="Sales orders, quotations, leads, opportunities",
            models=[
                "sale.order",
                "sale.order.line",
                "crm.lead",
                "crm.team",
                "sale.advance.payment.inv",
                "crm.stage",
            ],
            icon="💼",
            priority=10
        ),
        ModuleGroup(
            name="accounting",
            display_name="Accounting & Finance",
            description="Invoices, bills, payments, financial analysis",
            models=[
                "account.move",
                "account.move.line",
                "account.payment",
                "account.bank.statement",
                "account.bank.statement.line",
                "account.analytic.line",
                "account.analytic.account",
                "account.journal",
                "account.account",
                "account.tax",
            ],
            icon="💰",
            priority=20
        ),
        ModuleGroup(
            name="contacts",
            display_name="Contacts & Partners",
            description="Customers, vendors, contacts, addresses",
            models=[
                "res.partner",
                "res.partner.bank",
                "res.partner.category",
                "res.partner.title",
                "res.partner.industry",
            ],
            icon="👥",
            priority=5  # High priority - most common
        ),
        ModuleGroup(
            name="products",
            display_name="Products & Inventory",
            description="Products, pricing, categories, stock levels",
            models=[
                "product.product",
                "product.template",
                "product.category",
                "product.pricelist",
                "product.pricelist.item",
                "product.supplierinfo",
                "product.attribute",
                "product.attribute.value",
            ],
            icon="📦",
            priority=15
        ),
        ModuleGroup(
            name="inventory",
            display_name="Warehouse & Stock",
            description="Stock movements, locations, picking, transfers",
            models=[
                "stock.quant",
                "stock.move",
                "stock.move.line",
                "stock.picking",
                "stock.location",
                "stock.warehouse",
                "stock.inventory",
                "stock.production.lot",
            ],
            icon="🏭",
            priority=30
        ),
        ModuleGroup(
            name="purchase",
            display_name="Purchasing",
            description="Purchase orders, vendor bills, RFQs",
            models=[
                "purchase.order",
                "purchase.order.line",
                "purchase.requisition",
                "purchase.requisition.line",
                "supplier.info",
            ],
            icon="🛒",
            priority=25
        ),
        ModuleGroup(
            name="hr",
            display_name="Human Resources",
            description="Employees, departments, attendance, leaves",
            models=[
                "hr.employee",
                "hr.department",
                "hr.job",
                "hr.attendance",
                "hr.leave",
                "hr.contract",
                "hr.employee.category",
            ],
            icon="👔",
            priority=40
        ),
        ModuleGroup(
            name="project",
            display_name="Projects & Tasks",
            description="Projects, tasks, timesheets, planning",
            models=[
                "project.project",
                "project.task",
                "project.task.type",
                "project.tags",
                "account.analytic.line",  # Also for timesheets
            ],
            icon="📋",
            priority=35
        ),
        ModuleGroup(
            name="manufacturing",
            display_name="Manufacturing",
            description="Bill of materials, work orders, production",
            models=[
                "mrp.production",
                "mrp.bom",
                "mrp.bom.line",
                "mrp.workorder",
                "mrp.workcenter",
                "mrp.routing",
            ],
            icon="🏗️",
            priority=45
        ),
        ModuleGroup(
            name="pos",
            display_name="Point of Sale",
            description="POS orders, sessions, payments",
            models=[
                "pos.order",
                "pos.order.line",
                "pos.session",
                "pos.payment",
                "pos.config",
            ],
            icon="🛍️",
            priority=50
        ),
        ModuleGroup(
            name="website",
            display_name="Website & eCommerce",
            description="Website pages, products, visitors, carts",
            models=[
                "website",
                "website.page",
                "website.visitor",
                "website.track",
                "sale.order",  # For ecommerce orders
                "product.template",  # For website products
            ],
            icon="🌐",
            priority=55
        ),
        ModuleGroup(
            name="marketing",
            display_name="Marketing & Communication",
            description="Email/SMS campaigns, events, surveys",
            models=[
                "mailing.mailing",
                "mailing.list",
                "mailing.list.contact",
                "mailing.contact",
                "mailing.contact.subscription",
                "mailing.trace",
                "sms.sms",
                "sms.template",
                "event.event",
                "event.registration",
                "event.type",
                "event.stage",
                "survey.survey",
                "survey.question",
                "survey.question.answer",
                "survey.user_input",
                "survey.user_input_line",
            ],
            icon="📣",
            priority=60
        ),
        ModuleGroup(
            name="maintenance",
            display_name="Maintenance",
            description="Equipment registers, maintenance requests",
            models=[
                "maintenance.equipment",
                "maintenance.equipment.category",
                "maintenance.request",
                "maintenance.stage",
                "maintenance.team",
            ],
            icon="🛠️",
            priority=65
        ),
        ModuleGroup(
            name="fleet",
            display_name="Fleet Management",
            description="Company vehicles, odometers, fuel logs",
            models=[
                "fleet.vehicle",
                "fleet.vehicle.odometer",
                "fleet.vehicle.log.fuel",
                "fleet.vehicle.log.services",
                "fleet.vehicle.model",
                "fleet.vehicle.model.brand",
            ],
            icon="🚗",
            priority=70
        ),
        ModuleGroup(
            name="recruitment",
            display_name="Recruitment",
            description="Applicants, job positions, recruitment stages",
            models=[
                "hr.applicant",
                "hr.applicant.category",
                "hr.recruitment.stage",
                "hr.job",
                "hr.recruitment.source",
            ],
            icon="🧑‍💼",
            priority=42
        ),
        ModuleGroup(
            name="expenses",
            display_name="Expenses & Approvals",
            description="Expense reports, sheets, approvals",
            models=[
                "hr.expense",
                "hr.expense.sheet",
                "hr.expense.approver",
            ],
            icon="🧾",
            priority=44
        ),
        ModuleGroup(
            name="skills",
            display_name="Employee Skills",
            description="Skills, levels, employee competencies",
            models=[
                "hr.skill",
                "hr.skill.level",
                "hr.employee.skill",
                "hr.employee.skill.log",
            ],
            icon="🧠",
            priority=46
        ),
        ModuleGroup(
            name="calendar",
            display_name="Calendar & Meetings",
            description="Meetings, attendees, reminders",
            models=[
                "calendar.event",
                "calendar.event.type",
                "calendar.attendee",
                "calendar.alarm",
            ],
            icon="🗓️",
            priority=75
        ),
        ModuleGroup(
            name="notes",
            display_name="Notes & To-Do",
            description="Personal notes, stages, tags",
            models=[
                "note.note",
                "note.stage",
                "note.tag",
            ],
            icon="📝",
            priority=80
        ),
        ModuleGroup(
            name="lunch",
            display_name="Lunch Management",
            description="Lunch products, orders, alerts",
            models=[
                "lunch.product",
                "lunch.order",
                "lunch.alert",
                "lunch.supplier",
            ],
            icon="🥗",
            priority=85
        ),
        ModuleGroup(
            name="discuss_livechat",
            display_name="Discuss & Live Chat",
            description="Internal channels, live chat sessions",
            models=[
                "mail.channel",
                "mail.message",
                "mail.channel.partner",
                "im_livechat.channel",
                "im_livechat.channel.rule",
                "im_livechat.message",
            ],
            icon="💬",
            priority=90
        ),
        ModuleGroup(
            name="data_cleaning",
            display_name="Data Cleaning & Recycle",
            description="Deduplication and recycle rules",
            models=[
                "data.cleaning.model",
                "data.cleaning.operation",
                "data.cleaning.rule",
                "data.recycle",
            ],
            icon="♻️",
            priority=95
        ),
    ]

    def __init__(self):
        """Initialize the module registry."""
        self._groups_by_name = {g.name: g for g in self.MODULE_GROUPS}
        self._build_model_index()
        logger.info(f"Module registry initialized with {len(self.MODULE_GROUPS)} groups")

    def _build_model_index(self):
        """Build reverse index: model -> groups."""
        self._model_to_groups = {}
        for group in self.MODULE_GROUPS:
            for model in group.models:
                if model not in self._model_to_groups:
                    self._model_to_groups[model] = []
                self._model_to_groups[model].append(group.name)

    def get_all_groups(self) -> List[ModuleGroup]:
        """Get all available module groups sorted by priority."""
        return sorted(self.MODULE_GROUPS, key=lambda g: g.priority)

    def get_group(self, name: str) -> ModuleGroup:
        """Get a specific module group by name."""
        return self._groups_by_name.get(name)

    def get_models_for_groups(self, group_names: List[str]) -> Set[str]:
        """
        Get all models for the specified groups.

        Args:
            group_names: List of group names (e.g., ["sales_crm", "contacts"])

        Returns:
            Set of model names
        """
        models = set()
        for group_name in group_names:
            group = self.get_group(group_name)
            if group:
                models.update(group.models)
                logger.debug(f"Added {len(group.models)} models from group '{group_name}'")

        logger.info(f"Selected groups {group_names} provide {len(models)} models")
        return models

    def suggest_groups_for_columns(self, column_names: List[str]) -> List[str]:
        """
        Suggest module groups based on column names.

        Args:
            column_names: List of column names from the spreadsheet

        Returns:
            List of suggested group names
        """
        suggestions = set()
        column_names_lower = [c.lower() for c in column_names]

        # Keywords that suggest specific modules
        keywords_map = {
            "sales_crm": ["sale", "order", "customer", "quotation", "lead", "opportunity"],
            "accounting": ["invoice", "bill", "payment", "tax", "account", "journal", "debit", "credit"],
            "contacts": ["customer", "vendor", "supplier", "contact", "partner", "email", "phone", "address"],
            "products": ["product", "item", "sku", "price", "category", "description"],
            "inventory": ["stock", "quantity", "warehouse", "location", "lot", "serial"],
            "purchase": ["purchase", "vendor", "supplier", "po", "rfq"],
            "hr": ["employee", "department", "salary", "leave", "attendance"],
            "project": ["project", "task", "timesheet", "hours", "milestone"],
            "manufacturing": ["bom", "manufacturing", "workorder", "routing", "production"],
            "pos": ["pos", "point of sale", "session", "receipt", "cashier"],
            "website": ["website", "ecommerce", "cart", "visitor"],
            "marketing": ["campaign", "mailing", "newsletter", "event", "registration", "survey", "marketing"],
            "maintenance": ["equipment", "maintenance", "repair"],
            "fleet": ["vehicle", "odometer", "fuel", "fleet", "driver"],
            "recruitment": ["applicant", "application", "recruitment", "job position"],
            "expenses": ["expense", "receipt", "reimbursement"],
            "skills": ["skill", "competency", "certification"],
            "calendar": ["meeting", "calendar", "attendee", "appointment"],
            "notes": ["note", "todo", "task list"],
            "lunch": ["lunch", "meal", "canteen"],
            "discuss_livechat": ["chat", "channel", "conversation", "livechat"],
            "data_cleaning": ["deduplicate", "duplicate", "cleanup", "recycle"],
        }

        for group_name, keywords in keywords_map.items():
            for keyword in keywords:
                if any(keyword in col for col in column_names_lower):
                    suggestions.add(group_name)
                    break

        # Always suggest contacts if we see common contact fields
        contact_fields = ["name", "email", "phone", "address", "city", "country"]
        if any(field in column_names_lower for field in contact_fields):
            suggestions.add("contacts")

        suggested_list = list(suggestions)
        logger.info(f"Suggested module groups based on columns: {suggested_list}")
        return suggested_list

    def get_models_for_domain(self, domain: str) -> Set[str]:
        """
        Get models for a business domain detected by BusinessContextAnalyzer.

        Args:
            domain: Business domain name

        Returns:
            Set of relevant model names
        """
        domain_map = {
            "sales_revenue": ["sales_crm", "products", "accounting"],
            "financial_analysis": ["accounting"],
            "inventory": ["inventory", "products"],
            "customer_contacts": ["contacts", "sales_crm"],
            "hr_timesheet": ["hr", "project"],
            "purchase_orders": ["purchase", "contacts", "products"],
            "invoices": ["accounting", "contacts"],
        }

        group_names = domain_map.get(domain, [])
        return self.get_models_for_groups(group_names) if group_names else set()

    def filter_models_by_selection(self, all_models: Set[str], selected_groups: List[str]) -> Set[str]:
        """
        Filter a set of models to only include those in selected groups.

        Args:
            all_models: Set of all model names
            selected_groups: List of selected group names

        Returns:
            Filtered set of models
        """
        if not selected_groups:
            return all_models

        allowed_models = self.get_models_for_groups(selected_groups)
        filtered = all_models & allowed_models

        logger.info(f"Filtered {len(all_models)} models to {len(filtered)} based on selected groups")
        return filtered


# Singleton instance
_registry = None


def get_module_registry() -> OdooModuleRegistry:
    """Get the singleton module registry instance."""
    global _registry
    if _registry is None:
        _registry = OdooModuleRegistry()
    return _registry
