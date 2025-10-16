# Data Migrator MCP Server

This MCP (Model Context Protocol) server provides Claude Code with safe, read-only access to the Data Migrator API, allowing it to act as an intelligent assistant for users.

## What It Does

The MCP server exposes 11 read-only tools that Claude Code can use to help users:

### Dataset Tools
- `list_datasets` - Show all uploaded datasets
- `get_dataset_info` - Get dataset metadata and structure
- `get_dataset_preview` - View sample rows (max 20)

### Template Tools
- `list_templates` - Show available import templates
- `get_template_details` - Get template steps and recommendations

### Odoo Tools
- `get_odoo_models` - List available Odoo models
- `get_odoo_field_info` - Get field definitions for a model

### Mapping Tools
- `get_current_mappings` - View existing field mappings
- `get_available_transforms` - List data transformation functions

### Health
- `check_api_health` - Verify API is running

## Safety Features

✅ **Read-Only** - All tools only READ data, never modify it
✅ **Sample Limits** - Data previews limited to 20 rows maximum
✅ **No Execution** - Claude Code cannot run imports or modify mappings
✅ **User Control** - All actions require user approval via the UI

## Setup

The MCP server is automatically configured in `.vscode/mcp.json` for this workspace.

### Prerequisites
1. Backend API must be running on `http://localhost:8888`
2. Python 3.13+ with dependencies installed in `mcp-server/venv`

### Testing Manually

Start the MCP server:
```bash
cd mcp-server
source venv/bin/activate
python server.py
```

The server will start and wait for MCP requests from Claude Code.

## Usage Examples

Once configured, you can ask Claude Code questions like:

**"What datasets do I have?"**
```
Claude will call list_datasets() and show you a formatted list
```

**"Show me a sample of dataset 5"**
```
Claude will call get_dataset_info(5) and get_dataset_preview(5)
to show structure and sample data
```

**"What templates are available for accounting?"**
```
Claude will call list_templates() and filter by category
```

**"What fields does res.partner have?"**
```
Claude will call get_odoo_field_info("res.partner") and
explain the fields in plain English
```

**"How should I map my customer data?"**
```
Claude will:
1. Call get_dataset_preview() to see your columns
2. Call get_odoo_field_info("res.partner") to see target fields
3. Provide specific mapping recommendations with reasoning
```

## Architecture

```
Claude Code (VSCode Extension)
    ↓ (MCP Protocol)
MCP Server (server.py)
    ↓ (HTTP/JSON)
Data Migrator Backend API (localhost:8888)
    ↓
SQLite Database + Odoo
```

## Troubleshooting

**"MCP server not responding"**
- Check backend is running: `curl http://localhost:8888/api/v1/health`
- Check MCP server logs in VSCode Output panel
- Verify Python path in `.vscode/mcp.json` is correct

**"Tools not showing in Claude Code"**
- Reload VSCode window (Ctrl+Shift+P → "Developer: Reload Window")
- Check `.vscode/mcp.json` syntax is valid
- Ensure MCP server is in workspace root

**"API errors"**
- Verify backend API is accessible
- Check API responses with: `curl http://localhost:8888/api/v1/datasets`

## Adding New Tools

To add a new read-only tool:

1. Add function to `server.py`:
```python
@mcp.tool()
async def my_new_tool(param: str) -> dict:
    """Tool description for Claude"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/my-endpoint")
        return response.json()
```

2. Restart MCP server (reload VSCode window)
3. Claude Code will automatically discover the new tool

## Security Notes

- MCP server only listens for stdio communication (not network)
- Cannot be accessed remotely
- All tools are read-only by design
- No sensitive data (passwords, API keys) is exposed
- Sample limits prevent overwhelming responses

## Future Enhancements

Potential tools to add:
- `suggest_mappings` - AI-powered mapping suggestions
- `detect_data_issues` - Quality analysis
- `explain_error` - Help debug failed imports
- `recommend_transforms` - Suggest data cleaning steps
