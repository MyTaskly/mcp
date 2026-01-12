"""Task data formatters for React Native UI."""

from typing import Dict, Any, List
from datetime import datetime


def format_date_for_mobile(date_str: str) -> str:
    """
    Format ISO date string to mobile-friendly Italian format.

    Args:
        date_str: ISO format date string (e.g., "2025-12-15T18:00:00+00:00")

    Returns:
        Formatted string (e.g., "Venerdì 15 dicembre, 18:00")
    """
    if not date_str:
        return ""

    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))

        # Italian day and month names
        days = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
        months = [
            "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
            "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"
        ]

        day_name = days[dt.weekday()]
        month_name = months[dt.month - 1]

        return f"{day_name} {dt.day} {month_name}, {dt.strftime('%H:%M')}"
    except Exception:
        return date_str


def get_priority_emoji(priority: str) -> str:
    """Get emoji representation for task priority."""
    priority_map = {
        "Alta": "[!]",
        "Media": "",
        "Bassa": ""
    }
    return priority_map.get(priority, "")


def get_priority_color(priority: str) -> str:
    """Get color hex code for task priority."""
    color_map = {
        "Alta": "#EF4444",  # Red
        "Media": "#F59E0B",  # Orange
        "Bassa": "#10B981"   # Green
    }
    return color_map.get(priority, "#6B7280")


def get_category_color(category_name: str) -> str:
    """
    Get a consistent color for a category based on its name.
    Uses predefined colors for common categories and hash-based colors for others.
    """
    if not category_name:
        return "#6B7280"

    # Predefined colors for common Italian categories
    predefined = {
        "Lavoro": "#3B82F6",      # Blue
        "Personale": "#8B5CF6",   # Purple
        "Studio": "#10B981",      # Green
        "Sport": "#F59E0B",       # Orange
        "Famiglia": "#EC4899",    # Pink
        "Cibo": "#EF4444",        # Red
        "Generale": "#6B7280"     # Gray
    }

    if category_name in predefined:
        return predefined[category_name]

    # Generate consistent color from hash for unknown categories
    hash_val = sum(ord(c) for c in category_name)
    colors = ["#3B82F6", "#8B5CF6", "#10B981", "#F59E0B", "#EC4899", "#EF4444"]
    return colors[hash_val % len(colors)]


def get_category_icon(category_name: str) -> str:
    """
    Get an icon representation for a category based on its name.
    """
    if not category_name:
        return "folder"

    icon_map = {
        "Lavoro": "briefcase",
        "Personale": "user",
        "Studio": "book",
        "Sport": "activity",
        "Famiglia": "home",
        "Cibo": "coffee",
        "Generale": "folder"
    }
    return icon_map.get(category_name, "folder")


def format_categories_for_ui(categories: List[Dict[str, Any]], task_counts: Dict[int, int] = None) -> Dict[str, Any]:
    """
    Format categories response for React Native UI components.

    Creates a JSON structure optimized for native mobile rendering with:
    - Color coding for each category
    - Icons for common categories
    - Task count per category
    - UI hints for display configuration

    Args:
        categories: List of category dictionaries from FastAPI
        task_counts: Optional dictionary mapping category_id to task count

    Returns:
        Formatted dictionary with type, categories, columns, summary, and UI hints
    """
    formatted_categories = []
    task_counts = task_counts or {}

    for category in categories:
        category_id = category.get("category_id")
        category_name = category.get("name", "Senza nome")
        task_count = task_counts.get(category_id, 0)

        formatted_category = {
            "id": category_id,
            "name": category_name,
            "description": category.get("description", ""),
            "color": get_category_color(category_name),
            "icon": get_category_icon(category_name),
            "taskCount": task_count,
            "userId": category.get("user_id"),
            "actions": {
                "edit": {
                    "label": "✏️ Modifica",
                    "enabled": True
                },
                "delete": {
                    "label": "🗑️ Elimina",
                    "enabled": True,
                    "requiresConfirmation": True
                },
                "viewTasks": {
                    "label": "👁️ Vedi task",
                    "enabled": task_count > 0
                }
            }
        }
        formatted_categories.append(formatted_category)

    # Calculate summary statistics
    total = len(formatted_categories)
    total_tasks = sum(cat["taskCount"] for cat in formatted_categories)
    categories_with_tasks = sum(1 for cat in formatted_categories if cat["taskCount"] > 0)

    # Create voice summary for TTS
    voice_summary = f"Hai {total} categorie"
    if categories_with_tasks > 0:
        voice_summary += f", di cui {categories_with_tasks} con task attivi"
    if total_tasks > 0:
        voice_summary += f". Totale {total_tasks} task"
    voice_summary += "."

    return {
        "type": "category_list",
        "version": "1.0",
        "columns": [
            {
                "id": "name",
                "label": "Categoria",
                "width": "50%",
                "sortable": True
            },
            {
                "id": "taskCount",
                "label": "Task",
                "width": "25%",
                "sortable": True
            },
            {
                "id": "description",
                "label": "Descrizione",
                "width": "25%",
                "sortable": False
            }
        ],
        "categories": formatted_categories,
        "summary": {
            "total": total,
            "categories_with_tasks": categories_with_tasks,
            "total_tasks": total_tasks
        },
        "voice_summary": voice_summary,
        "ui_hints": {
            "display_mode": "grid",
            "enable_swipe_actions": True,
            "enable_pull_to_refresh": True,
            "enable_search": True,
            "default_sort": "name"
        }
    }


