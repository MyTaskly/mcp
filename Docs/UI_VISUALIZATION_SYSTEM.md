# MyTaskly UI Visualization System

## Overview

This document describes the complete UI visualization system for MyTaskly MCP server. The system provides a standardized approach for deciding when tool outputs should be displayed to users in the React Native mobile app versus when data is used internally.

---

## Core Principle

**Type-Based Output Detection**: The React Native app analyzes tool outputs and checks for specific `type` fields to determine what UI to display.

```typescript
// App-side logic
switch (response.type) {
  case "task_created":
  case "category_created":
  case "note_created":
    // Show success notification + "Edit" button
    showEditButton();
    break;

  case "task_list":
  case "category_list":
  case "note_list":
    // Render formatted list/grid
    renderFormattedView(response);
    break;

  default:
    // No UI display (internal use)
    break;
}
```

---

## Architecture

### 1. **Internal Use Tools** (NO visualization)

These tools return simple JSON without special `type` fields. The app does NOT display anything.

**Categories:**
- `get_my_categories()` - Returns: `{categories: [...], total: N}`

**Tasks:**
- `get_tasks()` - Returns: `{tasks: [...], total: N}`
- `update_task()` - Returns: `{message: "...", ...}`
- `complete_task()` - Returns: `{message: "...", ...}`

**Notes:**
- `get_notes()` - Returns: `{notes: [...], total: N}`
- `update_note()` - Returns: `{message: "...", ...}`
- `delete_note()` - Returns: `{message: "...", ...}`

### 2. **Visualization Tools** (YES visualization)

These tools return formatted data with `type: "X_list"` for rich UI rendering.

**Categories:**
- `show_categories_to_user()` - Returns: `{type: "category_list", ...}`

**Tasks:**
- `show_tasks_to_user()` - Returns: `{type: "task_list", ...}`

**Notes:**
- `show_notes_to_user()` - Returns: `{type: "note_list", ...}`

### 3. **Creation Tools** (Show "Edit" button)

These tools return `type: "X_created"` triggering automatic edit button display.

**Categories:**
- `create_category()` - Returns: `{type: "category_created", category: {...}, ...}`

**Tasks:**
- `add_task()` - Returns: `{type: "task_created", task: {...}, ...}`

**Notes:**
- `create_note()` - Returns: `{type: "note_created", note: {...}, ...}`

---

## Formatter Functions

All formatters are located in `src/formatters/tasks.py` and transform raw API data into React Native-optimized structures.

### `format_categories_for_ui(categories, task_counts)`

Transforms category data with:
- Color coding (predefined + hash-based)
- Icons (briefcase, user, book, etc.)
- Task counts per category
- Action buttons (edit, delete, viewTasks)
- Summary statistics
- Voice summary for TTS
- UI hints (grid mode, swipe actions, etc.)

### `format_tasks_for_ui(tasks)`

Transforms task data with:
- Italian date formatting
- Priority colors and emojis
- Category colors
- Action buttons (complete, edit, delete)
- Summary statistics (pending, completed, high priority)
- Voice summary for TTS
- UI hints (list mode, group by category)

### `format_notes_for_ui(notes)`

Transforms note data with:
- Color coding
- Position data (for drag & drop)
- Action buttons (edit, delete, changeColor)
- Color statistics
- Voice summary for TTS
- UI hints (grid mode, color picker, drag & drop)

---

## Output Structures

### Category Creation Response

```json
{
  "success": true,
  "type": "category_created",
  "message": "✅ Categoria 'Progetti' creata con successo",
  "category": {
    "category_id": 10,
    "name": "Progetti",
    "description": "Progetti personali",
    "user_id": 123
  }
}
```

### Category List Response

