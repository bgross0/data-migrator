"""
AI Assistant API endpoints - Bridge between web chat and MCP tools
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
import httpx
import json
import subprocess
import asyncio
from app.core.database import get_db

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    response: str
    tools_used: Optional[list] = None
    suggestions: Optional[list] = None


@router.post("/assistant/chat", response_model=ChatResponse)
async def chat_with_assistant(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Process a chat message and return AI assistant response.

    This endpoint acts as a bridge between the web UI and MCP tools.
    It interprets the user's message and calls appropriate MCP tools.
    """

    message = request.message.lower()
    context = request.context or {}

    # Route to appropriate MCP tool based on message content
    response_text = ""
    tools_used = []
    suggestions = []

    try:
        # Analyze intent
        if "dataset" in message and ("list" in message or "what" in message or "show" in message):
            # Call list_datasets tool
            datasets = await call_mcp_tool("list_datasets")
            tools_used.append("list_datasets")

            if datasets and "datasets" in datasets:
                dataset_list = datasets["datasets"]
                if dataset_list:
                    response_text = f"You have {len(dataset_list)} dataset(s):\n"
                    for ds in dataset_list:
                        response_text += f"• {ds['name']} (ID: {ds['id']}) - {len(ds.get('sheets', []))} sheets\n"
                else:
                    response_text = "You haven't uploaded any datasets yet. Click 'Upload New File' to get started."
            else:
                response_text = "I couldn't retrieve your datasets. Make sure the backend is running."

        elif "template" in message:
            # Call list_templates tool
            templates = await call_mcp_tool("list_templates")
            tools_used.append("list_templates")

            if templates:
                response_text = "Available import templates:\n"
                for template in templates[:5]:  # Show top 5
                    response_text += f"• **{template['name']}** - {template['description']} ({template['modelCount']} models)\n"
                suggestions.append("Click on a template in the QuickStart section to begin")

        elif "map" in message or "mapping" in message:
            # Provide mapping guidance
            dataset_id = context.get("datasetId")

            if dataset_id:
                mappings = await call_mcp_tool("get_current_mappings", {"dataset_id": dataset_id})
                tools_used.append("get_current_mappings")

                if mappings:
                    response_text = "Here are your current mappings:\n"
                    # Parse and format mappings
                else:
                    response_text = "No mappings configured yet. "

                response_text += "\n\nTo map fields:\n"
                response_text += "1. Click on a column header\n"
                response_text += "2. Select the target Odoo field\n"
                response_text += "3. Apply any necessary transforms"

                suggestions.append("Use 'Generate Mappings' for automatic suggestions")

        elif "error" in message or "fail" in message or "problem" in message:
            # Analyze errors
            import_history = await call_mcp_tool("get_import_history", {"limit": 1})
            tools_used.append("get_import_history")

            if import_history and "runs" in import_history and import_history["runs"]:
                last_run = import_history["runs"][0]
                if last_run.get("status") == "failed":
                    response_text = f"Your last import failed. Common issues:\n"
                    response_text += "• Missing required fields - Make sure all required fields are mapped\n"
                    response_text += "• Invalid data formats - Apply appropriate transforms\n"
                    response_text += "• Duplicate records - Check for unique constraints\n"

                    if last_run.get("error_message"):
                        response_text += f"\nSpecific error: {last_run['error_message'][:200]}"
                else:
                    response_text = "Your last import was successful!"
            else:
                response_text = "No import history found. Make sure to map your fields and run an import."

        elif "field" in message and "res.partner" in message:
            # Get Odoo field info
            fields = await call_mcp_tool("get_odoo_field_info", {"model": "res.partner"})
            tools_used.append("get_odoo_field_info")

            response_text = "Key fields for res.partner (Contacts):\n"
            response_text += "• **name** (required) - Contact/company name\n"
            response_text += "• **email** - Email address\n"
            response_text += "• **phone** - Phone number\n"
            response_text += "• **street**, **city**, **zip** - Address fields\n"
            response_text += "• **is_company** - Set to true for companies\n"
            response_text += "• **customer_rank** - Set >0 for customers\n"
            response_text += "• **supplier_rank** - Set >0 for vendors"

        elif "transform" in message:
            # List transforms
            transforms = await call_mcp_tool("get_available_transforms")
            tools_used.append("get_available_transforms")

            response_text = "Available data transforms:\n"
            response_text += "• **trim** - Remove extra whitespace\n"
            response_text += "• **phone_normalize** - Format phone numbers\n"
            response_text += "• **email_normalize** - Clean email addresses\n"
            response_text += "• **currency_to_float** - Convert $1,234.56 to 1234.56\n"
            response_text += "• **split_name** - Split 'John Doe' into first/last\n"
            response_text += "• **titlecase** - Capitalize names properly"

            suggestions.append("Click the transform icon next to a field mapping to apply")

        elif "help" in message or "how" in message:
            # General help
            response_text = "I can help you with:\n\n"
            response_text += "📊 **Datasets** - 'Show my datasets', 'What data do I have?'\n"
            response_text += "🗂️ **Templates** - 'What templates are available?'\n"
            response_text += "🔄 **Mapping** - 'How do I map fields?', 'Help with mapping'\n"
            response_text += "📝 **Odoo Models** - 'What fields does res.partner have?'\n"
            response_text += "🔧 **Transforms** - 'What transforms are available?'\n"
            response_text += "❌ **Errors** - 'Why did my import fail?'\n\n"
            response_text += "Just ask me anything about your data migration!"

        else:
            # Default response with context-aware suggestions
            response_text = "I'm here to help with your data migration. You can ask me about:\n"
            response_text += "• Your datasets and their structure\n"
            response_text += "• Available import templates\n"
            response_text += "• Field mapping suggestions\n"
            response_text += "• Odoo model documentation\n"
            response_text += "• Troubleshooting import errors\n\n"
            response_text += "What would you like to know?"

            suggestions = [
                "Try: 'Show my datasets'",
                "Try: 'What templates are available?'",
                "Try: 'How do I map customer data?'"
            ]

    except Exception as e:
        response_text = f"I encountered an error while processing your request: {str(e)}\n"
        response_text += "Make sure the backend services are running."

    return ChatResponse(
        response=response_text,
        tools_used=tools_used if tools_used else None,
        suggestions=suggestions if suggestions else None
    )