def format_notes_for_ui(notes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Format notes response for React Native UI components.

    Creates a JSON structure optimized for native mobile rendering with:
    - Color coding for each note
    - Timestamps formatted in Italian
    - Action buttons configuration
    - Summary statistics
    - Voice-friendly summary for TTS

    Args:
        notes: List of note dictionaries from FastAPI

    Returns:
        Formatted dictionary with type, notes, columns, summary, and UI hints
    """
    formatted_notes = []

    for note in notes:
        formatted_note = {
            "id": note.get("note_id"),
            "title": note.get("title", ""),
            "color": note.get("color", "#FFEB3B"),
            "positionX": note.get("position_x", "0"),
            "positionY": note.get("position_y", "0"),
            "createdAt": note.get("created_at"),
            "userId": note.get("user_id"),
            "actions": {
                "edit": {
                    "label": "✏️ Modifica",
                    "enabled": True
                },
                "delete": {
                    "label": "🗑️ Elimina",
                    "enabled": True,
                    "requiresConfirmation": True
                },
                "changeColor": {
                    "label": "🎨 Cambia colore",
                    "enabled": True
                }
            }
        }
        formatted_notes.append(formatted_note)

    # Calculate summary statistics
    total = len(formatted_notes)

    # Count notes by color
    color_counts = {}
    for note in formatted_notes:
        color = note["color"]
        color_counts[color] = color_counts.get(color, 0) + 1

    # Create voice summary for TTS
    voice_summary = f"Hai {total} note"
    if total > 0:
        most_common_color = max(color_counts.items(), key=lambda x: x[1])[0] if color_counts else None
        if most_common_color:
            color_name_map = {
                "#FFEB3B": "gialle",
                "#FF9800": "arancioni",
                "#4CAF50": "verdi",
                "#2196F3": "blu",
                "#E91E63": "rosa",
                "#9C27B0": "viola"
            }
            color_name = color_name_map.get(most_common_color, "colorate")
            voice_summary += f", la maggior parte sono {color_name}"
    voice_summary += "."

    return {
        "type": "note_list",
        "version": "1.0",
        "columns": [
            {
                "id": "title",
                "label": "Nota",
                "width": "80%",
                "sortable": True
            },
            {
                "id": "color",
                "label": "Colore",
                "width": "20%",
                "filterable": True
            }
        ],
        "notes": formatted_notes,
        "summary": {
            "total": total,
            "color_counts": color_counts
        },
        "voice_summary": voice_summary,
        "ui_hints": {
            "display_mode": "grid",
            "enable_swipe_actions": True,
            "enable_pull_to_refresh": True,
            "enable_color_picker": True,
            "enable_drag_and_drop": True
        }
    }


def format_tasks_for_ui(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Format tasks response for React Native UI components.

    Creates a JSON structure optimized for native mobile rendering with:
    - Formatted dates in Italian
    - Color coding for priorities and categories
    - Action buttons configuration
    - Summary statistics
    - Voice-friendly summary for TTS

    Args:
        tasks: List of task dictionaries from FastAPI

    Returns:
        Formatted dictionary with type, tasks, columns, summary, and UI hints
    """
    formatted_tasks = []

    for task in tasks:
        # Extract and format data
        priority = task.get("priority", "Media")
        category_name = task.get("category", {}).get("name", "Generale") if isinstance(task.get("category"), dict) else task.get("category", "Generale")

        formatted_task = {
            "id": task.get("task_id"),
            "title": task.get("title", ""),
            "description": task.get("description", ""),
            "endTime": task.get("end_time"),
            "endTimeFormatted": format_date_for_mobile(task.get("end_time")) if task.get("end_time") else None,
            "startTime": task.get("start_time"),
            "category": category_name,
            "categoryColor": get_category_color(category_name),
            "priority": priority,
            "priorityEmoji": get_priority_emoji(priority),
            "priorityColor": get_priority_color(priority),
            "status": task.get("status", "In sospeso"),
            "actions": {
                "complete": {
                    "label": "[OK] Completa",
                    "enabled": task.get("status") != "Completato"
                },
                "edit": {
                    "label": "✏️ Modifica",
                    "enabled": True
                },
                "delete": {
                    "label": "🗑️ Elimina",
                    "enabled": True
                }
            }
        }
        formatted_tasks.append(formatted_task)

    # Calculate summary statistics
    total = len(formatted_tasks)
    pending = sum(1 for t in formatted_tasks if t["status"] == "In sospeso")
    completed = sum(1 for t in formatted_tasks if t["status"] == "Completato")
    high_priority = sum(1 for t in formatted_tasks if t["priority"] == "Alta")

    # Create voice summary for TTS
    voice_summary = f"Hai {total} task"
    if high_priority > 0:
        voice_summary += f", di cui {high_priority} ad alta priorità"
    if pending > 0:
        voice_summary += f". {pending} sono in sospeso"
    if completed > 0:
        voice_summary += f" e {completed} completati"
    voice_summary += "."

    return {
        "type": "task_list",
        "version": "1.0",
        "columns": [
            {
                "id": "title",
                "label": "Task",
                "width": "40%",
                "sortable": True
            },
            {
                "id": "endTimeFormatted",
                "label": "Scadenza",
                "width": "30%",
                "sortable": True
            },
            {
                "id": "category",
                "label": "Categoria",
                "width": "20%",
                "filterable": True
            },
            {
                "id": "priority",
                "label": "Priorità",
                "width": "10%",
                "filterable": True
            }
        ],
        "tasks": formatted_tasks,
        "summary": {
            "total": total,
            "pending": pending,
            "completed": completed,
            "high_priority": high_priority
        },
        "voice_summary": voice_summary,
        "ui_hints": {
            "display_mode": "list",
            "enable_swipe_actions": True,
            "enable_pull_to_refresh": True,
            "group_by": "category"
        }
    }
