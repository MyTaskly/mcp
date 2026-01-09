"""MCP tools for category management."""

from typing import Dict, Any, Optional
from fastmcp import Context
from src.auth import authenticate_from_context
from src.client import category_client


async def get_my_categories(ctx: Context) -> Dict[str, Any]:
    """
    Ottieni TUTTE le categorie dell'utente.

    Restituisce l'elenco completo delle categorie create per organizzare i task.
    Ogni categoria ha un ID unico che puoi usare negli altri tools.

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

    Utile per:
    - Vedere come sono organizzati i task
    - Trovare l'ID di una categoria
    - Gestire le categorie esistenti

    Example usage:
        User: "Quali categorie ho?"
        Bot calls: get_my_categories()
        Bot response: "Hai 5 categorie: Lavoro, Personale, Studio, Sport, Famiglia"
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
            "category_id": 10,
            "name": "Progetti",
            "description": "Progetti personali",
            "user_id": 123,
            "message": "Category created successfully"
        }

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
        **result,
        "message": f"Category '{name}' created successfully"
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
