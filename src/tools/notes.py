"""MCP tools for note management."""

from typing import Dict, Any, List, Optional
from fastmcp import Context
from src.auth import authenticate_from_context
from src.client import note_client
from src.formatters import format_notes_for_ui


async def get_notes(ctx: Context) -> Dict[str, Any]:
    """
    Recupera tutte le note dell'utente per USO INTERNO (lookup, validazione).

    Questo tool restituisce dati JSON semplici senza formattazione UI.
    NON mostra nulla all'utente sullo schermo dell'app.

    Authentication:
        Requires valid JWT token in Authorization header: "Bearer <token>"

    Returns:
        {
            "notes": [
                {
                    "note_id": 1,
                    "title": "Comprare il latte",
                    "position_x": "0",
                    "position_y": "0",
                    "color": "#FFEB3B",
                    "created_at": "2025-12-15T10:30:00"
                },
                ...
            ],
            "total": 5
        }

    QUANDO USARE QUESTO TOOL:
    - ✅ Trovare note_id prima di modificare/eliminare una nota
    - ✅ Validare che una nota esista
    - ✅ Cercare una nota per contenuto
    - ❌ NON usare quando l'utente chiede "Mostrami le note" (usa show_notes_to_user)

    Per MOSTRARE le note all'utente, usa show_notes_to_user() invece.

    Example usage:
        User: "Elimina la nota sul latte"
        Bot reasoning: "Devo trovare l'ID della nota sul latte"
        Bot calls: get_notes()
        Bot finds: note_id=5 per "Comprare il latte"
        Bot calls: delete_note(note_id=5)
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
    """
    Crea una nota rapida come un post-it digitale.

    Le note sono semplici appunti con un UNICO campo di testo (title).
    Non hanno descrizione separata - tutto il contenuto va nel campo 'title'.
    Perfette per catturare idee veloci, promemoria, pensieri, liste, appunti lunghi.

    Authentication:
        Requires valid JWT token in Authorization header: "Bearer <token>"

    Parameters:
    - title: Testo completo della nota (lunghezza illimitata - può contenere testi molto lunghi)
    - position_x: Posizione X nel canvas (default: "0")
    - position_y: Posizione Y nel canvas (default: "0")
    - color: Colore della nota in formato hex (default: "#FFEB3B" giallo)
      Colori comuni: "#FFEB3B" (giallo), "#FF9800" (arancione), "#4CAF50" (verde),
                     "#2196F3" (blu), "#E91E63" (rosa), "#9C27B0" (viola)

    Returns:
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

    L'app React Native mostrerà automaticamente un bottone "Modifica nota"
    quando riceve type: "note_created".

    Esempi:
    - create_note(title="Comprare il latte")
    - create_note(title="Idea: app per fitness", color="#4CAF50")
    - create_note(title="Chiamare dentista domani")
    - create_note(title="Lista spesa:\\n- Pane\\n- Latte\\n- Uova\\n- Formaggio...")

    Example usage:
        User: "Crea una nota: Chiamare dentista domani"
        Bot calls: create_note(
            authorization="Bearer eyJ...",
            title="Chiamare dentista domani",
            color="#4CAF50"
        )
        Bot response: "✅ Nota creata: 'Chiamare dentista domani'"
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
        "message": "✅ Nota creata con successo",
        "note": note
    }


async def update_note(
    ctx: Context,
    note_id: int,
    title: Optional[str] = None,
    position_x: Optional[str] = None,
    position_y: Optional[str] = None,
    color: Optional[str] = None
) -> Dict[str, Any]:
    """
    Aggiorna il testo, posizione o colore di una nota.

    Le note hanno un UNICO campo di testo (title) - non hanno descrizione separata.

    Authentication:
        Requires valid JWT token in Authorization header: "Bearer <token>"

    Parameters:
    - note_id: ID della nota da aggiornare
    - title: Nuovo testo della nota (opzionale, lunghezza illimitata)
    - position_x: Nuova posizione X nel canvas (opzionale)
    - position_y: Nuova posizione Y nel canvas (opzionale)
    - color: Nuovo colore in formato hex (opzionale, es: "#FF9800" per arancione)
      Colori comuni: "#FFEB3B" (giallo), "#FF9800" (arancione), "#4CAF50" (verde),
                     "#2196F3" (blu), "#E91E63" (rosa), "#9C27B0" (viola)

    Returns:
        {
            "message": "✅ Nota aggiornata con successo",
            "note_id": 5
        }

    Esempi:
    - update_note(note_id=5, title="Comprare il pane")
    - update_note(note_id=5, color="#4CAF50")
    - update_note(note_id=5, title="Idea migliorata con dettagli aggiuntivi...", color="#2196F3")

    Example usage:
        User: "Cambia il colore della nota 'Latte' in verde"
        Bot calls:
            1. get_notes() → trova note_id=5 con title="Comprare il latte"
            2. update_note(note_id=5, color="#4CAF50")
        Bot response: "✅ Nota aggiornata con colore verde"
    """
    user_id = authenticate_from_context(ctx)

    result = await note_client.update_note(
        user_id=user_id,
        note_id=note_id,
        title=title,
        position_x=position_x,
        position_y=position_y,
        color=color
    )

    return {
        "message": "✅ Nota aggiornata con successo",
        "note_id": note_id,
        **result
    }


async def delete_note(ctx: Context, note_id: int) -> Dict[str, Any]:
    """
    Elimina una nota definitivamente.

    Authentication:
        Requires valid JWT token in Authorization header: "Bearer <token>"

    Parameters:
    - note_id: ID della nota da eliminare

    Returns:
        {
            "message": "✅ Nota eliminata con successo",
            "note_id": 5
        }

    Esempio:
    - delete_note(note_id=5)

    Example usage:
        User: "Elimina la nota 'Latte'"
        Bot calls:
            1. get_notes() → trova note_id=5 con title="Comprare il latte"
            2. delete_note(note_id=5)
        Bot response: "✅ Nota 'Comprare il latte' eliminata"
    """
    user_id = authenticate_from_context(ctx)

    result = await note_client.delete_note(user_id, note_id)

    return {
        "message": "✅ Nota eliminata con successo",
        "note_id": note_id,
        **result
    }


async def show_notes_to_user(ctx: Context) -> Dict[str, Any]:
    """
    MOSTRA le note all'utente con formattazione UI completa.

    Questo tool è specificamente per VISUALIZZARE le note sullo schermo dell'app mobile.
    Include formattazione ricca con colori, pulsanti azioni, e configurazione UI.

    Authentication:
        Requires valid JWT token in Authorization header: "Bearer <token>"

    Returns:
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
                    "createdAt": "2025-12-15T10:30:00"
                },
                ...
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
                "enable_color_picker": true,
                "enable_drag_and_drop": true
            }
        }

    QUANDO USARE QUESTO TOOL:
    - ✅ Utente chiede: "Mostrami le note"
    - ✅ Utente chiede: "Quali note ho?"
    - ✅ Utente chiede: "Fammi vedere i miei appunti"
    - ❌ NON usare per lookup interni (usa get_notes invece)

    L'app React Native renderizza automaticamente una griglia formattata
    quando riceve type: "note_list".

    Example usage:
        User: "Mostrami le mie note"
        Bot calls: show_notes_to_user()
        Bot response: "Ecco le tue 15 note" (l'app mostra la griglia formattata)
    """
    user_id = authenticate_from_context(ctx)

    # Get notes
    notes = await note_client.get_notes(user_id)

    # Format for UI
    formatted_response = format_notes_for_ui(notes)

    return formatted_response