```json
{
  "type": "category_list",
  "version": "1.0",
  "categories": [
    {
      "id": 1,
      "name": "Lavoro",
      "description": "Task di lavoro",
      "color": "#3B82F6",
      "icon": "briefcase",
      "taskCount": 12,
      "userId": 123,
      "actions": {
        "edit": {
          "label": "✏️ Modifica",
          "enabled": true
        },
        "delete": {
          "label": "🗑️ Elimina",
          "enabled": true,
          "requiresConfirmation": true
        },
        "viewTasks": {
          "label": "👁️ Vedi task",
          "enabled": true
        }
      }
    }
  ],
  "summary": {
    "total": 5,
    "categories_with_tasks": 3,
    "total_tasks": 25
  },
  "voice_summary": "Hai 5 categorie, di cui 3 con task attivi. Totale 25 task.",
  "ui_hints": {
    "display_mode": "grid",
    "enable_swipe_actions": true,
    "enable_pull_to_refresh": true,
    "enable_search": true,
    "default_sort": "name"
  }
}
```

### Task Creation Response

```json
{
  "success": true,
  "type": "task_created",
  "message": "✅ Task 'Riunione team' creato con successo in 'Lavoro'",
  "task": {
    "task_id": 42,
    "title": "Riunione team",
    "description": "Meeting settimanale",
    "end_time": "2025-12-15T10:00:00",
    "priority": "Alta",
    "status": "In sospeso",
    "category_id": 5
  },
  "category_used": "Lavoro"
}
```

### Task List Response

```json
{
  "type": "task_list",
  "version": "1.0",
  "tasks": [
    {
      "id": 1,
      "title": "Riunione team",
      "description": "Meeting settimanale",
      "endTime": "2025-12-15T10:00:00",
      "endTimeFormatted": "Lunedì 15 dicembre, 10:00",
      "category": "Lavoro",
      "categoryColor": "#3B82F6",
      "priority": "Alta",
      "priorityEmoji": "[!]",
      "priorityColor": "#EF4444",
      "status": "In sospeso",
      "actions": {
        "complete": {
          "label": "[OK] Completa",
          "enabled": true
        },
        "edit": {
          "label": "✏️ Modifica",
          "enabled": true
        },
        "delete": {
          "label": "🗑️ Elimina",
          "enabled": true
        }
      }
    }
  ],
  "summary": {
    "total": 10,
    "pending": 6,
    "completed": 4,
    "high_priority": 2
  },
  "voice_summary": "Hai 10 task, di cui 2 ad alta priorità. 6 sono in sospeso e 4 completati.",
  "ui_hints": {
    "display_mode": "list",
    "enable_swipe_actions": true,
    "enable_pull_to_refresh": true,
    "group_by": "category"
  }
}
```

### Note Creation Response

```json
{
  "success": true,
  "type": "note_created",
  "message": "✅ Nota creata con successo",
  "note": {
    "note_id": 456,
    "title": "Comprare il latte",
    "position_x": "0",
    "position_y": "0",
    "color": "#FFEB3B"
  }
}
```

### Note List Response

```json
{
  "type": "note_list",
  "version": "1.0",
  "notes": [
    {
      "id": 1,
      "title": "Comprare il latte",
      "color": "#FFEB3B",
      "positionX": "0",
      "positionY": "0",
      "createdAt": "2025-12-15T10:30:00",
      "userId": 123,
      "actions": {
        "edit": {
          "label": "✏️ Modifica",
          "enabled": true
        },
        "delete": {
          "label": "🗑️ Elimina",
          "enabled": true,
          "requiresConfirmation": true
        },
        "changeColor": {
          "label": "🎨 Cambia colore",
          "enabled": true
        }
      }
    }
  ],
  "summary": {
    "total": 15,
    "color_counts": {
      "#FFEB3B": 8,
      "#4CAF50": 5,
      "#2196F3": 2
    }
  },
  "voice_summary": "Hai 15 note, la maggior parte sono gialle.",
  "ui_hints": {
    "display_mode": "grid",
    "enable_swipe_actions": true,
    "enable_pull_to_refresh": true,
    "enable_color_picker": true,
    "enable_drag_and_drop": true
  }
}
```

---

## Usage Examples

### Example 1: User wants to see categories

```
User: "Mostrami le mie categorie"

AI:
1. Calls show_categories_to_user()
2. Receives response with type: "category_list"

App:
1. Sees type: "category_list"
2. Renders grid with formatted categories
3. Shows colors, icons, task counts
4. Enables swipe actions for edit/delete
```

