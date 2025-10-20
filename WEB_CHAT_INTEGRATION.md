# Web-Based AI Chat Integration

## Overview
We've added a **web-based AI chat interface** directly in the Data Migrator frontend, so users can get help without switching to VSCode/Cursor.

## Architecture

```
User Browser (localhost:5173)
    ↓
React Chat Component (AIChat.tsx)
    ↓ (HTTP API calls)
FastAPI Assistant Endpoint (/api/v1/assistant/chat)
    ↓ (Calls MCP tools internally)
Data Migrator Backend
    ↓
Database
```

## Components Added

### Frontend

#### 1. **AIChat Component** (`frontend/src/components/AIChat.tsx`)
- Floating chat widget (bottom-right corner)
- Minimizable/closable interface
- Message history with timestamps
- Quick action buttons
- Context-aware (knows current page)
- Typing indicators

#### 2. **Layout Integration**
- Chat widget added to main Layout
- Available on ALL pages
- Persists across navigation

### Backend

#### 3. **Assistant API** (`backend/app/api/assistant.py`)
- `/api/v1/assistant/chat` - Main chat endpoint
- `/api/v1/assistant/suggestions` - Context-aware suggestions
- Intent routing to appropriate MCP tools
- Response formatting for web display

## User Experience

### How Users Access It

1. **Floating Button** - Blue chat icon in bottom-right corner
2. **Click to Open** - Expands to chat interface
3. **Type Questions** - Natural language queries
4. **Get Instant Help** - AI responds with context-aware assistance

### Visual Design

```
┌────────────────────────────────────┐
│  Data Migrator Web App             │
│                                     │
│  [Main Content Area]                │
│                                     │
│                    ┌──────────────┐ │
│                    │ AI Assistant │ │
│                    │              │ │
│                    │ User: Help!  │ │
│                    │              │ │
│                    │ AI: I can... │ │
│                    │              │ │
│                    │ [Send]       │ │
│                    └──────────────┘ │
│                           💬        │
└────────────────────────────────────┘
```

## Features

### 1. **Context Awareness**
- Knows what page user is on
- Provides page-specific help
- Can reference current dataset

### 2. **Quick Actions**
- "Field Mapping" button
- "Templates" button
- "Debug Error" button

### 3. **Intent Recognition**
Handles queries like:
- "Show my datasets"
- "What templates are available?"
- "How do I map fields?"
- "Why did my import fail?"
- "What fields does res.partner have?"

### 4. **Tool Integration**
Internally calls MCP tools:
- `list_datasets`
- `list_templates`
- `get_current_mappings`
- `get_import_history`
- `get_odoo_field_info`
- `get_available_transforms`

## Example Interactions

### Dataset Query
```
User: "What datasets do I have?"
AI: "You have 3 dataset(s):
     • Customer List (ID: 1) - 2 sheets
     • Products (ID: 2) - 1 sheet
     • Sales Orders (ID: 3) - 3 sheets"
```

### Mapping Help
```
User: "How do I map customer data?"
AI: "To map fields:
     1. Click on a column header
     2. Select the target Odoo field
     3. Apply any necessary transforms

     Tip: Use 'Generate Mappings' for automatic suggestions"
```

### Error Debugging
```
User: "Why did my import fail?"
AI: "Your last import failed. Common issues:
     • Missing required fields - Make sure all required fields are mapped
     • Invalid data formats - Apply appropriate transforms
     • Duplicate records - Check for unique constraints

     Specific error: Missing required field 'name'"
```

## Installation Notes

### Frontend Requirements
```bash
npm install lucide-react  # For icons
```

### Backend Requirements
- No new dependencies (uses existing httpx)
- Assistant router added to main.py

## Security Considerations

✅ **Safe Design**
- All MCP tools remain read-only
- No direct database modifications
- User must perform actions in UI

✅ **Context Isolation**
- Each chat session is isolated
- No cross-user data leakage
- API authentication ready (when added)

## Future Enhancements

1. **Streaming Responses** - Real-time token streaming
2. **File Uploads** - Drag & drop CSV samples
3. **Visual Aids** - Inline charts and diagrams
4. **Voice Input** - Speech-to-text queries
5. **Export Chat** - Save conversation history
6. **Multi-language** - Support other languages
7. **Custom Actions** - Deep-link to UI actions

## Testing the Chat

1. Start backend:
```bash
cd backend
uvicorn app.main:app --port 8888
```

2. Start frontend:
```bash
cd frontend
npm run dev
```

3. Open browser to `http://localhost:5173`
4. Click blue chat icon (bottom-right)
5. Type: "Show my datasets"

## Comparison: MCP vs Web Chat

| Feature | MCP (VSCode) | Web Chat |
|---------|--------------|----------|
| **Access** | Need VSCode open | Direct in browser |
| **Context** | Full codebase | Current page/dataset |
| **Tools** | 20+ MCP tools | Same tools via API |
| **UI** | VSCode panel | Floating widget |
| **Best For** | Developers | End users |

## Summary

Users now have **TWO ways** to get AI assistance:

1. **MCP in VSCode** - For developers, full system access
2. **Web Chat** - For all users, integrated in the app

The web chat makes the AI assistant **immediately accessible** to non-technical users who just want to import their data without learning VSCode!

---

**Status:** ✅ Ready to use
**Files Added:** `AIChat.tsx`, `assistant.py`
**Integration:** Complete in Layout component