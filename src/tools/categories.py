"""MCP tools for category management."""

from typing import Dict, Any, Optional
from fastmcp import Context
from src.auth import authenticate_from_context
from src.client import category_client


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

    for cat in categories:
        cat.pop("user_id", None)

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
        "category_id": result.get("category_id")
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
    await category_client.update_category(user_id, category_id, new_name, new_description)

    return {"success": True, "category_id": category_id}



async def show_category_details(
    ctx: Context,
    category_name: Optional[str] = None,
    category_id: Optional[int] = None
) -> Dict[str, Any]:
    """Mostra i dettagli di una singola categoria nell'app mobile. L'app legge il type e renderizza autonomamente.

    Specifica category_name OPPURE category_id, non entrambi.

    Parameters:
    - category_name: Nome della categoria (es: "Lavoro") — alternativo a category_id
    - category_id: ID della categoria — alternativo a category_name

    Quando usare:
    - "Mostrami la categoria Lavoro", "Dettagli di Personale"

    Quando NON usare:
    - Per vedere tutte le categorie → usa show_categories_to_user()
    """
    authenticate_from_context(ctx)

    return {
        "type": "category_details",
        "success": True,
        **({"category_name": category_name} if category_name else {}),
        **({"category_id": category_id} if category_id else {})
    }


async def show_categories_to_user(ctx: Context) -> Dict[str, Any]:
    """Mostra tutte le categorie all'utente nell'app mobile. L'app legge il type e renderizza la griglia autonomamente.

    Quando usare:
    - "Mostrami le categorie", "Quali categorie ho?", "Fammi vedere le categorie"

    Quando NON usare:
    - Per lookup interni o trovare un category_id → usa get_my_categories()
    """
    authenticate_from_context(ctx)

    return {"type": "category_list", "success": True}