### Example 2: AI searches category before creating task

```
User: "Crea task Riunione in categoria Lavoro"

AI:
1. Calls get_my_categories() (internal use)
2. Finds category_id=5 for "Lavoro"
3. Calls add_task(title="Riunione", category_name="Lavoro")

App:
1. get_my_categories() has NO special type
2. App does NOT display anything (internal use)
3. add_task() returns type: "task_created"
4. App shows notification + "Edit task" button
```

### Example 3: User creates new category

```
User: "Crea categoria Progetti"

AI:
1. Calls create_category(name="Progetti")

Response:
{
  "success": true,
  "type": "category_created",
  "message": "✅ Categoria 'Progetti' creata con successo",
  "category": {
    "category_id": 10,
    "name": "Progetti",
    "description": null
  }
}

App:
1. Sees type: "category_created"
2. Shows success notification
3. Shows "Modifica Progetti" button
4. User can click to edit category immediately
```

### Example 4: User wants to see tasks

```
User: "Mostrami i miei task"

AI:
1. Calls show_tasks_to_user()
2. Receives response with type: "task_list"

App:
1. Sees type: "task_list"
2. Renders formatted task list
3. Groups by category
4. Shows priority colors, formatted dates
5. Enables swipe actions
```

---

## Color Schemes

### Category Colors

Predefined colors for common Italian categories:

```python
{
  "Lavoro": "#3B82F6",      # Blue
  "Personale": "#8B5CF6",   # Purple
  "Studio": "#10B981",      # Green
  "Sport": "#F59E0B",       # Orange
  "Famiglia": "#EC4899",    # Pink
  "Cibo": "#EF4444",        # Red
  "Generale": "#6B7280"     # Gray
}
```

Unknown categories get hash-based consistent colors from palette: `["#3B82F6", "#8B5CF6", "#10B981", "#F59E0B", "#EC4899", "#EF4444"]`

### Priority Colors

```python
{
  "Alta": "#EF4444",    # Red
  "Media": "#F59E0B",   # Orange
  "Bassa": "#10B981"    # Green
}
```

### Note Colors

```python
{
  "#FFEB3B": "gialle",      # Yellow
  "#FF9800": "arancioni",   # Orange
  "#4CAF50": "verdi",       # Green
  "#2196F3": "blu",         # Blue
  "#E91E63": "rosa",        # Pink
  "#9C27B0": "viola"        # Purple
}
```

---

## Icon Mapping

### Category Icons

```python
{
  "Lavoro": "briefcase",
  "Personale": "user",
  "Studio": "book",
  "Sport": "activity",
  "Famiglia": "home",
  "Cibo": "coffee",
  "Generale": "folder"
}
```

Default: `"folder"` for unknown categories

---

## Benefits

1. ✅ **Zero ambiguity**: App always knows what to display via `type` field
2. ✅ **Separation of concerns**: Internal tools vs visualization tools
3. ✅ **Consistency**: Same pattern across categories, tasks, and notes
4. ✅ **Extendible**: Easy to add new types (reminders, goals, etc.)
5. ✅ **Performance**: Formatting only when needed for visualization
6. ✅ **UX optimal**: Automatic "Edit" button after creation
7. ✅ **Accessibility**: Voice summaries for TTS
8. ✅ **Mobile-optimized**: UI hints guide the app's rendering

---

## Files Modified

### Formatters
- `src/formatters/tasks.py` - Added `format_categories_for_ui()`, `format_notes_for_ui()`, `get_category_icon()`
- `src/formatters/__init__.py` - Exported new formatters

### Tools - Categories
- `src/tools/categories.py` - Added `show_categories_to_user()`, updated `create_category()` and `get_my_categories()`

### Tools - Tasks
- `src/tools/tasks.py` - Added `show_tasks_to_user()`, updated `add_task()` and `get_tasks()`

### Tools - Notes
- `src/tools/notes.py` - Added `show_notes_to_user()`, updated `create_note()` and `get_notes()`

