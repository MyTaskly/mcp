"""MCP tools for task management."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastmcp import Context
from src.auth import authenticate_from_context
from src.client import task_client, category_client


async def get_tasks(
    ctx: Context,
    category_id: Optional[int] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    task_id: Optional[int] = None,
    title: Optional[str] = None
) -> Dict[str, Any]:
    """Recupera i task dell'utente come JSON grezzo per uso interno (lookup, validazione, filtri).

    Non mostra nulla all'utente. Restituisce dati strutturati per elaborazione interna.

    Parameters:
    - task_id: ID specifico del task (per cercare un singolo task)
    - title: Filtra per titolo con corrispondenza parziale case-insensitive — se più task corrispondono, li restituisce tutti
    - category_id: Filtra per ID categoria — se l'utente specifica il NOME, chiama prima get_my_categories() per ottenere l'ID
    - priority: Filtra per priorità — valori esatti: "Alta", "Media", "Bassa"
    - status: Filtra per stato — valori esatti: "In sospeso", "Completato", "Annullato"

    Quando usare:
    - Trovare task_id prima di modificare/completare/eliminare un task
    - Verificare se un task esiste
    - Filtrare task per elaborazione interna

    Attenzione nomi duplicati: se title restituisce più task, mostra i risultati all'utente e chiedi quale intende.

    Quando NON usare:
    - Se l'utente chiede "Mostrami i task" → usa show_tasks_to_user()

    Example:
        User: "Completa il task Riunione"
        → get_tasks(title="Riunione") per trovare task_id=12
        → complete_task(task_id=12)
    """
    user_id = authenticate_from_context(ctx)

    # Fetch tasks from FastAPI
    tasks = await task_client.get_tasks(user_id, category_id, priority, status, task_id)

    # Filter by title (partial, case-insensitive) client-side
    if title:
        title_lower = title.lower()
        tasks = [t for t in tasks if title_lower in t.get("title", "").lower()]

    return {
        "tasks": tasks,
        "total": len(tasks)
    }


async def update_task(
    ctx: Context,
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    end_time: Optional[str] = None,
    duration_minutes: Optional[int] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """Modifica un task esistente tramite il suo ID. Specifica solo i campi da aggiornare.

    Procedura obbligatoria: chiama sempre get_tasks() prima per ottenere il task_id corretto.
    Non indovinare l'ID.

    Parameters:
    - task_id: ID del task da modificare — ottienilo sempre con get_tasks() (obbligatorio)
    - title: Nuovo titolo (max 100 caratteri, opzionale)
    - description: Nuova descrizione con dettagli aggiuntivi (opzionale)
    - end_time: Scadenza in timezone locale dell'utente — formato "YYYY-MM-DD HH:MM:SS" (opzionale)
    - duration_minutes: Durata in minuti, range 1-10080 (opzionale)
    - priority: "Alta", "Media" o "Bassa" — solo valori italiani esatti (opzionale)
    - status: "In sospeso", "Completato" o "Annullato" — solo valori italiani esatti (opzionale)

    Example:
        User: "Sposta la riunione a domani"
        → get_tasks() → trova task_id=42 "Riunione team"
        → update_task(task_id=42, end_time="2026-03-20 10:00:00")
    """
    user_id = authenticate_from_context(ctx)

    await task_client.update_task(
        user_id=user_id,
        task_id=task_id,
        title=title,
        description=description,
        end_time=end_time,
        duration_minutes=duration_minutes,
        priority=priority,
        status=status
    )

    return {"success": True, "task_id": task_id}


async def complete_task(ctx: Context, task_id: int) -> Dict[str, Any]:
    """Segna un task come completato. Shortcut rapido per update_task(status="Completato").

    Parameters:
    - task_id: ID del task da completare — ottienilo con get_tasks() se non lo conosci

    Quando usare:
    - L'utente dice "fatto", "completato", "ho finito [task]"

    Quando NON usare:
    - Per cambiare stato a "Annullato" → usa update_task(status="Annullato")
    """
    user_id = authenticate_from_context(ctx)

    await task_client.update_task(user_id=user_id, task_id=task_id, status="Completato")

    return {"success": True, "task_id": task_id}


async def get_task_stats(ctx: Context) -> Dict[str, Any]:
    """Restituisce statistiche aggregate sui task dell'utente: conteggi per stato, priorità e categoria.

    Quando usare:
    - "Quanti task ho completato?", "Quanti task ad alta priorità ho?"
    - "Qual è la mia categoria più carica?", "Come sto con la produttività?"
    """
    user_id = authenticate_from_context(ctx)

    # Get statistics from FastAPI
    stats = await task_client.get_task_statistics(user_id)

    return stats


async def get_overdue_tasks(ctx: Context) -> List[Dict[str, Any]]:
    """Restituisce tutti i task non completati con scadenza già passata, ordinati dal più vecchio.

    Quando usare:
    - "Quali task ho scaduto?", "Mostra i task in ritardo", "Quali impegni ho mancato?"
    """
    user_id = authenticate_from_context(ctx)

    all_tasks = await task_client.get_tasks(user_id)
    now = datetime.now(timezone.utc)

    overdue = []
    for task in all_tasks:
        end_time_str = task.get("end_time")
        if not end_time_str:
            continue

        try:
            end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)

            if end_time < now and task.get("status") != "Completato":
                task["days_overdue"] = (now - end_time).days
                task["end_time_dt"] = end_time
                overdue.append(task)
        except Exception:
            continue

    overdue.sort(key=lambda x: x["end_time_dt"])
    for task in overdue:
        del task["end_time_dt"]

    return overdue


async def get_upcoming_tasks(
    ctx: Context,
    days: Optional[int] = None,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """Restituisce i task non completati con scadenza futura, ordinati per data crescente.

    Parameters:
    - days: Filtra entro una finestra temporale in giorni (opzionale)
    - limit: Numero massimo di task da restituire (opzionale)

    Combinazioni utili:
    - nessun parametro → tutti i task futuri
    - days=7 → task che scadono nei prossimi 7 giorni
    - limit=3 → i 3 task con scadenza più vicina in assoluto
    - days=7, limit=3 → i 3 task più vicini entro questa settimana

    Quando usare:
    - "Qual è il prossimo task?" → limit=1
    - "Cosa ho domani?" → days=1
    - "Cosa scade questa settimana?" → days=7
    - "Dammi le prossime 5 scadenze" → limit=5
    """
    from datetime import timedelta

    user_id = authenticate_from_context(ctx)

    all_tasks = await task_client.get_tasks(user_id)
    now = datetime.now(timezone.utc)
    future_cutoff = now.replace(hour=23, minute=59, second=59) + timedelta(days=days) if days is not None else None

    upcoming = []
    for task in all_tasks:
        end_time_str = task.get("end_time")
        if not end_time_str:
            continue

        try:
            end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)

            if end_time <= now or task.get("status") == "Completato":
                continue
            if future_cutoff is not None and end_time > future_cutoff:
                continue

            task["days_until_due"] = (end_time - now).days
            task["end_time_dt"] = end_time
            upcoming.append(task)
        except Exception:
            continue

    upcoming.sort(key=lambda x: x["end_time_dt"])

    if limit is not None:
        upcoming = upcoming[:limit]

    for task in upcoming:
        del task["end_time_dt"]

    return {
        "success": True,
        "tasks": upcoming,
        "total": len(upcoming)
    }


async def add_task(
    ctx: Context,
    title: str,
    category_name: str = "Generale",
    end_time: Optional[str] = None,
    duration_minutes: Optional[int] = None,
    description: Optional[str] = None,
    priority: str = "Bassa"
) -> Dict[str, Any]:
    """Crea un nuovo task. La categoria deve esistere — restituisce errore con suggerimenti se non trovata.

    Parameters:
    - title: Titolo breve e identificativo (obbligatorio, max 100 caratteri)
      Buono: "Riunione Vicenza" | Cattivo: "Riunione di lavoro importante a Vicenza il pomeriggio"
    - category_name: Nome categoria esistente (default: "Generale") — non crea categorie automaticamente
    - end_time: Scadenza in timezone locale — formato "YYYY-MM-DD HH:MM:SS", includi ora appropriata al contesto
    - duration_minutes: Durata prevista in minuti, range 1-10080 (opzionale)
    - description: Tutti i dettagli, contesto e note aggiuntive (opzionale)
    - priority: "Alta", "Media" o "Bassa" — deduci dal contesto (default: "Bassa")

    Regola titolo/descrizione: il titolo identifica, la descrizione spiega.
    Metti SEMPRE i dettagli nella descrizione, non nel titolo.

    Examples:
    - add_task(title="Riunione team", end_time="2026-03-20 10:00:00", description="Meeting settimanale")
    - add_task(title="Palestra", category_name="Sport", end_time="2026-03-20 18:00:00", duration_minutes=60)
    """
    user_id = authenticate_from_context(ctx)

    # Validate title length
    if len(title) > 100:
        return {
            "success": False,
            "message": f"Title too long ({len(title)} chars). Max 100 chars. Move details to description.",
            "title_length": len(title),
            "max_length": 100
        }

    # Get all categories to find the category_id
    try:
        categories = await category_client.get_categories(user_id)

        # Find category by name
        category_id = None
        category_used = category_name or "Generale"

        for cat in categories:
            if cat["name"].lower() == category_used.lower():
                category_id = cat["category_id"]
                category_used = cat["name"]  # Use exact name from database
                break

        if category_id is None:
            # Category not found, return error with suggestions
            category_names = [cat["name"] for cat in categories[:5]]
            return {
                "success": False,
                "message": f"Category '{category_used}' not found. Existing categories: {', '.join(category_names)}",
                "category_suggestions": category_names,
                "action_required": "ask_user_to_create_category"
            }

        # Create task via FastAPI with category_id
        result = await task_client.create_task(
            user_id=user_id,
            title=title,
            category_id=category_id,
            end_time=end_time,
            duration_minutes=duration_minutes,
            description=description,
            priority=priority or "Bassa"
        )

        return {
            "success": True,
            "task_id": result.get("task_id"),
            "category_used": category_used
        }
    except Exception as e:
        error_msg = str(e)
        return {
            "success": False,
            "message": f"Failed to create task: {error_msg}",
            "error": error_msg
        }


async def show_tasks_to_user(
    ctx: Context,
    category_id: Optional[int] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    due_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """Mostra i task all'utente nell'app mobile. L'app legge il type e renderizza la lista autonomamente.

    Parameters:
    - category_id: Filtra per ID categoria (opzionale)
    - priority: "Alta", "Media" o "Bassa" (opzionale)
    - status: "In sospeso", "Completato" o "Annullato" (opzionale)
    - due_date: Data specifica formato "YYYY-MM-DD" (opzionale, alternativo a start/end_date)
    - start_date: Inizio range date formato "YYYY-MM-DD" (opzionale)
    - end_date: Fine range date formato "YYYY-MM-DD" (opzionale)

    I filtri sono combinabili. Usa due_date per un giorno preciso, start_date/end_date per un intervallo.

    Quando usare:
    - "Mostrami i task", "Quali task ho?", "Fammi vedere i miei impegni"
    - "Mostra i task ad alta priorità di questa settimana"
    - "Task che scadono il 15 marzo"

    Quando NON usare:
    - Per lookup interni o trovare un task_id → usa get_tasks()
    """
    authenticate_from_context(ctx)

    filters_applied = {}
    if category_id:
        filters_applied["category_id"] = category_id
    if priority:
        filters_applied["priority"] = priority
    if status:
        filters_applied["status"] = status
    if due_date:
        filters_applied["due_date"] = due_date
    if start_date or end_date:
        filters_applied["date_range"] = f"{start_date or 'start'} to {end_date or 'end'}"

    return {
        "type": "task_list",
        "success": True,
        **({"filters_applied": filters_applied} if filters_applied else {})
    }
