# ToDo API Documentation (Django REST Framework)

## Получение списка задач

**GET** `api/tasks/`

**Ответ**
```json
[
    {
        "title": "Лаба",
        "description": "лаба по проге",
        "isCompleted": false,
        "priority": 8,
        "tag": "lab"
    },
    {
        "title": "test1",
        "description": "test1",
        "isCompleted": false,
        "priority": 1,
        "tag": "test"
    }
]
```

