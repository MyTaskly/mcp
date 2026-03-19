"""MCP tools for task management."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastmcp import Context
from src.auth import authenticate_from_context
from src.client import task_client, category_client
from src.formatters import format_tasks_for_ui


async def get_tasks(
    ctx: Context,
    category_id: Optional[int] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    task_id: Optional[int] = None
) -> Dict[str, Any]:
    """Recupera i task dell'utente come JSON grezzo per uso interno (lookup, validazione, filtri).

    Non mostra nulla all'utente. Restituisce dati strutturati per elaborazione interna.

    Parameters:
    - task_id: ID specifico del task (per cercare un singolo task)
    - category_id: Filtra per ID categoria — se l'utente specifica il NOME, chiama prima get_my_categories() per ottenere l'ID
    - priority: Filtra per priorità — valori esatti: "Alta", "Media", "Bassa"
    - status: Filtra per stato — valori esatti: "In sospeso", "Completato", "Annullato"

    Quando usare:
    - Trovare task_id prima di modificare/completare/eliminare un task
    - Verificare se un task esiste
    - Filtrare task per elaborazione interna

    Quando NON usare:
    - Se l'utente chiede "Mostrami i task" → usa show_tasks_to_user()

    Example:
        User: "Completa il task Riunione"
        → get_tasks() per trovare task_id=12
        → complete_task(task_id=12)
    """
    user_id = authenticate_from_context(ctx)

    # Fetch tasks from FastAPI
    tasks = await task_client.get_tasks(user_id, category_id, priority, status, task_id)

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

    result = await task_client.update_task(
        user_id=user_id,
        task_id=task_id,
        title=title,
        description=description,
        end_time=end_time,
        duration_minutes=duration_minutes,
        priority=priority,
        status=status
    )

    return {
        "message": f"✅ Task aggiornato con successo",
        **result
    }


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

    # Update task status to Completato
    result = await task_client.update_task(
        user_id=user_id,
        task_id=task_id,
        status="Completato"
    )

    return {
        "message": f"Task marked as completed",
        **result
    }


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


async def get_next_due_task(
    ctx: Context,
    limit: int = 1
) -> Dict[str, Any]:
    """Restituisce i task con le scadenze più vicine nel futuro, ordinati per data crescente.

    Parameters:
    - limit: Quanti task restituire (default: 1, max: 20)

    Quando usare:
    - "Qual è il prossimo task in scadenza?" → limit=1
    - "Dammi le prossime 5 scadenze" → limit=5
    - "Quando scade il mio prossimo impegno?"
    """
    user_id = authenticate_from_context(ctx)

    # Validate limit
    if limit < 1:
        limit = 1
    if limit > 20:
        limit = 20

    # Get all tasks
    all_tasks = await task_client.get_tasks(user_id)
    now = datetime.now(timezone.utc)

    # Filter future tasks that are not completed
    future_tasks = []
    for task in all_tasks:
        end_time_str = task.get("end_time")
        if not end_time_str:
            continue

        try:
            end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)

            if end_time > now and task.get("status") != "Completato":
                task["end_time_dt"] = end_time  # For sorting
                future_tasks.append(task)
        except Exception:
            continue

    if not future_tasks:
        return {
            "success": False,
            "message": "Non ci sono task con scadenza futura",
            "tasks": []
        }

    # Sort by end_time (closest first) and take top N
    future_tasks.sort(key=lambda x: x["end_time_dt"])
    selected_tasks = future_tasks[:limit]

    # Remove the temporary sorting field
    for task in selected_tasks:
        if "end_time_dt" in task:
            del task["end_time_dt"]

    if limit == 1:
        return {
            "success": True,
            "task": selected_tasks[0],
            "tasks": selected_tasks,
            "total_upcoming": len(future_tasks),
            "message": f"Il prossimo task in scadenza è '{selected_tasks[0]['title']}' il {selected_tasks[0]['end_time']}"
        }
    else:
        return {
            "success": True,
            "tasks": selected_tasks,
            "total_upcoming": len(future_tasks),
            "returned": len(selected_tasks),
            "message": f"Prossimi {len(selected_tasks)} task in scadenza (su {len(future_tasks)} totali)"
        }


async def get_overdue_tasks(ctx: Context) -> List[Dict[str, Any]]:
    """Restituisce tutti i task non completati con scadenza già passata, ordinati dal più vecchio.

    Quando usare:
    - "Quali task ho scaduto?", "Mostra i task in ritardo", "Quali impegni ho mancato?"
    """
    user_id = authenticate_from_context(ctx)

    # Get all tasks
    all_tasks = await task_client.get_tasks(user_id)
    now = datetime.now(timezone.utc)

    # Filter overdue tasks
    overdue = []
    for task in all_tasks:
        end_time_str = task.get("end_time")
        if not end_time_str:
            continue

        try:
            end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)

            # Only if not completed and past due
            if end_time < now and task.get("status") != "Completato":
                days_overdue = (now - end_time).days
                task["days_overdue"] = days_overdue
                task["end_time_dt"] = end_time  # For sorting
                overdue.append(task)
        except Exception:
            continue

    # Sort by end_time (oldest first)
    overdue.sort(key=lambda x: x["end_time_dt"])

    # Remove temporary sorting field
    for task in overdue:
        if "end_time_dt" in task:
            del task["end_time_dt"]

    return overdue


async def get_upcoming_tasks(
    ctx: Context,
    days: int = 7
) -> List[Dict[str, Any]]:
    """Restituisce i task non completati con scadenza nei prossimi N giorni, ordinati per data.

    Parameters:
    - days: Finestra temporale in giorni (default: 7)

    Quando usare:
    - "Cosa ho domani?" → days=1
    - "Cosa scade questa settimana?" → days=7
    - "Mostra i prossimi impegni dei prossimi 30 giorni" → days=30
    """
    user_id = authenticate_from_context(ctx)

    # Get all tasks
    all_tasks = await task_client.get_tasks(user_id)
    now = datetime.now(timezone.utc)

    # Calculate future date (end of day N days from now)
    from datetime import timedelta
    future_date = now.replace(hour=23, minute=59, second=59) + timedelta(days=days)

    # Filter upcoming tasks
    upcoming = []
    for task in all_tasks:
        end_time_str = task.get("end_time")
        if not end_time_str:
            continue

        try:
            end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)

            # Between now and future_date, not completed
            if now < end_time <= future_date and task.get("status") != "Completato":
                days_until_due = (end_time - now).days
                task["days_until_due"] = days_until_due
                task["end_time_dt"] = end_time  # For sorting
                upcoming.append(task)
        except Exception:
            continue

    # Sort by end_time (closest first)
    upcoming.sort(key=lambda x: x["end_time_dt"])

    # Remove temporary sorting field
    for task in upcoming:
        if "end_time_dt" in task:
            del task["end_time_dt"]

    return upcoming


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
            "message": f"❌ Titolo troppo lungo ({len(title)} caratteri). Massimo 100 caratteri. Usa una versione più breve o sposta i dettagli nella descrizione.",
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
                "message": f"❌ Categoria '{category_used}' non trovata. Categorie esistenti: {', '.join(category_names)}",
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
            "type": "task_created",
            "message": f"✅ Task '{title}' creato con successo in '{category_used}'",
            "task": result,
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
    """Mostra i task all'utente nell'app mobile con formattazione UI completa e filtri.

    Restituisce type="task_list" — l'app React Native renderizza automaticamente la lista formattata.

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

    Example:
        User: "Mostra i task ad alta priorità"
        → show_tasks_to_user(priority="Alta")
    """
    user_id = authenticate_from_context(ctx)

    # Get tasks with optional filters
    tasks = await task_client.get_tasks(user_id, category_id, priority, status)

    # Apply date filters
    if due_date or start_date or end_date:
        from datetime import datetime, timezone
        filtered_tasks = []

        for task in tasks:
            end_time_str = task.get("end_time")
            if not end_time_str:
                continue

            try:
                end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                if end_time.tzinfo is None:
                    end_time = end_time.replace(tzinfo=timezone.utc)

                task_date = end_time.date()

                # Filter by specific due_date
                if due_date:
                    filter_date = datetime.fromisoformat(due_date).date()
                    if task_date == filter_date:
                        filtered_tasks.append(task)
                # Filter by date range
                elif start_date or end_date:
                    include_task = True

                    if start_date:
                        filter_start = datetime.fromisoformat(start_date).date()
                        if task_date < filter_start:
                            include_task = False

                    if end_date and include_task:
                        filter_end = datetime.fromisoformat(end_date).date()
                        if task_date > filter_end:
                            include_task = False

                    if include_task:
                        filtered_tasks.append(task)
            except Exception:
                continue

        tasks = filtered_tasks

    # Format for UI
    formatted_response = format_tasks_for_ui(tasks)

    # Add filters_applied metadata
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
        date_range = f"{start_date or 'start'} to {end_date or 'end'}"
        filters_applied["date_range"] = date_range

    if filters_applied:
        formatted_response["filters_applied"] = filters_applied

    return formatted_response
