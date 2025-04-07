# ToDo API Documentation (Django REST Framework)

!!!! Дополнить доки (получение конкретной задачи, обновление задачи)

## Базовый URL (изменить)
Все запросы отправляются на:  
`http://your-server-address/api/tasks/` 

---
## 1. Получить список всех задач
**Endpoint:** `GET /api/tasks/`

### Пример запроса:
```bash
curl -X GET http://localhost:8000/api/tasks/
```

### Пример ответа:
```json
[
    {
        "id": 1,
        "name": "лаба",
        "isCompleted": false,
    },
]

```
## 2. Создать новую задачу
**Endpoint:** `POST /api/todos/`

### Параметры запроса:

Поле	    Тип	        Обязательное	Описание
name	    string	    Да	            Название задачи
isCompleted	boolean	    Нет	            Статус выполнения

### Пример запроса:
```bash
curl -X POST http://localhost:8000/api/todos/ \
-H "Content-Type: application/json" \
-d '{"name": "Новая задача"}'
```

### Пример ответа:
```json
{
    "id": 3,
    "name": "Новая задача",
    "isCompleted": false,
}
```
## 3. Удалить задачу
**Endpoint:** `DELETE /api/todos/{id}/`

### Параметры URL(Запроса)

Параметр  Тип	 Описание
id	      int	 ID задачи

### Пример запроса:
```bash
curl -X DELETE http://localhost:8000/api/todos/3/
```

### Пример ответа (204 No Content (Успешное удаление)):

(Пустой тело ответа)

### Пример ответа (400 Not Found (Задача не существует)):

```json
{
    "detail": "Не найдено."
}
```
