"""MCP meta-tools for advanced operations."""

from typing import Dict, Any, List
from fastmcp import Context
from src.auth import authenticate_from_context
from src.client import category_client, task_client



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
