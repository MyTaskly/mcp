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
    """Recupera i task dell'utente per USO INTERNO (lookup, validazione, filtri).

    Questo tool restituisce dati JSON semplici senza formattazione UI.
    NON mostra nulla all'utente sullo schermo dell'app.

    Authentication:
        Requires valid JWT token in Authorization header: "Bearer <token>"

    QUANDO USARE QUESTO TOOL:
    - ✅ Trovare task_id prima di modificare/completare un task
    - ✅ Filtrare task per categoria/priorità/stato per logica interna
    - ✅ Verificare se un task esiste
    - ❌ NON usare quando l'utente chiede "Mostrami i task" (usa show_tasks_to_user)

    Usa questo tool per:
    - Ottenere TUTTI i task: non specificare filtri
    - Cercare un task SPECIFICO: usa task_id
    - Filtrare per CATEGORIA: usa category_id (IMPORTANTE: se l'utente specifica il NOME della categoria,
      devi PRIMA chiamare get_my_categories() per trovare l'ID corrispondente, POI chiamare get_tasks con category_id)
    - Filtrare per PRIORITÀ: usa priority ("Alta", "Media", "Bassa")
    - Filtrare per STATO: usa status ("In sospeso", "Completato", "Annullato")
    - Combinare più filtri: usa multiple opzioni insieme

    PROCEDURA per filtrare per categoria quando l'utente specifica il NOME:
    1. Chiama get_my_categories() per ottenere tutte le categorie con i loro ID
    2. Trova la categoria con il nome corrispondente
    3. Usa il category_id trovato per chiamare get_tasks(category_id=X)

    Per MOSTRARE i task all'utente, usa show_tasks_to_user() invece.

    Example usage:
        User: "Completa il task Riunione"
        Bot reasoning: "Devo trovare l'ID del task Riunione"
        Bot calls: get_tasks()
        Bot finds: task_id=12 per "Riunione"
        Bot calls: complete_task(task_id=12)
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
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """Modifica un task esistente tramite il suo ID.

    ⚠️ IMPORTANTE - PROCEDURA OBBLIGATORIA:
    1. PRIMA chiama get_tasks() per ottenere la lista completa dei task con i loro ID
    2. Identifica il task_id corretto dalla lista (cerca per titolo, categoria, ecc.)
    3. POI chiama update_task() con il task_id trovato

    ❌ NON cercare di indovinare il task_id!
    ❌ NON usare task_id di task precedentemente modificati senza verificare!
    ✅ Chiama SEMPRE get_tasks() prima per ottenere l'ID aggiornato!

    Authentication:
        Requires valid JWT token in Authorization header: "Bearer <token>"

    Parameters:
    - task_id: ID del task da modificare (OBBLIGATORIO - ottienilo con get_tasks!)
    - title: Nuovo titolo del task (opzionale)
    - description: Nuova descrizione (opzionale)
    - start_time: Data/ora inizio (formato: YYYY-MM-DD HH:MM:SS) (opzionale)
    - end_time: Data/ora scadenza (formato: YYYY-MM-DD HH:MM:SS) (opzionale)
    - priority: Nuova priorità ("Alta", "Media", "Bassa") (opzionale)
    - status: Nuovo stato ("In sospeso", "Completato", "Annullato") (opzionale)

    Nota: Specifica solo i campi che vuoi modificare. I campi non specificati mantengono il valore attuale.

    Esempio corretto:
    1. Chiama get_tasks() → ottieni lista con task_id=42 per "Meeting"
    2. Chiama update_task(task_id=42, title="Riunione importante")
    """
    user_id = authenticate_from_context(ctx)

    result = await task_client.update_task(
        user_id=user_id,
        task_id=task_id,
        title=title,
        description=description,
        start_time=start_time,
        end_time=end_time,
        priority=priority,
        status=status
    )

    return {
        "message": f"✅ Task aggiornato con successo",
        **result
    }


async def complete_task(ctx: Context, task_id: int) -> Dict[str, Any]:
    """Segna un task come COMPLETATO.

    Questo è uno shortcut veloce per marcare un task come completato.
    Se hai bisogno di cambiare lo stato a qualcos'altro, usa update_task.

    Authentication:
        Requires valid JWT token in Authorization header: "Bearer <token>"

    Parameters:
    - task_id: ID del task da completare

    Esempi:
    - Voce: "Segna il task 5 come completato" -> complete_task(task_id=5)
    - API: complete_task(task_id=5)
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
    """Ottieni statistiche complete sui task dell'utente.

    Restituisce metriche utili per:
    - Monitorare la produttività
    - Vedere quanti task sono completati vs in sospeso
    - Analizzare la distribuzione per priorità e stato
    - Ottenere informazioni sui prossimi impegni

    Authentication:
        Requires valid JWT token in Authorization header: "Bearer <token>"

    Utile per domande come:
    - "Quanti task ho completato?"
    - "Quanti task ad alta priorità ho?"
    - "Qual è la mia categoria più carica?"
    """
    user_id = authenticate_from_context(ctx)

    # Get statistics from FastAPI
    stats = await task_client.get_task_statistics(user_id)

    return stats


