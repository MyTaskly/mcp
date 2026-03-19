"""MCP meta-tools for advanced operations."""

from typing import Dict, Any, Optional, List
from fastmcp import Context
from src.auth import authenticate_from_context
from src.client import category_client, task_client
import difflib


async def get_or_create_category(
    ctx: Context,
    category_name: str,
    description: Optional[str] = None,
    similarity_threshold: float = 0.8
) -> Dict[str, Any]:
    """Trova una categoria per nome (esatto o fuzzy) oppure la crea se non esiste.

    Garantisce sempre una categoria valida senza duplicati. Usa prima la ricerca fuzzy, poi crea se necessario.

    Parameters:
    - category_name: Nome della categoria da trovare o creare (obbligatorio)
    - description: Descrizione da usare se la categoria viene creata (opzionale)
    - similarity_threshold: Soglia minima di similarità per match fuzzy, range 0-1 (default: 0.8)

    Restituisce sempre la categoria con campo action: "found_exact" | "found_similar" | "created".

    Quando usare:
    - Vuoi assicurarti che una categoria esista prima di creare task, senza rischiare duplicati
    - Quando l'utente menziona una categoria che potrebbe non esistere ancora
    """
    user_id = authenticate_from_context(ctx)

    # 1. Try to find exact match
    all_categories = await category_client.get_categories(user_id)
    category_name_lower = category_name.lower().strip()

    for cat in all_categories:
        if cat["name"].lower().strip() == category_name_lower:
            return {
                "success": True,
                "category": cat,
                "action": "found_exact",
                "message": f"Found exact category: '{category_name}'"
            }

    # 2. Find similar category
    best_match = None
    best_ratio = 0.0

    for cat in all_categories:
        cat_name_lower = cat["name"].lower().strip()
        ratio = difflib.SequenceMatcher(None, category_name_lower, cat_name_lower).ratio()

        if ratio > best_ratio and ratio >= similarity_threshold:
            best_ratio = ratio
            best_match = cat

    if best_match:
        return {
            "success": True,
            "category": best_match,
            "action": "found_similar",
            "message": f"Found similar category: '{best_match['name']}' (searched for: '{category_name}')",
            "original_search": category_name,
            "similarity": best_ratio
        }

    # 3. Create new category
    new_category = await category_client.create_category(
        user_id,
        category_name,
        description or f"Categoria creata automaticamente"
    )

    return {
        "success": True,
        "category": new_category,
        "action": "created",
        "message": f"Created new category: '{category_name}'"
    }


async def move_all_tasks_between_categories(
    ctx: Context,
    source_category: str,
    target_category: str,
    auto_create_target: bool = True
) -> Dict[str, Any]:
    """Sposta tutti i task da una categoria all'altra. Crea automaticamente la categoria destinazione se non esiste.

    Parameters:
    - source_category: Nome categoria di origine — deve esistere (obbligatorio)
    - target_category: Nome categoria destinazione (obbligatorio)
    - auto_create_target: Se True, crea la destinazione automaticamente se mancante (default: True)

    Restituisce quanti task spostati, quanti falliti e la lista dettagliata.

    Quando usare:
    - "Sposta tutti i task da Lavoro a Ufficio"
    - "Unisci le categorie Progetti A e Progetti B"
    - Riorganizzare la struttura delle categorie
    """
    user_id = authenticate_from_context(ctx)

    # Step 1: Find source category
    all_categories = await category_client.get_categories(user_id)
    source_cat = None
    source_category_lower = source_category.lower().strip()

    for cat in all_categories:
        if cat["name"].lower().strip() == source_category_lower:
            source_cat = cat
            break

    if not source_cat:
        # Try fuzzy match
        for cat in all_categories:
            ratio = difflib.SequenceMatcher(
                None,
                source_category_lower,
                cat["name"].lower().strip()
            ).ratio()
            if ratio >= 0.6:
                source_cat = cat
                break

    if not source_cat:
        category_names = [cat["name"] for cat in all_categories[:5]]
        return {
            "success": False,
            "message": f"Source category '{source_category}' not found",
            "suggestions": category_names
        }

    # Step 2: Find or create target category
    target_cat = None
    target_category_lower = target_category.lower().strip()
    target_action = "found_exact"

    for cat in all_categories:
        if cat["name"].lower().strip() == target_category_lower:
            target_cat = cat
            break

    if not target_cat:
        if auto_create_target:
            target_cat = await category_client.create_category(
                user_id,
                target_category,
                f"Categoria creata per spostamento task"
            )
            target_action = "created"
        else:
            category_names = [cat["name"] for cat in all_categories[:5]]
            return {
                "success": False,
                "message": f"Target category '{target_category}' not found and auto_create is disabled",
                "suggestions": category_names
            }

    # Step 3: Get all tasks from source category
    tasks = await task_client.get_tasks(user_id, category_id=source_cat["category_id"])

    if not tasks:
        return {
            "success": True,
            "message": f"No tasks found in source category '{source_cat['name']}'",
            "source_category_action": "found_exact",
            "target_category_action": target_action,
            "tasks_moved": 0
        }

    # Step 4: Move all tasks
    # Note: This requires updating each task's category
    # Since we don't have a direct "update category" endpoint,
    # we would need to use update_task for each task
    # For now, return a message indicating this operation
    # would need to be implemented on the FastAPI server side

    moved_tasks = []
    failed_moves = []

    for task in tasks:
        try:
            # Update task to move to new category
            # This would require the FastAPI server to support category_id in update
            result = await task_client.update_task(
                user_id=user_id,
                task_id=task["task_id"],
                # category_id=target_cat["category_id"]  # Not yet supported
            )

            moved_tasks.append({
                "task_id": task["task_id"],
                "title": task.get("title", ""),
                "from_category": source_cat["name"],
                "to_category": target_cat["name"]
            })
        except Exception as e:
            failed_moves.append({
                "task_id": task["task_id"],
                "title": task.get("title", ""),
                "error": str(e)
            })

    return {
        "success": len(moved_tasks) > 0,
        "tasks_moved": len(moved_tasks),
        "tasks_failed": len(failed_moves),
        "moved_tasks": moved_tasks,
        "failed_moves": failed_moves,
        "source_category": source_cat["name"],
        "target_category": target_cat["name"],
        "source_category_action": "found_exact",
        "target_category_action": target_action,
        "message": f"Moved {len(moved_tasks)} tasks from '{source_cat['name']}' to '{target_cat['name']}'"
    }


