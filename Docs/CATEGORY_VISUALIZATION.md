# Category Visualization System

## Overview

Il sistema di visualizzazione delle categorie segue lo stesso pattern dei task, con tools separati per uso interno vs visualizzazione utente.

## Architettura

### 1. **Tools per uso interno** (NO visualizzazione)
- `get_my_categories()` - Ritorna JSON semplice per lookup/validazione
- `search_categories()` - Trova categorie per nome
- `update_category()` - Modifica categoria esistente

### 2. **Tools per visualizzazione** (SI visualizzazione)
- `show_categories_to_user()` - Mostra categorie formattate con UI ricca

### 3. **Tools per creazioni** (Mostrano bottone "Modifica")
- `create_category()` - Ritorna `type: "category_created"` + bottone edit

---

## Formattazione UI

### Formatter: `format_categories_for_ui()`

Trasforma dati grezzi in struttura ottimizzata per React Native:

```python
from src.formatters import format_categories_for_ui

# Input: liste di categorie + conteggi task
categories = [{"category_id": 1, "name": "Lavoro", ...}]
task_counts = {1: 12, 2: 5}  # category_id -> task count

# Output: JSON formattato per UI
formatted = format_categories_for_ui(categories, task_counts)
```

### Output Structure

```json
{
  "type": "category_list",
  "version": "1.0",
  "categories": [
    {
      "id": 1,
      "name": "Lavoro",
      "description": "Task di lavoro",
      "color": "#3B82F6",
      "icon": "briefcase",
      "taskCount": 12,
      "userId": 123,
      "actions": {
        "edit": {
          "label": "✏️ Modifica",
          "enabled": true
        },
        "delete": {
          "label": "🗑️ Elimina",
          "enabled": true,
          "requiresConfirmation": true
        },
        "viewTasks": {
          "label": "👁️ Vedi task",
          "enabled": true
        }
      }
    }
  ],
  "summary": {
    "total": 5,
    "categories_with_tasks": 3,
    "total_tasks": 25
  },
  "voice_summary": "Hai 5 categorie, di cui 3 con task attivi. Totale 25 task.",
  "ui_hints": {
    "display_mode": "grid",
    "enable_swipe_actions": true,
    "enable_pull_to_refresh": true,
    "enable_search": true,
    "default_sort": "name"
  }
}
```

### Features della formattazione:

1. **Colori**: Assegnati automaticamente usando `get_category_color()`
   - Colori predefiniti per categorie comuni (Lavoro, Personale, Studio, etc.)
   - Colori hash-based per categorie custom

2. **Icone**: Mapping automatico usando `get_category_icon()`
   - Icone predefinite per categorie comuni
   - Default: "folder" per categorie sconosciute

3. **Task Count**: Numero di task per categoria

4. **Actions**: Bottoni configurabili con stato enabled/disabled

5. **Summary Statistics**: Totale categorie, categorie con task, totale task

6. **Voice Summary**: Testo ottimizzato per Text-to-Speech

7. **UI Hints**: Suggerimenti per la visualizzazione mobile

---

## Come funziona nell'app React Native

### Gestione automatica basata su `type`

```typescript
function handleToolResponse(response: any) {
  switch (response.type) {
    case "category_created":
      // Mostra notifica + bottone "Modifica categoria"
      Toast.show(response.message);
      showEditButton(
        `Modifica "${response.category.name}"`,
        () => navigation.navigate("CategoryEditor", {
          categoryId: response.category.category_id
        })
      );
      break;

    case "category_list":
      // Renderizza lista/griglia formattata
      renderCategoryGrid(response.categories);
      break;
  }
}
```

### Esempio di rendering

```typescript
function renderCategoryGrid(categories: Category[]) {
  return (
    <Grid>
      {categories.map(cat => (
        <CategoryCard
          key={cat.id}
          name={cat.name}
          color={cat.color}
          icon={cat.icon}
          taskCount={cat.taskCount}
          onEdit={() => editCategory(cat.id)}
          onDelete={() => deleteCategory(cat.id)}
          onViewTasks={() => viewCategoryTasks(cat.id)}
        />
      ))}
    </Grid>
  );
}
```

---

## Esempi di utilizzo

### Scenario 1: Utente vuole vedere le categorie

```
User: "Mostrami le mie categorie"

AI:
1. Chiama show_categories_to_user()
2. Riceve risposta con type: "category_list"

App:
1. Vede type: "category_list"
2. Renderizza griglia con categorie formattate
3. Mostra colori, icone, conteggi task
4. Abilita swipe actions per edit/delete
```

### Scenario 2: AI cerca categoria per creare task

```
User: "Crea task Riunione in categoria Lavoro"

AI:
1. Chiama get_my_categories() (uso interno)
2. Trova category_id=5 per "Lavoro"
3. Chiama add_task(category_id=5)

App:
1. get_my_categories() NON ha type speciale
2. NON mostra nulla (è uso interno)
3. Solo add_task mostra notifica "Task creato"
```

### Scenario 3: Utente crea nuova categoria

```
User: "Crea categoria Progetti"

AI:
1. Chiama create_category(name="Progetti")

Response:
{
  "success": true,
  "type": "category_created",
  "message": "✅ Categoria 'Progetti' creata con successo",
  "category": {
    "category_id": 10,
    "name": "Progetti",
    "description": null
  }
}

App:
1. Vede type: "category_created"
2. Mostra notifica di successo
3. Mostra bottone "Modifica Progetti"
4. Utente può cliccare per modificare subito la categoria
```

---

## Pattern di output standardizzato

### Creazione (con bottone edit)

```json
{
  "success": true,
  "type": "category_created",
  "message": "✅ Categoria creata",
  "category": {
    "category_id": 10,
    "name": "Progetti",
    ...
  }
}
```

### Visualizzazione (lista formattata)

```json
{
  "type": "category_list",
  "version": "1.0",
  "categories": [...],
  "summary": {...},
  "ui_hints": {...}
}
```

### Uso interno (JSON semplice)

```json
{
  "categories": [...],
  "total": 5
}
```

---

## Benefits del sistema

1. ✅ **Separazione chiara**: Tools interni vs visualizzazione
2. ✅ **Zero ambiguità**: L'app sa sempre cosa mostrare tramite `type`
3. ✅ **Consistency**: Stesso pattern per task e categorie
4. ✅ **Estendibile**: Facile aggiungere nuovi tipi (note, stats, etc.)
5. ✅ **Performance**: Formattazione solo quando necessario
6. ✅ **UX ottimale**: Bottone "Modifica" automatico dopo creazione

---

## File modificati

- `src/formatters/tasks.py` - Aggiunto `format_categories_for_ui()` e `get_category_icon()`
- `src/formatters/__init__.py` - Esportato nuovo formatter
- `src/tools/categories.py` - Aggiunto `show_categories_to_user()` + aggiornato `create_category()` e `get_my_categories()`
- `src/core/server.py` - Registrato nuovo tool