### Server
- `src/core/server.py` - Registered all new visualization tools

---

## Decision History

### Initial Approach (Rejected)
- Considered metadata-based schemas with `display_mode` or `intent` fields
- Too complex for AI to manage consistently

### Separate Tools Approach (Partially Adopted)
- Create separate tools for internal use vs visualization
- User initially proposed this
- AI confirmed this reduces confusion
- **Result**: Adopted with hybrid type-based system

### Final Approach (Current)
- Separate tools for internal vs visualization
- Type-based detection for creations (`X_created`)
- Simple app logic: check `type` field
- No complex metadata required
- **Result**: Implemented for categories, tasks, and notes

---

## React Native Implementation Guide

### Type Detection

```typescript
interface ToolResponse {
  type?: string;
  [key: string]: any;
}

function handleToolResponse(response: ToolResponse) {
  switch (response.type) {
    case "category_created":
      handleCreation("category", response);
      break;
    case "task_created":
      handleCreation("task", response);
      break;
    case "note_created":
      handleCreation("note", response);
      break;
    case "category_list":
      renderCategoryGrid(response);
      break;
    case "task_list":
      renderTaskList(response);
      break;
    case "note_list":
      renderNoteGrid(response);
      break;
    default:
      // Internal use, no UI
      break;
  }
}
```

### Creation Handler

```typescript
function handleCreation(type: string, response: any) {
  // Show success toast
  Toast.show({
    type: "success",
    text1: response.message
  });

  // Show edit button
  const itemData = response[type]; // response.category, response.task, or response.note
  showActionButton({
    label: `Modifica ${itemData.name || itemData.title}`,
    onPress: () => {
      navigation.navigate(`${capitalize(type)}Editor`, {
        [`${type}Id`]: itemData[`${type}_id`]
      });
    }
  });
}
```

### List Rendering

```typescript
function renderCategoryGrid(response: CategoryListResponse) {
  return (
    <Grid>
      {response.categories.map(cat => (
        <CategoryCard
          key={cat.id}
          name={cat.name}
          color={cat.color}
          icon={cat.icon}
          taskCount={cat.taskCount}
          onEdit={() => handleEdit(cat.id)}
          onDelete={() => handleDelete(cat.id)}
          onViewTasks={() => handleViewTasks(cat.id)}
        />
      ))}
    </Grid>
  );
}
```

---

## Testing

### Test Scenarios

1. **Internal lookup**
   - Call `get_my_categories()` or `get_tasks()`
   - Verify NO UI is displayed
   - Verify simple JSON is returned

2. **User visualization**
   - Call `show_categories_to_user()` or `show_tasks_to_user()`
   - Verify formatted list/grid is displayed
   - Verify colors, icons, counts are present

3. **Item creation**
   - Call `create_category()`, `add_task()`, or `create_note()`
   - Verify success notification appears
   - Verify "Edit" button is displayed
   - Verify button navigates to correct editor

4. **Voice summary**
   - Enable TTS in app
   - Trigger any visualization tool
   - Verify `voice_summary` is read aloud

---

## Future Enhancements

### Possible Additions

1. **Reminders**: `type: "reminder_list"`, `type: "reminder_created"`
2. **Goals**: `type: "goal_list"`, `type: "goal_created"`
3. **Statistics**: `type: "stats_dashboard"`
4. **Calendar view**: `type: "calendar_view"`
5. **Search results**: `type: "search_results"`

### Pattern to Follow

For any new feature:

1. Create formatter function in `src/formatters/`
2. Create internal tool (returns simple JSON)
3. Create visualization tool (returns `type: "X_list"`)
4. Update creation tool to return `type: "X_created"`
5. Register tools in `src/core/server.py`
6. Update React Native app to handle new types
7. Document in this file

---

## Summary

The MyTaskly UI Visualization System provides a clean, consistent, and extensible architecture for controlling what data is displayed to users. By separating internal tools from visualization tools and using type-based detection, the system eliminates ambiguity while keeping implementation simple.

The pattern is proven across **3 major features** (categories, tasks, notes) and is ready for future expansion.