async def get_next_due_task(
    ctx: Context,
    limit: int = 1
) -> Dict[str, Any]:
    """Ottieni i PROSSIMI task in scadenza (i task con le date di fine più vicine nel futuro).

    Authentication:
        Requires valid JWT token in Authorization header: "Bearer <token>"

    Parameters:
    - limit: Numero di task da restituire (default: 1, massimo: 20)

    Perfetto per domande come:
    - "Qual è il prossimo task in scadenza?" (limit=1)
    - "Dammi i prossimi 3 task in scadenza" (limit=3)
    - "Quando scade il prossimo impegno?"
    - "Quali sono le prossime 5 scadenze?" (limit=5)

    Restituisce i task con le date di scadenza più vicine, indipendentemente da quando siano
    (domani, tra una settimana, o tra un anno).
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
    """Ottieni tutti i task SCADUTI (la data di fine è passata).

    Authentication:
        Requires valid JWT token in Authorization header: "Bearer <token>"

    Perfetto per domande come:
    - "Quali task ho scaduto?"
    - "Quali impegni ho mancato?"
    - "Mostra i task in ritardo"

    I task ritornati sono ordinati per data di scadenza (più vecchi prima).
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
    """Ottieni i task in scadenza nei prossimi N giorni.

    Authentication:
        Requires valid JWT token in Authorization header: "Bearer <token>"

    Parameters:
    - days: Numero di giorni da controllare (default: 7)

    Perfetto per:
    - "Cosa ho da fare domani?" (days=1)
    - "Quali task scadono questa settimana?" (days=7)
    - "Mostra i prossimi impegni" (days=7)

    I task sono ordinati per data di scadenza (più vicini prima).
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
    start_time: Optional[str] = None,
    description: Optional[str] = None,
    priority: str = "Bassa"
) -> Dict[str, Any]:
    """Crea un NUOVO task con gestione intelligente delle categorie.

    Questo è il tool principale per aggiungere task!

    Authentication:
        Requires valid JWT token in Authorization header: "Bearer <token>"

    Parameters:
    - title: Titolo del task (OBBLIGATORIO, MAX 100 caratteri, BREVE E CONCISO)
    - category_name: Categoria (default: "Generale"). DEVE ESISTERE - non crea categorie automaticamente
    - end_time: Scadenza con ORA (formato: "YYYY-MM-DD HH:MM:SS" o "YYYY-MM-DD HH:MM")
    - start_time: Inizio del task (opzionale, per calcolo durata)
    - description: Descrizione con TUTTI I DETTAGLI (contesto, note, informazioni aggiuntive)
    - priority: "Alta", "Media", o "Bassa" (dedurre dal contesto)

    IMPORTANTE - DIVISIONE TITOLO/DESCRIZIONE:
    - Titolo: MAX 100 caratteri, SOLO per identificare rapidamente il task
      Esempi: "Riunione Vicenza" (NON "Riunione di lavoro importante a Vicenza")
              "Spesa supermercato" (NON "Andare a fare la spesa al supermercato")
              "Chiamare Mario" (NON "Ricordarsi di chiamare Mario per il progetto")

    - Descrizione: USA SEMPRE per dettagli, contesto, note aggiuntive
      Esempi: title="Riunione Vicenza" description="Riunione di lavoro importante alle 16:00"
              title="Dentista" description="Controllo semestrale, portare tessera sanitaria"
              title="Studiare matematica" description="Capitoli 5-7, esercizi da pag 120 a 135"

    - End_time: SEMPRE includere l'ora appropriata al contesto (pranzo=12:00, cena=19:00, etc)
    - Se categoria non esiste, ritorna errore con suggerimenti

    Esempi di uso CORRETTI:
    - add_task(title="Riunione team", description="Meeting settimanale con il team di sviluppo", end_time="2025-12-15 10:00")
    - add_task(title="Pranzo Marco", description="Pranzo con Marco al ristorante Da Luigi", category_name="Personale", end_time="2025-12-16 12:30")
    - add_task(title="Studiare matematica", description="Studiare 2 ore - Capitoli 5-7", end_time="2025-12-15 16:00")
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
            start_time=start_time,
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
    """
    MOSTRA i task all'utente con formattazione UI completa e filtri avanzati.

    Questo tool è specificamente per VISUALIZZARE i task sullo schermo dell'app mobile.
    Include formattazione ricca con date formattate, pulsanti azioni, e configurazione UI.

    Authentication:
        Requires valid JWT token in Authorization header: "Bearer <token>"

    Parameters:
    - category_id: Filtra per ID categoria (opzionale)
    - priority: Filtra per priorità ("Alta", "Media", "Bassa") (opzionale)
    - status: Filtra per stato ("In sospeso", "Completato", "Annullato") (opzionale)
    - due_date: Filtra per data di scadenza specifica (formato: "YYYY-MM-DD") (opzionale)
    - start_date: Filtra task con scadenza >= start_date (formato: "YYYY-MM-DD") (opzionale)
    - end_date: Filtra task con scadenza <= end_date (formato: "YYYY-MM-DD") (opzionale)

    Note sui filtri:
    - Usa due_date per una data specifica, OPPURE start_date/end_date per un range
    - I filtri possono essere combinati (es: categoria + priorità + range date)

    Returns:
        {
            "type": "task_list",
            "version": "1.0",
            "tasks": [
                {
                    "id": 1,
                    "title": "Riunione team",
                    "description": "Meeting settimanale",
                    "endTime": "2025-12-15T10:00:00",
                    "endTimeFormatted": "Lunedì 15 dicembre, 10:00",
                    "category": "Lavoro",
                    "priority": "Alta",
                    "status": "In sospeso",
                    "actions": {...}
                },
                ...
            ],
            "filters_applied": {
                "category_id": 1,
                "priority": "Alta",
                "date_range": "2025-12-01 to 2025-12-31"
            },
            "summary": {
                "total": 10,
                "pending": 6,
                "completed": 4,
                "high_priority": 2
            },
            "voice_summary": "Hai 10 task, di cui 2 ad alta priorità. 6 sono in sospeso e 4 completati.",
            "ui_hints": {
                "display_mode": "list",
                "enable_swipe_actions": true,
                "group_by": "category"
            }
        }

    QUANDO USARE QUESTO TOOL:
    - ✅ Utente chiede: "Mostrami i task"
    - ✅ Utente chiede: "Quali task ho?"
    - ✅ Utente chiede: "Fammi vedere i miei impegni"
    - ✅ Utente chiede: "Mostra i task di categoria Lavoro"
    - ✅ Utente chiede: "Mostra i task ad alta priorità di questa settimana"
    - ✅ Utente chiede: "Fammi vedere i task che scadono il 15 dicembre"
    - ❌ NON usare per lookup interni (usa get_tasks invece)

    L'app React Native renderizza automaticamente una lista formattata
    quando riceve type: "task_list".

    Example usage:
        User: "Mostrami i task ad alta priorità"
        Bot calls: show_tasks_to_user(priority="Alta")
        Bot response: "Ecco i tuoi task ad alta priorità" (l'app mostra la lista filtrata)

        User: "Mostra i task che scadono questa settimana"
        Bot calls: show_tasks_to_user(start_date="2025-12-13", end_date="2025-12-19")
        Bot response: "Ecco i task che scadono questa settimana" (l'app mostra la lista filtrata)
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
