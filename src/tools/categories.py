"""MCP tools for category management."""

from typing import Dict, Any, Optional
from fastmcp import Context
from src.auth import authenticate_from_context
from src.client import category_client, task_client
from src.formatters import format_categories_for_ui


async def get_my_categories(ctx: Context) -> Dict[str, Any]:
    """
    Ottieni TUTTE le categorie dell'utente per USO INTERNO (lookup, validazione).

    Questo tool restituisce dati JSON semplici senza formattazione UI.
    NON mostra nulla all'utente sullo schermo dell'app.

    Authentication:
        Automatic - JWT token extracted from SSE connection headers

    Returns:
        {
            "categories": [
                {
                    "category_id": 1,
                    "name": "Lavoro",
                    "description": "Task di lavoro",
                    "user_id": 123
                },
                ...
            ],
            "total": 5
        }

    QUANDO USARE QUESTO TOOL:
    - ✅ Trovare category_id da nome categoria prima di creare un task
    - ✅ Validare che una categoria esista
    - ✅ Verificare il nome esatto di una categoria
    - ❌ NON usare quando l'utente chiede "Mostrami le categorie" (usa show_categories_to_user)

    Per MOSTRARE le categorie all'utente, usa show_categories_to_user() invece.

    Example usage:
        User: "Crea task Riunione in categoria Lavoro"
        Bot reasoning: "Devo trovare l'ID della categoria Lavoro"
        Bot calls: get_my_categories()
        Bot finds: category_id=5 per "Lavoro"
        Bot calls: add_task(title="Riunione", category_id=5)
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
    """
    Crea una NUOVA categoria per organizzare i task.

    Authentication:
        Automatic - JWT token extracted from SSE connection headers

    Parameters:
    - name: Nome della categoria (obbligatorio, es: "Lavoro", "Progetti", "Casa")
    - description: Descrizione opzionale (es: "Task relativi al lavoro")

    Errore se la categoria esiste già.

    Returns:
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

    L'app React Native mostrerà automaticamente un bottone "Modifica categoria"
    quando riceve type: "category_created".

    Utile per:
    - Creare categorie per organizzare meglio i task
    - Preparare una struttura prima di aggiungere task

    Example usage:
        User: "Crea una categoria Progetti"
        Bot calls: create_category(name="Progetti", description="Progetti personali")
        Bot response: "✅ Categoria 'Progetti' creata con successo"
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
    """
    Modifica il nome e/o descrizione di una categoria ESISTENTE tramite il suo ID.

    Procedura:
    1. Prima usa get_my_categories per ottenere l'elenco delle categorie e trovare l'ID corretto
    2. Usa l'ID della categoria trovata in questa funzione per modificarla

    Authentication:
        Automatic - JWT token extracted from SSE connection headers

    Parameters:
    - category_id: ID della categoria da modificare (ottienilo con get_my_categories)
    - new_name: Nuovo nome per la categoria (opzionale, mantiene quello attuale se non specificato)
    - new_description: Nuova descrizione (opzionale, mantiene quella attuale se non specificato)

    Returns:
        {
            "message": "Category updated successfully to 'Nuovo Nome'"
        }

    Utile per:
    - Rinominare categorie usando l'ID
    - Aggiornare solo la descrizione di una categoria tramite il suo ID
    - Modificare sia nome che descrizione contemporaneamente

    Example usage:
        User: "Rinomina la categoria Lavoro in Ufficio"
        Bot calls:
            1. get_my_categories() → trova category_id=5 per "Lavoro"
            2. update_category(category_id=5, new_name="Ufficio")
        Bot response: "✅ Categoria rinominata da 'Lavoro' a 'Ufficio'"
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


async def search_categories(
    ctx: Context,
    search_term: str,
    max_suggestions: int = 5
) -> Dict[str, Any]:
    """
    CERCA una categoria per nome, con suggerimenti di categorie simili.

    Perfetto quando non ricordi il nome esatto di una categoria.
    Mostra corrispondenze esatte e suggerimenti di categorie simili.

    Authentication:
        Automatic - JWT token extracted from SSE connection headers

    Parameters:
    - search_term: Parte del nome della categoria da cercare
    - max_suggestions: Numero massimo di suggerimenti (default: 5)

    Returns:
        {
            "success": true,
            "search_term": "lavoro",
            "exact_match": {...},  # Se trovata corrispondenza esatta
            "similar_categories": [...],  # Categorie simili
            "similarity_scores": [0.8, 0.6, ...],
            "total_categories": 10,
            "message": "Found 3 similar categories for 'lavoro'"
        }

    Esempi:
    - search_categories(search_term="lavoro") -> mostra categorie simili
    - search_categories(search_term="proj") -> suggerisce categorie tipo "Progetto"

    Example usage:
        User: "Cerca categorie tipo progetto"
        Bot calls: search_categories(search_term="proj")
        Bot response: "Ho trovato 2 categorie simili: 'Progetti', 'Progetto Casa'"
    """
    user_id = authenticate_from_context(ctx)

    # Get all categories
    categories = await category_client.get_categories(user_id)

    # Find exact match
    exact_match = None
    search_lower = search_term.lower().strip()
    for cat in categories:
        if cat["name"].lower() == search_lower:
            exact_match = cat
            break

    # Find similar categories using simple substring matching
    import difflib
    similar_categories = []
    for category in categories:
        category_name_lower = category["name"].lower().strip()
        ratio = difflib.SequenceMatcher(None, search_lower, category_name_lower).ratio()

        if ratio > 0.3:  # Low threshold for suggestions
            similar_categories.append({
                "category": category,
                "similarity": ratio
            })

    # Sort by similarity and limit
    similar_categories.sort(key=lambda x: x["similarity"], reverse=True)
    similar_categories = similar_categories[:max_suggestions]

    return {
        "success": True,
        "search_term": search_term,
        "exact_match": exact_match,
        "similar_categories": [item["category"] for item in similar_categories],
        "similarity_scores": [item["similarity"] for item in similar_categories],
        "total_categories": len(categories),
        "message": f"Found {len(similar_categories)} similar categories for '{search_term}'"
    }


async def show_category_details(
    ctx: Context,
    category_name: Optional[str] = None,
    category_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    MOSTRA i dettagli di UNA SINGOLA categoria all'utente con formattazione UI completa.

    Questo tool è specificamente per VISUALIZZARE una categoria specifica sullo schermo dell'app mobile.
    Include tutti i dettagli della categoria, conteggio task, e statistiche.

    Authentication:
        Automatic - JWT token extracted from SSE connection headers

    Parameters:
    - category_name: Nome della categoria da visualizzare (es: "Lavoro") (opzionale)
    - category_id: ID della categoria da visualizzare (opzionale, alternativo a category_name)

    Nota: Specifica category_name OPPURE category_id, non entrambi.

    Returns:
        {
            "type": "category_details",
            "version": "1.0",
            "category": {
                "id": 1,
                "name": "Lavoro",
                "description": "Task di lavoro",
                "taskCount": 12,
                "userId": 123
            },
            "task_breakdown": {
                "pending": 8,
                "completed": 3,
                "cancelled": 1,
                "high_priority": 4,
                "medium_priority": 5,
                "low_priority": 3
            },
            "voice_summary": "Categoria Lavoro con 12 task, di cui 8 in sospeso e 4 ad alta priorità.",
            "ui_hints": {
                "enable_edit": true,
                "enable_view_tasks": true
            }
        }

    QUANDO USARE QUESTO TOOL:
    - ✅ Utente chiede: "Mostrami la categoria Lavoro"
    - ✅ Utente chiede: "Dettagli della categoria Personale"
    - ✅ Utente chiede: "Fammi vedere i dettagli di Lavoro"
    - ❌ NON usare per vedere tutte le categorie (usa show_categories_to_user)

    L'app React Native renderizza automaticamente una vista dettagliata
    quando riceve type: "category_details".

    Example usage:
        User: "Mostrami i dettagli della categoria Lavoro"
        Bot calls: show_category_details(category_name="Lavoro")
        Bot response: "Ecco i dettagli della categoria Lavoro" (l'app mostra la vista dettagliata)
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
    """
    MOSTRA le categorie all'utente con formattazione UI completa.

    Questo tool è specificamente per VISUALIZZARE le categorie sullo schermo dell'app mobile.
    Include formattazione ricca con colori, icone, conteggi task, e configurazione UI.

    Authentication:
        Automatic - JWT token extracted from SSE connection headers

    Returns:
        {
            "type": "category_list",
            "version": "1.0",
            "categories": [
                {
                    "id": 1,
                    "name": "Lavoro",
                    "description": "Task di lavoro",
                    "taskCount": 12
                },
                ...
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
                "enable_search": true
            }
        }

    QUANDO USARE QUESTO TOOL:
    - ✅ Utente chiede: "Mostrami le categorie"
    - ✅ Utente chiede: "Quali categorie ho?"
    - ✅ Utente chiede: "Fammi vedere le categorie"
    - ❌ NON usare per lookup interni (usa get_my_categories invece)

    L'app React Native renderizza automaticamente una lista/griglia formattata
    quando riceve type: "category_list".

    Example usage:
        User: "Mostrami le mie categorie"
        Bot calls: show_categories_to_user()
        Bot response: "Ecco le tue 5 categorie" (l'app mostra la lista formattata)
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
