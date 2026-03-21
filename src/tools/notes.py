"""MCP tools for note management."""

from typing import Dict, Any, Optional
from fastmcp import Context
from src.auth import authenticate_from_context
from src.client import note_client


async def get_notes(ctx: Context) -> Dict[str, Any]:
    """Recupera tutte le note dell'utente come JSON grezzo per uso interno (lookup, validazione).

    Non mostra nulla all'utente. Restituisce dati strutturati per elaborazione interna.

    Quando usare:
    - Trovare note_id prima di modificare/eliminare una nota
    - Verificare se una nota esiste o cercarla per contenuto

    Quando NON usare:
    - Se l'utente chiede "Mostrami le note" → usa show_notes_to_user()

    Example:
        User: "Elimina la nota sul latte"
        → get_notes() per trovare note_id=5 "Comprare il latte"
        → delete_note(note_id=5)
    """
    user_id = authenticate_from_context(ctx)
    notes = await note_client.get_notes(user_id)

    return {
        "notes": notes,
        "total": len(notes)
    }


async def create_note(
    ctx: Context,
    title: str,
    position_x: str = "0",
    position_y: str = "0",
    color: str = "#FFEB3B"
) -> Dict[str, Any]:
    """Crea una nota post-it digitale. Le note hanno un solo campo testo (title) senza descrizione separata.

    Perfette per idee veloci, promemoria, liste, appunti di qualsiasi lunghezza.

    Parameters:
    - title: Testo completo della nota (obbligatorio, lunghezza illimitata)
    - color: Colore hex (default: "#FFEB3B" giallo)
      Disponibili: "#FFEB3B" giallo, "#FF9800" arancione, "#4CAF50" verde, "#2196F3" blu, "#E91E63" rosa, "#9C27B0" viola
    - position_x: Posizione X nel canvas (default: "0")
    - position_y: Posizione Y nel canvas (default: "0")

    Restituisce type="note_created" — l'app mostra automaticamente il pulsante "Modifica nota".

    Examples:
    - create_note(title="Comprare il latte")
    - create_note(title="Idea: app per fitness", color="#4CAF50")
    - create_note(title="Lista spesa:\\n- Pane\\n- Latte\\n- Uova")
    """
    user_id = authenticate_from_context(ctx)

    note = await note_client.create_note(
        user_id=user_id,
        title=title,
        position_x=position_x,
        position_y=position_y,
        color=color
    )

    return {
        "success": True,
        "type": "note_created",
        "note_id": note.get("note_id")
    }


async def update_note(
    ctx: Context,
    note_id: int,
    title: Optional[str] = None,
    position_x: Optional[str] = None,
    position_y: Optional[str] = None,
    color: Optional[str] = None
) -> Dict[str, Any]:
    """Aggiorna testo, colore o posizione di una nota esistente. Specifica solo i campi da modificare.

    Parameters:
    - note_id: ID della nota da aggiornare — ottienilo con get_notes() (obbligatorio)
    - title: Nuovo testo completo della nota (opzionale, lunghezza illimitata)
    - color: Nuovo colore hex (opzionale) — "#FFEB3B" giallo, "#FF9800" arancione, "#4CAF50" verde, "#2196F3" blu, "#E91E63" rosa, "#9C27B0" viola
    - position_x: Nuova posizione X nel canvas (opzionale)
    - position_y: Nuova posizione Y nel canvas (opzionale)

    Example:
        User: "Cambia il colore della nota 'Latte' in verde"
        → get_notes() → trova note_id=5
        → update_note(note_id=5, color="#4CAF50")
    """
    user_id = authenticate_from_context(ctx)

    await note_client.update_note(
        user_id=user_id,
        note_id=note_id,
        title=title,
        position_x=position_x,
        position_y=position_y,
        color=color
    )

    return {"success": True, "note_id": note_id}


async def delete_note(ctx: Context, note_id: int) -> Dict[str, Any]:
    """Elimina definitivamente una nota. Operazione irreversibile — la nota non può essere recuperata.

    IMPORTANTE: chiedi sempre conferma esplicita all'utente prima di chiamare questo tool.
    Non eliminare mai in automatico senza che l'utente abbia confermato.

    Parameters:
    - note_id: ID della nota da eliminare — ottienilo con get_notes() se non lo conosci

    Example:
        User: "Elimina la nota sul latte"
        → get_notes() → trova note_id=5 "Comprare il latte"
        → [chiedi conferma: "Vuoi eliminare la nota 'Comprare il latte'?"]
        → delete_note(note_id=5)
    """
    user_id = authenticate_from_context(ctx)

    await note_client.delete_note(user_id, note_id)

    return {"success": True, "note_id": note_id}


async def show_notes_to_user(ctx: Context) -> Dict[str, Any]:
    """Mostra le note all'utente nell'app mobile. L'app legge il type e renderizza la griglia autonomamente.

    Quando usare:
    - "Mostrami le note", "Quali note ho?", "Fammi vedere i miei appunti"

    Quando NON usare:
    - Per lookup interni o trovare un note_id → usa get_notes()
    """
    authenticate_from_context(ctx)

    return {"type": "note_list", "success": True}
