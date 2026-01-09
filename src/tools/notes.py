"""MCP tools for note management."""

from typing import Dict, Any, List, Optional
from fastmcp import Context
from src.auth import authenticate_from_context
from src.client import note_client


async def get_notes(ctx: Context) -> List[Dict[str, Any]]:
    """
    Recupera tutte le note salvate dall'utente.

    Le note sono come post-it digitali con un singolo testo (campo 'title').
    Non hanno descrizione o contenuto separato.

    Authentication:
        Requires valid JWT token in Authorization header: "Bearer <token>"

    Returns:
        [
            {
                "note_id": 1,
                "title": "Comprare il latte",
                "position_x": "0",
                "position_y": "0",
                "color": "#FFEB3B",
                "created_at": "2025-12-15T10:30:00"
            },
            ...
        ]

    Example usage:
        User: "Mostrami le mie note"
        Bot calls: get_notes(authorization="Bearer eyJ...")
        Bot response: "Hai 5 note salvate: 'Comprare il latte', 'Chiamare dentista', ..."
    """
    user_id = authenticate_from_context(ctx)
    notes = await note_client.get_notes(user_id)
    return notes


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
            "note_id": 456,
            "title": "Comprare il latte",
            "position_x": "0",
            "position_y": "0",
            "color": "#FFEB3B",
            "message": "✅ Nota creata con successo"
        }

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

    return note


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
