"""MCP tools for category management."""

from typing import Dict, Any, Optional
from fastmcp import Context
from src.auth import authenticate_from_context
from src.client import category_client, task_client
from src.formatters import format_categories_for_ui


async def get_my_categories(ctx: Context) -> Dict[str, Any]:
    """Recupera tutte le categorie dell'utente come JSON grezzo per uso interno (lookup, validazione).

    Non mostra nulla all'utente. Restituisce dati strutturati per elaborazione interna.

    Quando usare:
    - Trovare category_id da nome categoria prima di creare un task
    - Verificare se una categoria esiste o ottenerne il nome esatto

    Quando NON usare:
    - Se l'utente chiede "Mostrami le categorie" → usa show_categories_to_user()

    Example:
        User: "Crea task Riunione in categoria Lavoro"
        → get_my_categories() per trovare category_id=5 "Lavoro"
        → add_task(title="Riunione", category_name="Lavoro")
    """
    user_id = authenticate_from_context(ctx)
    categories = await category_client.get_categories(user_id)

    return {
        "categories": categories,
        "total": len(categories)
    }


async def create_category(
    ctx: Context,
    name: str,
    description: Optional[str] = None
) -> Dict[str, Any]:
    """Crea una nuova categoria per organizzare i task. Restituisce errore se esiste già.

    Parameters:
    - name: Nome della categoria (obbligatorio, es: "Lavoro", "Progetti", "Casa")
    - description: Descrizione opzionale (es: "Task relativi al lavoro")

    Restituisce type="category_created" — l'app mostra automaticamente il pulsante "Modifica categoria".
    """
    user_id = authenticate_from_context(ctx)
    result = await category_client.create_category(user_id, name, description)

    return {
        "success": True,
        "type": "category_created",
        "message": f"✅ Categoria '{name}' creata con successo",
        "category": result
    }


async def update_category(
    ctx: Context,
    category_id: int,
    new_name: Optional[str] = None,
    new_description: Optional[str] = None
) -> Dict[str, Any]:
    """Modifica nome e/o descrizione di una categoria esistente tramite il suo ID.

    Chiama get_my_categories() prima per ottenere il category_id corretto. Specifica solo i campi da modificare.

    Parameters:
    - category_id: ID della categoria da modificare — ottienilo con get_my_categories() (obbligatorio)
    - new_name: Nuovo nome (opzionale, mantiene l'attuale se non specificato)
    - new_description: Nuova descrizione (opzionale, mantiene l'attuale se non specificato)

    Example:
        User: "Rinomina Lavoro in Ufficio"
        → get_my_categories() → trova category_id=5
        → update_category(category_id=5, new_name="Ufficio")
    """
    user_id = authenticate_from_context(ctx)
    result = await category_client.update_category(
        user_id,
        category_id,
        new_name,
        new_description
    )

    final_name = new_name if new_name else "category"
    return {
        "message": f"Category updated successfully to '{final_name}'",
        **result
    }



async def show_category_details(
    ctx: Context,
    category_name: Optional[str] = None,
    category_id: Optional[int] = None
) -> Dict[str, Any]:
    """Mostra i dettagli di una singola categoria nell'app mobile con statistiche dei task.

    Restituisce type="category_details" con conteggio task, breakdown per stato e priorità.
    Specifica category_name OPPURE category_id, non entrambi.

    Parameters:
    - category_name: Nome della categoria (es: "Lavoro") — alternativo a category_id
    - category_id: ID della categoria — alternativo a category_name

    Quando usare:
    - "Mostrami la categoria Lavoro", "Dettagli di Personale", "Quanti task ho in Lavoro?"

    Quando NON usare:
    - Per vedere tutte le categorie → usa show_categories_to_user()
    """
    user_id = authenticate_from_context(ctx)

    # Get all categories
    categories = await category_client.get_categories(user_id)

    # Find the specific category
    selected_category = None
    if category_name:
        for cat in categories:
            if cat["name"].lower() == category_name.lower():
                selected_category = cat
                break
    elif category_id:
        for cat in categories:
            if cat["category_id"] == category_id:
                selected_category = cat
                break

    if not selected_category:
        search_term = category_name or str(category_id)
        return {
            "type": "category_details",
            "version": "1.0",
            "error": f"Categoria '{search_term}' non trovata",
            "voice_summary": f"Categoria {search_term} non trovata"
        }

    # Get all tasks for this category
    cat_id = selected_category["category_id"]
    all_tasks = await task_client.get_tasks(user_id, category_id=cat_id)

    # Calculate task breakdown
    task_breakdown = {
        "pending": sum(1 for t in all_tasks if t.get("status") == "In sospeso"),
        "completed": sum(1 for t in all_tasks if t.get("status") == "Completato"),
        "cancelled": sum(1 for t in all_tasks if t.get("status") == "Annullato"),
        "high_priority": sum(1 for t in all_tasks if t.get("priority") == "Alta"),
        "medium_priority": sum(1 for t in all_tasks if t.get("priority") == "Media"),
        "low_priority": sum(1 for t in all_tasks if t.get("priority") == "Bassa")
    }

    task_count = len(all_tasks)
    cat_name = selected_category["name"]

    # Create voice summary
    voice_summary = f"Categoria {cat_name} con {task_count} task"
    if task_breakdown["pending"] > 0:
        voice_summary += f", di cui {task_breakdown['pending']} in sospeso"
    if task_breakdown["high_priority"] > 0:
        voice_summary += f" e {task_breakdown['high_priority']} ad alta priorità"
    voice_summary += "."

    return {
        "type": "category_details",
        "version": "1.0",
        "category": {
            "id": cat_id,
            "name": cat_name,
            "description": selected_category.get("description", ""),
            "taskCount": task_count,
            "userId": selected_category.get("user_id")
        },
        "task_breakdown": task_breakdown,
        "voice_summary": voice_summary,
        "ui_hints": {
            "enable_edit": True,
            "enable_view_tasks": task_count > 0
        }
    }


async def show_categories_to_user(ctx: Context) -> Dict[str, Any]:
    """Mostra tutte le categorie all'utente nell'app mobile con conteggio task e formattazione UI.

    Restituisce type="category_list" — l'app React Native renderizza automaticamente la griglia.

    Quando usare:
    - "Mostrami le categorie", "Quali categorie ho?", "Fammi vedere le categorie"

    Quando NON usare:
    - Per lookup interni o trovare un category_id → usa get_my_categories()
    """
    user_id = authenticate_from_context(ctx)

    # Get categories
    categories = await category_client.get_categories(user_id)

    # Get all tasks to count per category
    all_tasks = await task_client.get_tasks(user_id)

    # Count tasks per category
    task_counts = {}
    for task in all_tasks:
        category_info = task.get("category")
        if category_info and isinstance(category_info, dict):
            category_id = category_info.get("category_id")
            if category_id:
                task_counts[category_id] = task_counts.get(category_id, 0) + 1

    # Format for UI
    formatted_response = format_categories_for_ui(categories, task_counts)

    return formatted_response