async def call_mcp_tool(tool_name: str, params: Optional[Dict] = None) -> Dict:
    """
    Call an MCP tool via subprocess or HTTP.

    This is a simplified version - in production, you'd want to:
    1. Use a proper MCP client library
    2. Cache connections
    3. Handle streaming responses
    """

    # For now, directly call the API endpoints that MCP would call
    # This bypasses MCP but gives the same functionality

    BASE_URL = "http://localhost:8888/api/v1"

    async with httpx.AsyncClient() as client:
        try:
            if tool_name == "list_datasets":
                response = await client.get(f"{BASE_URL}/datasets")
                return response.json()

            elif tool_name == "list_templates":
                response = await client.get(f"{BASE_URL}/templates")
                return response.json()

            elif tool_name == "get_current_mappings" and params and "dataset_id" in params:
                response = await client.get(f"{BASE_URL}/datasets/{params['dataset_id']}/mappings")
                return response.json()

            elif tool_name == "get_import_history":
                limit = params.get("limit", 10) if params else 10
                response = await client.get(f"{BASE_URL}/runs", params={"limit": limit})
                return response.json()

            elif tool_name == "get_odoo_field_info" and params and "model" in params:
                response = await client.get(f"{BASE_URL}/odoo/models/{params['model']}/fields")
                return response.json()

            elif tool_name == "get_available_transforms":
                response = await client.get(f"{BASE_URL}/transforms/available")
                return response.json()

            else:
                return {"error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"error": str(e)}


@router.get("/assistant/suggestions")
async def get_contextual_suggestions(
    page: str,
    dataset_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get context-aware suggestions based on current page.
    """
    suggestions = []

    if page == "/":
        suggestions = [
            {"text": "Upload your first dataset", "action": "navigate", "target": "/upload"},
            {"text": "Explore templates", "action": "scroll", "target": "#quickstart"},
            {"text": "Learn about field mapping", "action": "help", "topic": "mapping"}
        ]
    elif page == "/upload":
        suggestions = [
            {"text": "Supported formats: CSV, Excel", "action": "info"},
            {"text": "Make sure first row contains headers", "action": "tip"},
            {"text": "Maximum file size: 100MB", "action": "info"}
        ]
    elif "/datasets/" in page and dataset_id:
        suggestions = [
            {"text": "Generate automatic mappings", "action": "button", "target": "generate_mappings"},
            {"text": "View data quality report", "action": "navigate", "target": f"/datasets/{dataset_id}/quality"},
            {"text": "Apply transforms to clean data", "action": "help", "topic": "transforms"}
        ]
    elif "/mappings" in page:
        suggestions = [
            {"text": "Required fields must be mapped", "action": "tip"},
            {"text": "Use transforms for data cleaning", "action": "help", "topic": "transforms"},
            {"text": "Check field types match", "action": "tip"}
        ]

    return {"suggestions": suggestions}