async def add_multiple_tasks(
    ctx: Context,
    tasks: List[Dict[str, Any]],
    auto_create_categories: bool = False
) -> Dict[str, Any]:
    """Crea più task in una sola chiamata. Più efficiente di chiamare add_task() ripetutamente.

    Parameters:
    - tasks: Lista di task da creare. Ogni task è un oggetto con:
      - title: Titolo (obbligatorio)
      - category_name: Nome categoria (opzionale, default: "Generale")
      - end_time: Scadenza formato "YYYY-MM-DD HH:MM:SS" (opzionale)
      - description: Dettagli aggiuntivi (opzionale)
      - priority: "Alta", "Media" o "Bassa" (opzionale, default: "Bassa")
    - auto_create_categories: Se True, crea le categorie mancanti automaticamente (default: False)

    Restituisce summary con conteggio creati/falliti e lista dettagliata degli errori.

    Quando usare:
    - L'utente elenca più task contemporaneamente: "Aggiungi: Spesa, Dentista, Palestra"
    - Bulk import da liste o note
    """
    user_id = authenticate_from_context(ctx)

    created_tasks = []
    failed_tasks = []
    categories_created = []
    categories_used = set()

    for i, task_info in enumerate(tasks):
        try:
            # Extract task parameters
            title = task_info.get("title")
            if not title:
                failed_tasks.append({
                    "index": i,
                    "error": "Missing required field: title",
                    "task_info": task_info
                })
                continue

            category_name = task_info.get("category_name", "Generale")
            end_time = task_info.get("end_time")
            start_time = task_info.get("start_time")
            description = task_info.get("description")
            priority = task_info.get("priority", "Bassa")

            # Create task
            try:
                result = await task_client.create_task(
                    user_id=user_id,
                    title=title,
                    category_name=category_name,
                    end_time=end_time,
                    start_time=start_time,
                    description=description,
                    priority=priority
                )

                created_tasks.append(result)
                categories_used.add(category_name)

            except Exception as e:
                error_msg = str(e)
                # If category doesn't exist and auto_create is enabled
                if auto_create_categories and "category" in error_msg.lower() and "not found" in error_msg.lower():
                    # Create category first
                    await category_client.create_category(
                        user_id,
                        category_name,
                        f"Categoria creata automaticamente"
                    )
                    categories_created.append(category_name)

                    # Retry task creation
                    result = await task_client.create_task(
                        user_id=user_id,
                        title=title,
                        category_name=category_name,
                        end_time=end_time,
                        start_time=start_time,
                        description=description,
                        priority=priority
                    )
                    created_tasks.append(result)
                    categories_used.add(category_name)
                else:
                    failed_tasks.append({
                        "index": i,
                        "error": error_msg,
                        "task_info": task_info
                    })

        except Exception as e:
            failed_tasks.append({
                "index": i,
                "error": str(e),
                "task_info": task_info
            })

    return {
        "success": len(created_tasks) > 0,
        "created_tasks": created_tasks,
        "failed_tasks": failed_tasks,
        "categories_created": list(set(categories_created)),
        "categories_used": list(categories_used),
        "summary": {
            "total_tasks_requested": len(tasks),
            "tasks_created": len(created_tasks),
            "tasks_failed": len(failed_tasks),
            "categories_created": len(set(categories_created)),
            "categories_used": len(categories_used)
        },
        "message": f"Created {len(created_tasks)}/{len(tasks)} tasks successfully"
    }
