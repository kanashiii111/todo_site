## 07.04.25 
Настроен CORS для фронта, написал сериализатор, создана модель todo, простенький юрл раутинг, скрыт ключ из settings.py

## 08.04.25
1. Добавлены 2 приложения: users - авторизация пользователей, userProfile - основные вкладки пользователя (пока что settings, tasks, calendar)
2. Добавлена авторизация пользователя с редиректом на profile/tasks/ после успешного входа
3. При неуспешном входе заново открывается страница со входом
4. /logout редиректит на /login 
5. Переход между profile/tasks, profile/calendar, profile/settings происходит через slug

## 09.04.2025
1. Убрал переход между profile/tasks, profile/calendar, profile/settings через slug, не понял как через него сделать кнопки с переходом на другие страницы
2. Добавленые кнопки на profile/tasks, profile/calendar, profile/settings, позволяющие переходить по соответствующим ссылкам
3. Добавлена модель Task
4. Изменен темплейт tasks.html, теперь на нем можно увидеть список задач (https://imgur.com/a/dkiGsdF)
5. При нажатии на кнопку выход происходит переадресация на страницу входа
6. Добавлена форма регистрации (https://imgur.com/a/XnswoHY)
7. Добавил сохранение профиля пользователя в БД
8. В профиле теперь будет указываться ник и выбранный при регистрации аватар (https://imgur.com/a/fQu4c2i)
9. Редирект на страницу входа если не авторизованный пользователь попытается зайти на /profile/tasks/ , /profile/calendar/ , /profile/settings/
10. Добавлена кнопка создания задачи, задачи привязываются к пользователю (https://imgur.com/a/WTdtRUe)
11. Добавил сериализатор для задач, добавил адрес для получения списка задач, обновил API_DOCS

## 14.04.2025
1. Чуть переписаны html файлы страниц, добавлены static файлы.
2. Добавлен пустой календарь.

## 15.04.2025
1. При создании задачи теперь можно выбрать срок ее выполнения
2. В profile/tasks задачи теперь можно фильтровать по тегу, сроку выполнения и приоритету
3. Добавлен редирект на /login/ если заходить на глав. страницу

## 17.04.2025

1. При нажатии на кнопку задачи появляется всплывающее окно с информацией о ней.
2. Добавлено удаление задачи.
3. Задачи (пока только название) отображаются на календаре в днях, где заканчивается их срок выполнения.
4. Срок выполнения задачи в формате с точностью до минут.
5. Сломал к чертям фильтр, пока пытался пофиксить сгорела жопа и удалил его к хренам :)

## 21.04.2025

1. Новый фильтр (рабочий!!!)
2. Возможность редактирования задачи

## 22.04.2025

1. Добавил плашку с информацией о пользователе над панелью навигации на страницах Задач и Календаря
2. При нажатии на эту плашку перекидывает на страницу с профилем
3. Если у пользователя отсутствует аватар, будет показываться дефолтный
4. Убрал поле приоритетности у задачи (в дизайне он отсутствует)
5. Добавил поле status в модели пользователя, возможность его изменения пока не предусмотрел, хз где это должно быть

## 29.04.2025

1. Добавил возможность создания, просмотра и редактирования задачи в календаре
2. Добавил поле опыта к модели пользователя

## 30.04.2025

1. Добавил уведомления через ТГ-бота.
2. При создании задачи можно указать определенное время для уведомлений.

## 01.05.2025

1. Добавил редактирование уведомлений
2. Теперь в профиле есть плашка с возможностью редактирования никнейма и аватара пользователя
3. Добавил поку пустую кнопку настроек в профиль

## 03.05.2025

1. Добавил поле почты в регистрацию
2. Добавил дефолтный аватар через Gravatar
3. Добавил систему опыта и статусов
4. За выполнение задачи пользователь награждается опытов в зависимости от типа задачи (лаба, экзамен)

## 04.05.2025

1. Пофиксил неправильное отображение задач из-за временных зон
2. Пофиксил поиск по названию и описанию
3. Поиск теперь динамический
4. Пофиксил неправильную отправку уведомлений тг-бота из-за временных зон

## 05.05.2025

1. Все предыдущие изменения можно удалять, нужно все переписывать чтобы работа была через чистый апи
2. Замерджил ПР от https://github.com/MrSedan (эндпоинты для авторизации, проверки авторизации)
3. Добавил эндпоинты для регистрации, задач (просмотр всех, создание, удаление, завершение), календаря (просмотр), настроек (просмотр) (Скорее всего что-то да не будет работать, требуется куча мелких исправлений)

## 06.05.2025

1. Исправил недочеты эндпоинтов
2. Проверил каждый эндпоинт, не прям досконально но нужные ответы они посылают.
3. Разделил работу с задачами и настройками на разные эндпоинты
4. К модели задачи добавил поле "Просрочено", написал функцию для расчета, просрочен срок выполнения задачи или нет
5. Создал воркспейс в постмане и разделил все реквесты по страницам, к каждой коллекции написал документацию по использованию

## 07.05.2025

1. Добавил модель тега, написал к ней все необходимые эндпоинты
2. Написал доки к апи тега

## 11.05.2025

1. Переписал теги