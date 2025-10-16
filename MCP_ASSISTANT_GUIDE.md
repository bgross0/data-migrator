# Data Migrator AI Assistant (via MCP)

## Overview

The Data Migrator now includes an **AI Assistant** powered by Claude Code and MCP (Model Context Protocol). This assistant can help you navigate data migration tasks, suggest field mappings, explain Odoo models, and more - all through natural conversation.

## Key Features

✅ **Context-Aware Help** - The assistant knows what datasets you have and can examine your actual data
✅ **Safe & Read-Only** - Cannot modify your data or execute imports without your approval
✅ **Explains Reasoning** - Shows you why it makes specific recommendations
✅ **Odoo Expert** - Understands Odoo 18 models, fields, and relationships
✅ **Template Guide** - Recommends import templates based on your needs

## How It Works

The AI assistant uses **MCP (Model Context Protocol)** to safely access your Data Migrator API. It has 11 read-only tools that let it:

- View your datasets and sample data (max 20 rows)
- Look up Odoo model definitions
- Check current field mappings
- List available templates and transforms

**Important:** The assistant only **reads** data and **suggests** actions. You still control all actual operations through the UI.

## Setup

### Prerequisites
1. Data Migrator backend running on `http://localhost:8888`
2. Claude Code extension installed in VSCode
3. This workspace open in VSCode

### Enabling the Assistant

The MCP server is already configured in `.vscode/mcp.json`. To activate it:

1. **Reload VSCode Window**
   - Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
   - Type "Developer: Reload Window"
   - Press Enter

2. **Verify MCP Server is Running**
   - Open Claude Code chat
   - Type: "Are you connected to the Data Migrator MCP server?"
   - Claude should confirm it has access to the tools

## Example Conversations

### Getting Started

**You:** "What datasets do I have?"

**Assistant:** "Let me check..."
```
[Calls list_datasets tool]
```
**Assistant:** "You have 3 datasets:
1. Customer List (uploaded 2 days ago) - 5 sheets, 1,234 rows
2. Sales Orders (uploaded yesterday) - 2 sheets, 567 rows
3. Products (uploaded today) - 1 sheet, 89 rows

Which one would you like to work with?"

---

### Field Mapping Help

**You:** "I uploaded a customer spreadsheet but I'm not sure how to map the columns"

**Assistant:** "I'll take a look at your data..."
```
[Calls get_dataset_info to see structure]
[Calls get_dataset_preview to see sample rows]
```
**Assistant:** "I can see your spreadsheet has these columns:
- customer_name → Should map to `res.partner.name`
- email_address → Maps to `res.partner.email`
- phone_num → Maps to `res.partner.phone` (I recommend adding 'phone_normalize' transform)
- company_name → Maps to `res.partner.company_name`
- city, state, zip → Map to `res.partner.city`, `res.partner.state_id`, `res.partner.zip`

Would you like me to explain any of these fields in more detail?"

---

### Understanding Odoo Models

**You:** "What is res.partner and what fields does it have?"

**Assistant:**
```
[Calls get_odoo_field_info("res.partner")]
```
**Assistant:** "`res.partner` is Odoo's central model for contacts - it stores customers, vendors, and companies. Key fields:

**Required:**
- `name` (string) - Contact name

**Contact Info:**
- `email` (email) - Email address
- `phone` (phone) - Phone number
- `mobile` (phone) - Mobile number

**Address:**
- `street`, `street2` (string) - Address lines
- `city` (string) - City
- `state_id` (many2one → res.country.state) - State/province
- `zip` (string) - Postal code
- `country_id` (many2one → res.country) - Country

**Business:**
- `is_company` (boolean) - Is this a company or individual?
- `customer_rank` (integer) - Customer ranking
- `supplier_rank` (integer) - Supplier ranking

Would you like details on any specific field?"

---

### Template Recommendations

**You:** "I need to import customer data, sales orders, and products. What's the best way?"

**Assistant:**
```
[Calls list_templates]
```
**Assistant:** "For your needs, I recommend the **'Sales & CRM'** template. It includes:

1. **Customers** (res.partner) - Import first
2. **Products** (product.template, product.product) - Import second
3. **Sales Orders** (sale.order, sale.order.line) - Import last

This template handles dependencies automatically - customers and products must exist before sales orders reference them.

**Estimated time:** 15-30 minutes
**Difficulty:** Beginner

Would you like me to explain the import order or show you the steps?"

---

### Data Quality Issues

**You:** "I'm getting errors when importing. Can you help?"

**Assistant:** "Let me examine your data..."
```
[Calls get_dataset_preview]
[Calls get_current_mappings]
```
**Assistant:** "I found a few issues:

1. **Phone numbers** - You have mixed formats like '+1 (555) 123-4567' and '555.123.4567'. Add the 'phone_normalize' transform to fix this.

2. **Email addresses** - Some have extra spaces. Use 'email_normalize' transform.

3. **Missing required field** - The `name` field in res.partner is required, but your 'customer_name' column has 3 empty values (rows 45, 67, 103).

Would you like me to explain how to apply these transforms?"

---

### Transform Suggestions

**You:** "What data transforms are available?"

**Assistant:**
```
[Calls get_available_transforms]
```
**Assistant:** "Available transforms:

**Text Cleaning:**
- `trim` - Remove leading/trailing whitespace
- `lower` - Convert to lowercase
- `upper` - Convert to uppercase
- `titlecase` - Capitalize first letter of each word

**Normalization:**
- `phone_normalize` - Standardize phone numbers (+15551234567)
- `email_normalize` - Lowercase and trim email addresses
- `currency_to_float` - Convert '$1,234.56' → 1234.56

**Name Handling:**
- `split_name` - Split 'John Doe' → first_name='John', last_name='Doe'
- `concat` - Combine multiple columns

**Advanced:**
- `regex_extract` - Extract patterns with regex
- Custom transforms via Lambda mappings

Which one would you like details on?"

## Available Tools

The assistant has access to these read-only tools:

| Tool | Purpose |
|------|---------|
| `list_datasets` | Show all uploaded datasets |
| `get_dataset_info` | Get dataset structure and metadata |
| `get_dataset_preview` | View sample rows (max 20) |
| `list_templates` | Show available import templates |
| `get_template_details` | Get template steps and prerequisites |
| `get_odoo_models` | List available Odoo models |
| `get_odoo_field_info` | Get field definitions for a model |
| `get_current_mappings` | View existing field mappings |
| `get_available_transforms` | List data transformation functions |
| `check_api_health` | Verify API connectivity |

## Tips for Best Results

### Be Specific
❌ "Help me with my data"
✅ "I have a customer spreadsheet with name, email, and phone columns. How should I map these to Odoo?"

### Provide Context
❌ "What's this error?"
✅ "I'm importing to res.partner and getting a 'required field missing' error on row 45. Can you help?"

### Ask Follow-Up Questions
The assistant remembers context within a conversation, so you can ask:
- "Can you explain that field in more detail?"
- "What about the other columns?"
- "Show me an example of how to use that transform"

### Request Explanations
- "Why do you recommend this mapping?"
- "What's the difference between customer_rank and is_customer?"
- "Explain the import order for this template"

## Limitations

**What the Assistant CAN do:**
✅ Read your data and provide recommendations
✅ Explain Odoo models and relationships
✅ Suggest field mappings and transforms
✅ Guide you through templates
✅ Help troubleshoot issues

**What the Assistant CANNOT do:**
❌ Modify your data or mappings
❌ Execute imports
❌ Access sensitive data (passwords, API keys)
❌ Read more than 20 rows at a time
❌ Write to the database

## Troubleshooting

### "MCP server not responding"

1. Check backend is running:
   ```bash
   curl http://localhost:8888/api/v1/health
   ```

2. Reload VSCode window:
   - `Ctrl+Shift+P` → "Developer: Reload Window"

3. Check MCP server logs in VSCode Output panel

### "Tools not showing"

1. Verify `.vscode/mcp.json` exists in workspace root
2. Ensure Python path is correct in config
3. Reload VSCode window

### "API connection errors"

1. Start the backend:
   ```bash
   cd backend
   source venv/bin/activate
   uvicorn app.main:app --reload --port 8888
   ```

2. Verify API responds:
   ```bash
   curl http://localhost:8888/api/v1/datasets
   ```

## Privacy & Security

- **Local Only** - MCP server runs on your machine, no external network access
- **Read-Only** - Cannot modify data, only reads via API
- **No Secrets** - Doesn't access passwords, API keys, or sensitive configuration
- **Sample Limits** - Data previews limited to 20 rows to prevent overwhelming responses
- **User Control** - All actions require your approval through the UI

## Feedback & Improvements

To suggest new assistant capabilities:
1. Open an issue in the repository
2. Describe what kind of help would be useful
3. We can add new tools to the MCP server

Example suggestions:
- "Detect duplicate records in dataset"
- "Suggest default values for missing fields"
- "Explain import failures in detail"
- "Recommend data cleaning steps"

---

**Ready to try it?** Ask Claude Code: "What datasets do I have?" and start exploring!
