"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

export type Locale = "ru" | "en" | "kk";
type Variables = Record<string, string | number>;

const translations: Record<Exclude<Locale, "ru">, Record<string, string>> = {
  en: {
    "Язык": "Language",
    "Подключения Growly: автопостинг в ваши соцсети.": "Growly connections: auto-posting to your social networks.",
    "Instagram автопостинг": "Instagram auto-posting",
    "Ожидает подключения": "Awaiting connection",
    "Growly может автоматически публиковать посты в ваш Instagram. Подключение выполняется безопасно через официальный вход Instagram/Meta. Мы никогда не просим и не храним ваш пароль.": "Growly can automatically publish posts to your Instagram. The connection is made securely through the official Instagram/Meta login. We never ask for or store your password.",
    "Подключение выполняется вручную администратором Growly на MVP-этапе. Вы не передаёте пароль. Вы сами подтверждаете доступ через официальный экран Instagram/Meta.": "On the MVP stage the connection is done manually by a Growly admin. You do not share your password. You confirm access yourself via the official Instagram/Meta screen.",
    "Instagram не подключен": "Instagram is not connected",
    "Отправьте заявку, и мы поможем подключить ваш Instagram к автопостингу. Подключение проходит через официальный OAuth, без передачи пароля.": "Send a request and we will help connect your Instagram to auto-posting. The connection goes through official OAuth, without sharing a password.",
    "Instagram username": "Instagram username",
    "Отправить заявку на подключение": "Send a connection request",
    "Заявка на подключение отправлена": "Connection request sent",
    "Администратор Growly свяжется с вами и поможет безопасно подключить Instagram через OAuth. Не отправляйте пароль от Instagram.": "A Growly admin will contact you and help securely connect Instagram via OAuth. Do not send your Instagram password.",
    "Обновить статус": "Refresh status",
    "Отменить заявку": "Cancel request",
    "Отменяем": "Cancelling",
    "Instagram подключен": "Instagram connected",
    "Growly может публиковать посты в этот аккаунт через Blotato.": "Growly can publish posts to this account via Blotato.",
    "ID аккаунта": "Account ID",
    "Подключён": "Connected on",
    "Не удалось подключить Instagram": "Could not connect Instagram",
    "Подключение не удалось. Отправьте заявку повторно.": "The connection failed. Please send the request again.",
    "Повторить заявку": "Resend request",
    "Укажите ваш Instagram username.": "Enter your Instagram username.",
    "Заявка отправлена.": "Request sent.",
    "Заявка отменена.": "Request cancelled.",
    "Instagram отключён.": "Instagram disconnected.",
    "Не удалось загрузить интеграции. Попробуйте ещё раз.": "Could not load integrations. Please try again.",
    "Доступ ограничен": "Access restricted",
    "Доступ только для администратора Growly.": "Access is for the Growly admin only.",
    "Blotato и подключения": "Blotato and connections",
    "Подключение клиентов к автопостингу выполняется вручную через официальный OAuth.": "Connecting clients to auto-posting is done manually via official OAuth.",
    "Как подключать клиента безопасно": "How to connect a client safely",
    "Никогда не просите пароль от Instagram.": "Never ask for the Instagram password.",
    "Подключение должно проходить через официальный OAuth.": "The connection must go through official OAuth.",
    "Клиент сам входит в Instagram/Meta на своём устройстве.": "The client logs in to Instagram/Meta on their own device.",
    "После подключения нажмите «Обновить аккаунты» в Growly.": "After connecting, click 'Refresh accounts' in Growly.",
    "Найдите новый accountId из Blotato и свяжите его с заявкой клиента.": "Find the new accountId from Blotato and link it to the client request.",
    "Не подключайте аккаунт клиента, если вы не уверены, что клиент сам дал разрешение через OAuth.": "Do not connect a client account unless you are sure the client granted permission via OAuth themselves.",
    "Статус Blotato": "Blotato status",
    "настроен": "configured",
    "не настроен": "not configured",
    "Последняя проверка": "Last checked",
    "Blotato не отвечает": "Blotato is not responding",
    "Заявки на подключение": "Connection requests",
    "Заявок пока нет.": "No requests yet.",
    "Пользователь": "User",
    "В работу": "Start working",
    "Связать аккаунт": "Link account",
    "Отметить ошибку": "Mark as failed",
    "Отменить": "Cancel",
    "Статус заявки обновлён.": "Request status updated.",
    "Сначала выберите аккаунт Blotato.": "Select a Blotato account first.",
    "Аккаунт связан с заявкой.": "Account linked to the request.",
    "Аккаунты из Blotato": "Accounts from Blotato",
    "Нажмите «Обновить аккаунты», чтобы получить список из Blotato.": "Click 'Refresh accounts' to fetch the list from Blotato.",
    "Платформа": "Platform",
    "Связан с": "Linked to",
    "Instagram автопостинг не подключен. Отправьте заявку на подключение в Интеграциях.": "Instagram auto-posting is not connected. Send a connection request in Integrations.",
    "Заявка на подключение Instagram уже отправлена. После подключения вы сможете публиковать посты автоматически.": "An Instagram connection request has already been sent. Once connected, you will be able to publish posts automatically.",
    "Instagram подключен. Пост можно опубликовать или запланировать.": "Instagram is connected. You can publish or schedule the post.",
    "Заявка уже отправлена": "Request already sent",
    "Администратор подключит ваш Instagram через безопасный OAuth-flow. После подключения публикация станет доступна.": "The admin will connect your Instagram via a secure OAuth flow. Publishing will become available after connection.",
    "Чтобы Growly мог автоматически публиковать посты, отправьте заявку на подключение Instagram. Пароль не нужен: подключение проходит через официальный OAuth.": "So Growly can publish posts automatically, send an Instagram connection request. No password needed: the connection goes through official OAuth.",
    "Instagram через Blotato": "Instagram via Blotato",
    "Instagram подключён": "Instagram connected",
    "Выберите аккаунт": "Choose an account",
    "Подключите Blotato для автопостинга": "Connect Blotato for auto-posting",
    "Growly будет отправлять готовые посты в Blotato, а Blotato опубликует их в Instagram.":
      "Growly sends ready-made posts to Blotato, and Blotato publishes them to Instagram.",
    "API-ключ Blotato": "Blotato API key",
    "Вставьте BLOTATO_API_KEY": "Paste your BLOTATO_API_KEY",
    "Ключ хранится только на сервере в зашифрованном виде и никогда не возвращается в браузер.":
      "The key is stored encrypted on the server only and is never returned to the browser.",
    "Сохранить API ключ": "Save API key",
    "Blotato подключён. Выберите Instagram аккаунт для автопостинга.":
      "Blotato connected. Choose an Instagram account for auto-posting.",
    "Instagram аккаунты не найдены. Сначала подключите Instagram в кабинете Blotato, затем вернитесь сюда и нажмите «Обновить аккаунты».":
      "No Instagram accounts found. Connect Instagram in your Blotato dashboard first, then come back and click “Refresh accounts”.",
    "Instagram аккаунт": "Instagram account",
    "Сохранить аккаунт": "Save account",
    "Открыть кабинет Blotato": "Open Blotato dashboard",
    "Аккаунт": "Account",
    "Аккаунтов в Blotato": "Accounts in Blotato",
    "Сменить аккаунт": "Change account",
    "Отключить": "Disconnect",
    "Отключаем": "Disconnecting",
    "Другие соцсети": "Other social networks",
    "Threads, TikTok, YouTube, Facebook, LinkedIn и X публикуются через Blotato.":
      "Threads, TikTok, YouTube, Facebook, LinkedIn and X publish via Blotato.",
    "Введите корректный API-ключ Blotato.": "Enter a valid Blotato API key.",
    "Blotato подключён. Найдено аккаунтов: {count}.":
      "Blotato connected. Accounts found: {count}.",
    "Выберите Instagram аккаунт из списка.":
      "Choose an Instagram account from the list.",
    "Instagram аккаунт сохранён.": "Instagram account saved.",
    "Выберите другой Instagram аккаунт.": "Choose a different Instagram account.",
    "Blotato отключён.": "Blotato disconnected.",
    "Опубликовать": "Publish",
    "Создать черновик": "Create draft",
    "Открыть черновик": "Open draft",
    "Посмотреть": "View",
    "Закрыть": "Close",
    "Запланирован": "Scheduled",
    "Выберите тему из плана и нажмите «Создать черновик», «Опубликовать» или «Запланировать». Для автопостинга в Instagram сначала подключите Blotato в разделе «Интеграции».":
      "Pick a topic from the plan and click “Create draft”, “Publish” or “Schedule”. To auto-post to Instagram, connect Blotato in “Integrations” first.",
    "Instagram не подключён": "Instagram not connected",
    "Чтобы публиковать посты автоматически, подключите Instagram через Blotato.":
      "To publish posts automatically, connect Instagram via Blotato.",
    "Перейти в Интеграции": "Go to Integrations",
    "Ссылка на изображение или видео": "Image or video URL",
    "Медиа": "Media",
    "Фото, видео или карусель для публикации":
      "Photo, video, or carousel for the post",
    "Загрузить фото или видео": "Upload photo or video",
    "Загружаем медиа": "Uploading media",
    "Удалить медиа": "Remove media",
    "Генерация в Blotato": "Generate in Blotato",
    "Карусель изображений": "Image carousel",
    "AI-видео": "AI video",
    "AI-изображение": "AI image",
    "Что должно быть на фото или видео":
      "Describe the photo or video",
    "Сгенерировать": "Generate",
    "Генерируем": "Generating",
    "Или вставьте публичную ссылку": "Or paste a public URL",
    "В очереди": "Queued",
    "Подготовка сценария": "Preparing script",
    "Генерация медиа": "Generating media",
    "Экспорт медиа": "Exporting media",
    "Медиа готово и добавлено к публикации.":
      "Media is ready and attached to the post.",
    "Можно добавить не более 10 файлов.":
      "You can attach up to 10 files.",
    "Поддерживаются изображения JPG, PNG, WEBP, GIF и видео MP4, MOV, WEBM.":
      "Supported formats: JPG, PNG, WEBP, GIF, MP4, MOV, and WEBM.",
    "Не удалось загрузить файл в Blotato.":
      "Could not upload the file to Blotato.",
    "Blotato не вернул ID созданного медиа.":
      "Blotato did not return a media ID.",
    "Blotato не вернул созданное медиа.":
      "Blotato did not return the generated media.",
    "Blotato не удалось сгенерировать медиа.":
      "Blotato could not generate the media.",
    "Генерация заняла слишком много времени. Проверьте результат в Blotato.":
      "Generation is taking too long. Check the result in Blotato.",
    "Для публикации в Instagram добавьте изображение или видео.":
      "To publish to Instagram, add an image or video.",
    "Instagram выбран, но автопостинг ещё не подключён. Подключите Instagram через Blotato в Интеграциях.":
      "Instagram is selected, but auto-posting is not connected yet. Connect Instagram via Blotato in Integrations.",
    "Подключить Instagram": "Connect Instagram",
    "Сохраните API-ключ Blotato на странице «Интеграции»":
      "Save the Blotato API key on the Integrations page",
    "Рабочее пространство": "Workspace",
    "Основная навигация": "Main navigation",
    "Обзор": "Overview",
    "Чат": "Chat",
    "Анализ рынка": "Market analysis",
    "Отчёты": "Reports",
    "Контент-план": "Content plan",
    "Черновики": "Drafts",
    "Источники": "Sources",
    "Настройки": "Settings",
    "Выйти": "Sign out",
    "Открыть меню": "Open menu",
    "Закрыть меню": "Close menu",
    "Возможности": "Capabilities",
    "Как работает": "How it works",
    "Для кого": "Who it is for",
    "Открыть Growly": "Open Growly",
    "Маркетинговое рабочее пространство": "Marketing workspace",
    "От рыночных данных до готового контента.":
      "From market evidence to publish-ready content.",
    "Начать работу": "Get started",
    "Посмотреть возможности": "Explore capabilities",
    "Рабочая область": "Workspace",
    "Сегодня": "Today",
    "Система готова": "System ready",
    "Следующее действие": "Next action",
    "Запустить анализ рынка": "Run market analysis",
    "Новый анализ": "New analysis",
    "Последний отчёт": "Latest report",
    "Ожидает данных": "Waiting for data",
    "Появится после первого анализа": "Appears after the first analysis",
    "Не создан": "Not created",
    "Формируется на основе источников": "Built from saved sources",
    "Задача": "Task",
    "Статус": "Status",
    "Данные": "Data",
    "Не запускался": "Not started",
    "Нет": "No",
    "Синхронизация Notion": "Notion sync",
    "По настройке": "Configured",
    "Сервер": "Server",
    "Что делает Growly": "What Growly does",
    "Один процесс вместо набора разрозненных инструментов.":
      "One workflow instead of disconnected tools.",
    "Рабочий процесс": "Workflow",
    "Каждый вывод остаётся связан с источником.":
      "Every conclusion stays connected to evidence.",
    "Укажите нишу и регион": "Enter the niche and region",
    "Проверьте собранные источники": "Review collected sources",
    "Получите конкурентный отчёт": "Get a competitor report",
    "Сформируйте контент-план": "Build a content plan",
    "Подготовьте и согласуйте посты": "Prepare and approve posts",
    "Малый бизнес": "Small business",
    "Маркетолог": "Marketer",
    "Агентство": "Agency",
    "Telegram и Instagram": "Telegram and Instagram",
    "Начните с первого анализа рынка.": "Start with your first market analysis.",
    "Открыть рабочую область": "Open workspace",
    "Контакты": "Contacts",
    "Рабочее пространство Growly": "Growly workspace",
    "Рынок, отчёты и контент в одном процессе.":
      "Market research, reports, and content in one workflow.",
    "Вернуться на главную": "Back to home",
    "Вход": "Sign in",
    "Рабочая почта": "Work email",
    "Пароль": "Password",
    "Проверяем доступ": "Checking access",
    "Войти": "Sign in",
    "Открыть локальный режим": "Open local mode",
    "Вход временно недоступен": "Sign in is temporarily unavailable",
    "Черновики на согласовании": "Drafts awaiting approval",
    "Открыть список": "Open list",
    "Активные источники": "Active sources",
    "Управлять источниками": "Manage sources",
    "Опубликованные материалы": "Published items",
    "По данным Growly": "Based on Growly data",
    "Последняя синхронизация Notion": "Last Notion sync",
    "Настроен": "Configured",
    "Не настроен": "Not configured",
    "Последние результаты": "Latest results",
    "Что уже готово": "What is ready",
    "Все отчёты": "All reports",
    "Конкурентный отчёт": "Competitor report",
    "Быстрые действия": "Quick actions",
    "Продолжить работу": "Continue working",
    "Новый анализ рынка": "New market analysis",
    "Создать контент-план": "Create content plan",
    "Подготовить пост": "Prepare a post",
    "Согласование": "Approval",
    "Черновики в работе": "Drafts in progress",
    "Все черновики": "All drafts",
    "Канал не указан": "Channel not specified",
    "Исследование": "Research",
    "Параметры анализа": "Analysis parameters",
    "Ниша или продукт": "Niche or product",
    "Регион и язык": "Region and language",
    "Известные конкуренты": "Known competitors",
    "Можно оставить пустым": "Optional",
    "Анализ выполняется": "Analysis in progress",
    "Запустить анализ": "Run analysis",
    "Ищу источники": "Searching for sources",
    "Сохраняю данные": "Saving data",
    "Анализирую": "Analyzing",
    "Формирую отчёт": "Building report",
    "Синхронизирую с Notion": "Syncing with Notion",
    "Не удалось завершить анализ рынка.":
      "Could not complete the market analysis.",
    "Анализ занимает больше времени, чем ожидалось.":
      "The analysis is taking longer than expected.",
    "Сервер не успел запустить анализ. Повторите попытку.":
      "The server could not start the analysis in time. Try again.",
    "Открыть отчёт": "Open report",
    "Открыть отчёты": "Open reports",
    "Отчёт создан, но ссылка на него не получена. Откройте раздел Отчёты.":
      "Report was created, but its link was not returned. Open Reports.",
    "База знаний": "Knowledge base",
    "Поиск по отчётам": "Search reports",
    "Найти отчёт": "Find a report",
    "Всего: {count}": "Total: {count}",
    "{count} источников": "{count} sources",
    "Краткий вывод не указан.": "No summary provided.",
    "Пока нет отчётов": "No reports yet",
    "Планирование": "Planning",
    "Новый план": "New plan",
    "Цель недели": "Weekly goal",
    "Формируем план": "Building plan",
    "Создать план": "Create plan",
    "Создано элементов: {count}.": "Items created: {count}.",
    "Не удалось создать контент-план.": "Could not create the content plan.",
    "Причина: {reason}": "Reason: {reason}",
    "Созданный план на основе реальных отчётов Growly.":
      "A generated plan based on real Growly reports.",
    "Вернуться к планам": "Back to plans",
    "Черновик «{name}» создан.": "Draft “{name}” created.",
    "Календарь": "Calendar",
    "Запланированные материалы": "Scheduled content",
    "Контент-план ещё не создан": "Content plan has not been created",
    "Дата": "Date",
    "Канал": "Channel",
    "Тема": "Topic",
    "Цель": "Goal",
    "Формат": "Format",
    "Призыв": "Call to action",
    "Источник идеи": "Idea source",
    "Не указан": "Not specified",
    "Без темы": "Untitled",
    "Не указана": "Not specified",
    "Создаём": "Creating",
    "Создан": "Created",
    "Черновик": "Draft",
    "Фильтр статуса": "Status filter",
    "Все статусы": "All statuses",
    "На согласовании": "Awaiting approval",
    "Согласованные": "Approved",
    "Отклонённые": "Rejected",
    "Опубликованные": "Published",
    "Показано: {count}": "Shown: {count}",
    "версия {version}": "version {version}",
    "Сохранён в Notion": "Saved to Notion",
    "Не сохранён в Notion": "Not saved to Notion",
    "Согласовать": "Approve",
    "Новая версия": "New version",
    "В Notion": "To Notion",
    "Отклонить": "Reject",
    "Черновиков пока нет": "No drafts yet",
    "Создать пост": "Create post",
    "Проверить активные": "Check active sources",
    "Найти источники": "Discover sources",
    "Добавить вручную": "Add manually",
    "Способ добавления": "Add method",
    "Поиск": "Search",
    "Вручную": "Manual",
    "Ниша": "Niche",
    "Регион": "Region",
    "Платформы через запятую": "Platforms, comma-separated",
    "Название": "Name",
    "Выполняется": "In progress",
    "Найти кандидатов": "Find candidates",
    "Добавить источник": "Add source",
    "Реестр": "Registry",
    "Сохранённые источники": "Saved sources",
    "Источников пока нет": "No sources yet",
    "URL не указан": "URL not specified",
    "Командный интерфейс": "Command interface",
    "Действия": "Actions",
    "Конкуренты": "Competitors",
    "Сохранить в Notion": "Save to Notion",
    "Сообщение": "Message",
    "Отправить": "Send",
    "Ошибка": "Error",
    "Задача выполняется на сервере.": "The task is running on the server.",
    "Длительные операции могут занять несколько минут.":
      "Long-running operations can take several minutes.",
    "Конфигурация": "Configuration",
    "Профиль бизнеса": "Business profile",
    "Тон бренда": "Brand tone",
    "Telegram-канал": "Telegram channel",
    "Корневая страница Notion": "Notion root page",
    "Настройки сохранены.": "Settings saved.",
    "Сохраняем": "Saving",
    "Сохранить": "Save",
    "Режим рабочего пространства": "Workspace mode",
    "Оплата": "Billing",
    "Тариф и оплата": "Plan and billing",
    "План, оплата и доступ к платёжному кабинету Growly.":
      "Plan, billing, and Growly billing portal access.",
    "Открыть оплату": "Open billing",
    "Управляйте тарифом Growly, статусом подписки и доступом к платёжному кабинету.":
      "Manage your Growly plan, subscription status, and billing portal access.",
    "Посмотреть тарифы": "View plans",
    "Не удалось загрузить данные по оплате.": "Could not load billing data.",
    "Платёжный кабинет пока не настроен.":
      "The billing portal is not configured yet.",
    "Оплата пока не настроена.": "Payment is not configured yet.",
    "Текущий тариф": "Current plan",
    "Следующее списание": "Next billing date",
    "Нет даты списания": "No billing date",
    "Отмена в конце периода": "Cancel at period end",
    "Выбрать тариф": "Choose plan",
    "Изменить тариф": "Change plan",
    "Управлять оплатой": "Manage billing",
    "Тарифы": "Plans",
    "Выберите размер рабочей области": "Choose the workspace size",
    "Предпросмотр": "Preview",
    "Имя пользователя Instagram": "Instagram username",
    "Мобильный режим": "Mobile mode",
    "Growly для Telegram": "Growly for Telegram",
    "Проверка Telegram-пользователя": "Telegram user verification",
    "Загружаем отчёт": "Loading report",
    "Сформировано Growly": "Generated by Growly",
    "Синхронизирован": "Synced",
    "Не сохранён": "Not saved",
    "Открыть Notion": "Open Notion",
    "Вернуться к отчётам": "Back to reports",
    "Главный вывод": "Key finding",
    "Сравнение конкурентов": "Competitor comparison",
    "Конкурент": "Competitor",
    "Предложение": "Offer",
    "Цена / ценность": "Price / value",
    "Сильная сторона": "Strength",
    "Слабая сторона": "Weakness",
    "Возможность": "Opportunity",
    "Не подтверждено": "Not verified",
    "Требуется больше данных": "More data required",
    "Динамика публикаций": "Publication performance",
    "Повторяющиеся предложения": "Recurring offers",
    "Призывы к действию": "Calls to action",
    "Пробелы в контенте": "Content gaps",
    "Боли аудитории": "Audience pain points",
    "Рекомендуемое позиционирование": "Recommended positioning",
    "Действия на неделю": "Actions for the week",
    "Идеи контента": "Content ideas",
    "Риски и ограничения": "Risks and limitations",
    "Полный текст": "Full text",
    "Загрузка данных": "Loading data",
    "Не удалось загрузить данные": "Could not load data",
    "Повторить": "Retry",
    "Неизвестная ошибка": "Unknown error",
    "Нет данных": "No data",
    "Не синхронизировалось": "Not synced",
    "Сервис временно недоступен.": "The service is temporarily unavailable.",
    "Не удалось создать черновик. Сервис временно недоступен.":
      "Could not create the draft. The service is temporarily unavailable.",
    "Задачу не удалось выполнить. Сервис временно недоступен.":
      "The task could not be completed. The service is temporarily unavailable.",
    "Генерация временно недоступна: лимит AI-сервиса исчерпан. Попробуйте позже.":
      "Generation is temporarily unavailable: the AI service limit has been reached. Please try again later.",
    "Генерация временно недоступна. Попробуйте позже.":
      "Generation is temporarily unavailable. Please try again later.",
    "Генерация заняла слишком много времени. Попробуйте ещё раз.":
      "Generation took too long. Please try again.",
    "Активен": "Active",
    "Ожидает анализа": "Awaiting analysis",
    "Согласован": "Approved",
    "Завершён": "Completed",
    "Отключён": "Disabled",
    "Черновик создан": "Draft created",
    "Готов": "Ready",
    "Требует проверки": "Needs review",
    "Growly сначала сохраняет найденные материалы, затем анализирует их и только после этого формирует план и черновики.":
      "Growly saves discovered material first, analyzes it, and only then creates plans and drafts.",
    "Growly сначала сохраняет публичные источники, затем формирует выводы и отчёт.":
      "Growly saves public sources first, then produces findings and a report.",
    "Growly собирает публичные источники, готовит отчёты и помогает вести контент-процесс без разрыва между аналитикой и публикацией.":
      "Growly collects public sources, prepares reports, and keeps research, planning, and publishing in one workflow.",
    "Supabase Auth не настроен. В локальном режиме можно открыть интерфейс без авторизации.":
      "Supabase Auth is not configured. Local mode can be opened without authentication.",
    "Supabase Auth не настроен. Вход в рабочую область временно недоступен.":
      "Supabase Auth is not configured. Workspace sign-in is temporarily unavailable.",
    "Tavily ищет только публично доступные страницы.":
      "Tavily searches only publicly available pages.",
    "Анализ ещё не запускался. Укажите нишу и регион.":
      "Analysis has not run yet. Enter a niche and region.",
    "Аналитика, контент и согласование в одной системе.":
      "Research, content, and approvals in one system.",
    "Быстрый доступ к основным действиям Growly без дублирования бизнес-логики.":
      "Quick access to Growly actions without duplicating business logic.",
    "Версии материалов, статусы согласования и сохранение в Notion.":
      "Content versions, approval statuses, and Notion sync.",
    "Вести исследование, согласование и отчётность по единой структуре.":
      "Run research, approvals, and reporting in one structure.",
    "Войдите, чтобы продолжить работу с источниками, планами и согласованием материалов.":
      "Sign in to continue working with sources, plans, and approvals.",
    "Выберите действие слева и опишите задачу. Growly вызовет тот же сервисный слой, который используется Telegram-ботом.":
      "Choose an action and describe the task. Growly uses the same service layer as the Telegram bot.",
    "Для команд, которым нужен управляемый контент-процесс.":
      "For teams that need a controlled content workflow.",
    "Добавьте известный вам официальный источник.":
      "Add an official source you already know.",
    "Добавьте известный источник или найдите публичные страницы по нише.":
      "Add a known source or discover public pages for the niche.",
    "Задача выполнена.": "Task completed.",
    "Задачу не удалось выполнить.": "The task could not be completed.",
    "Источник добавлен.": "Source added.",
    "Компактная точка входа, подготовленная для будущего Telegram Mini App.":
      "A compact entry point prepared for a future Telegram Mini App.",
    "Найдено кандидатов: {count}.": "Candidates found: {count}.",
    "Например: доставка здорового питания для офисов":
      "For example: healthy office meal delivery",
    "Например: объяснить ценность услуги и получить заявки на консультацию":
      "For example: explain the service value and generate consultation leads",
    "Например: спокойно, предметно, без громких обещаний":
      "For example: calm, specific, without exaggerated claims",
    "Не удалось войти. Проверьте почту и пароль.":
      "Sign-in failed. Check your email and password.",
    "Нет черновиков, ожидающих согласования.":
      "No drafts are waiting for approval.",
    "Опишите рынок достаточно конкретно, чтобы поиск не смешивал разные категории.":
      "Describe the market precisely enough to avoid mixing categories.",
    "Отчёт готов. Сохранено источников: {count}.":
      "Report ready. Sources saved: {count}.",
    "Отчёты появятся после анализа рынка, конкурентов или публикаций.":
      "Reports appear after market, competitor, or publication analysis.",
    "План ещё не создан. Сначала подготовьте рыночные данные.":
      "The plan has not been created. Prepare market data first.",
    "Понять рынок и регулярно готовить материалы без отдельного отдела.":
      "Understand the market and prepare content regularly without a separate department.",
    "Последние результаты, состояние данных и быстрые действия.":
      "Latest results, data status, and quick actions.",
    "Появится после сбора и анализа источников.":
      "Appears after sources are collected and analyzed.",
    "Профиль бизнеса и ссылки на подключённые рабочие пространства.":
      "Business profile and connected workspace links.",
    "Публичные сайты и каналы, которые Growly использует как рыночные свидетельства.":
      "Public websites and channels used by Growly as market evidence.",
    "Рыночные, конкурентные и результативные отчёты с источниками и ограничениями.":
      "Market, competitor, and performance reports with evidence and limitations.",
    "Связать анализ предложений с практическими темами и черновиками.":
      "Connect offer analysis with practical topics and drafts.",
    "Сначала выполните анализ рынка, затем сформируйте цель на неделю.":
      "Run market analysis first, then set a weekly goal.",
    "Собрать наблюдения, аргументы и план в одном рабочем пространстве.":
      "Keep observations, arguments, and the plan in one workspace.",
    "Сохранено новых материалов: {count}.":
      "New source items saved: {count}.",
    "Текущая база Growly использует единую бизнес-область. Supabase Auth управляет входом в веб-интерфейс, но изоляция нескольких компаний требует отдельной миграции данных с полем workspace_id.":
      "The current Growly database uses one business workspace. Supabase Auth controls web access, while multi-company isolation requires a separate workspace_id migration.",
    "Темы, форматы и задачи на неделю на основе сохранённых источников.":
      "Weekly topics, formats, and tasks based on saved sources.",
    "Укажите бизнес-цель на неделю. Growly использует последние отчёты и материалы источников.":
      "Set a business goal for the week. Growly uses recent reports and source material.",
    "Укажите нишу и регион. Growly сохранит источники до начала анализа.":
      "Enter a niche and region. Growly will save sources before analysis.",
    "Черновики появятся после генерации поста или создания материала из контент-плана.":
      "Drafts appear after generating a post or creating content from the plan.",
    "Эта страница пока использует обычную веб-сессию. При подключении Mini App параметр initData должен проверяться на сервере; данные из initDataUnsafe не используются как доверенный источник.":
      "This page currently uses a regular web session. For Mini App integration, initData must be verified on the server; initDataUnsafe is not trusted.",
    "Эти данные используются при подготовке планов и материалов. Секретные ключи на этой странице не отображаются.":
      "This data is used for plans and content. Secret keys are not displayed here.",
    "Отчёт готов: {name}. Откройте раздел «Отчёты» для просмотра.":
      "Report ready: {name}. Open Reports to view it.",
    "Черновик создан: {name}. Он доступен в разделе «Черновики».":
      "Draft created: {name}. It is available in Drafts.",
    "Готово. Получено элементов: {count}.": "Done. Items received: {count}.",
    "Синхронизация Notion завершена. Обработано объектов: {count}.":
      "Notion sync completed. Objects processed: {count}.",
    "Собирает публичные источники и формирует проверяемый обзор.":
      "Collects public sources and produces a verifiable overview.",
    "Сравнивает предложения, призывы, сильные стороны и рыночные пробелы.":
      "Compares offers, calls to action, strengths, and market gaps.",
    "Переводит рыночные наблюдения в темы, форматы и задачи на неделю.":
      "Turns market observations into weekly topics, formats, and tasks.",
    "Создаёт посты по брифу и сохраняет версии до согласования.":
      "Creates posts from a brief and keeps versions until approval.",
    "Показывает выводы, таблицы, источники, риски и следующие действия.":
      "Shows findings, tables, sources, risks, and next actions.",
    "Синхронизирует отчёты, планы, источники и готовые материалы.":
      "Syncs reports, plans, sources, and completed content.",
    "Опишите нишу, продукт и регион": "Describe the niche, product, and region",
    "Укажите рынок или тему отчёта": "Enter a market or report topic",
    "Опишите цель на неделю": "Describe the weekly goal",
    "Передайте подробный бриф, канал и желаемый призыв":
      "Provide a detailed brief, channel, and desired call to action",
    "Показать последние черновики": "Show latest drafts",
    "Показать последние отчёты": "Show latest reports",
    "Показать сохранённые источники": "Show saved sources",
    "Синхронизировать последние данные": "Sync latest data",
    "Собрать и сохранить публичные источники.":
      "Collect and save public sources.",
    "Сформировать недельный план на основе данных.":
      "Build a weekly plan from saved data.",
    "Передать бриф и получить черновик.": "Submit a brief and get a draft.",
    "Запустить новый сбор источников.": "Start a new source collection.",
    "Проверить материалы на согласовании.": "Review content awaiting approval.",
    "Открыть последние результаты.": "Open latest results.",
    "Опубликован": "Published",
    "Отклонён": "Rejected",
    "Последний анализ": "Latest analysis",
    "Последний анализ: {topic}. Источников: {count}. Что хотите сделать дальше?":
      "Latest analysis: {topic}. Sources: {count}. What would you like to do next?",
    "Спросите по последнему анализу или выберите действие":
      "Ask about the latest analysis or pick an action",
    "анализ рынка": "market analysis",
    "последний анализ рынка": "the latest market analysis",
    "Показать идеи": "Show ideas",
    "Сформировать конкурентный отчёт": "Build a competitor report",
    "Сохранено в Notion": "Saved to Notion",
    "План будет создан на основе анализа: {topic}":
      "The plan will be built from the analysis: {topic}",
    "Изменить источник": "Change source",
    "Контент-план по нише: {topic}": "Content plan for the niche: {topic}",
    "Контент": "Content",
    "Подготовьте пост на основе анализа, контент-плана или вручную.":
      "Prepare a post from an analysis, a content plan, or manually.",
    "Создать пост по последнему анализу": "Create a post from the latest analysis",
    "На основе анализа: {topic}": "Based on the analysis: {topic}",
    "Сначала выполните анализ рынка.": "Run a market analysis first.",
    "Создать пост из контент-плана": "Create a post from the content plan",
    "Откройте план и создайте черновик из выбранной темы.":
      "Open the plan and create a draft from a chosen topic.",
    "Контент-план ещё не создан.": "The content plan has not been created yet.",
    "Создать вручную": "Create manually",
    "Передайте свой бриф и канал.": "Provide your brief and channel.",
    "Бриф": "Brief",
    "Формируем пост": "Building the post",
    "Формируем пост на сервере...": "Building the post on the server...",
    "Опишите задачу подробнее (минимум 10 символов).":
      "Describe the task in more detail (at least 10 characters).",
    "Создай продающий пост для канала {channel} на основе последнего анализа рынка. Ниша: {topic}{region}. Используй боли клиентов и офферы из анализа, добавь конкретный призыв к действию.":
      "Write a sales post for the {channel} channel based on the latest market analysis. Niche: {topic}{region}. Use customer pains and offers from the analysis and add a concrete call to action.",
    "Открыть": "Open",
    "Открываем": "Opening",
    "Конкуренты / источники": "Competitors / sources",
    "Повторяющиеся призывы": "Recurring calls to action",
    "Доминирующие темы": "Dominant topics",
    "Возражения": "Objections",
    "Что сделать на этой неделе": "What to do this week",
    "Боли клиентов": "Customer pains",
    "Повторяющиеся офферы": "Recurring offers",
    "Контентные пробелы": "Content gaps",
    "Спросите по выбранному отчёту или выберите действие":
      "Ask about the selected report or pick an action",
    "Сначала выберите отчёт или опишите нишу, продукт и регион":
      "First select a report, or describe the niche, product and region",
    "Выбор отчёта": "Report selection",
    "Пока нет отчётов. Сначала запустите анализ рынка.":
      "No reports yet. Run a market analysis first.",
    "Использовать этот отчёт": "Use this report",
    "Не удалось загрузить данные. Попробуйте ещё раз или выберите другой отчёт.":
      "Could not load the data. Try again or choose another report.",
    "Технические детали": "Technical details",
    "Готовим варианты по отчёту": "Preparing options from the report",
    "Контент-план создан.": "Content plan created.",
    "Открыть контент-план": "Open content plan",
    "Сохранённый контент-план": "Saved content plan",
    "Тем в последнем плане: {count}": "Topics in the latest plan: {count}",
    "Аудитория": "Audience",
    "Оффер": "Offer",
    "Каналы": "Channels",
    "Форматы": "Formats",
    "Призыв к действию": "Call to action",
    "Дополнительные пожелания": "Additional notes",
    "Например: спокойный тон, без громких обещаний":
      "For example: calm tone, no loud promises",
    "Или впишите своё": "Or write your own",
    "Источников: {count}": "Sources: {count}",
    "Отчёт": "Report",
    "План будет создан на основе отчёта":
      "The plan will be built from the report",
    "Изменить отчёт": "Change report",
    "Выберите отчёт, на основе которого создать контент-план":
      "Choose the report to build the content plan from",
    "Создать без отчёта": "Create without a report",
    "Назад к выбору отчёта": "Back to report selection",
    "Чат работает с отчётом «{topic}». Задайте вопрос или выберите действие.":
      "The chat is working with the report «{topic}». Ask a question or pick an action.",
    "Опишите нишу, продукт и регион — или вернитесь и выберите отчёт.":
      "Describe the niche, product and region — or go back and select a report.",
    "отчёт": "report",
    "Выберите отчёт, с которым будет работать чат":
      "Choose the report the chat will work with",
    "Продолжить без отчёта": "Continue without a report",
    "Чат работает с отчётом": "The chat is working with the report",
    "Показать идеи постов": "Show post ideas",
    "Идеи постов": "Post ideas",
    "Разобрать конкурентов": "Analyze competitors",
    "Вопрос по отчёту": "Question about the report",
    "Использовать для контент-плана": "Use for content plan",
    "Использовать в чате": "Use in chat",
    "Не удалось выбрать отчёт. Попробуйте ещё раз.":
      "Could not select the report. Please try again.",
    "Выбрать другой отчёт": "Choose another report",
    "Загружаю контекст отчёта…": "Loading report context…",
    "Готовлю варианты для контент-плана…":
      "Preparing content-plan options…",
    "Показаны базовые варианты по теме отчёта.":
      "Showing default options based on the report topic.",
    "Обновить": "Refresh",
    "Я работаю с отчётом «{topic}». Выберите действие или задайте вопрос по этому рынку.":
      "I'm working with the report «{topic}». Pick an action or ask a question about this market.",
    "Выберите быстрое действие выше или задайте вопрос ниже.":
      "Pick a quick action above or ask a question below.",
    "Шаг {step}": "Step {step}",
    "Что должен сделать контент на этой неделе?":
      "What should the content achieve this week?",
    "Для кого создаём контент?": "Who is the content for?",
    "Что продвигаем?": "What are we promoting?",
    "Где публикуем?": "Where do we publish?",
    "Какое действие должен совершить клиент?":
      "What action should the customer take?",
    "Дополнительная инструкция (необязательно)":
      "Additional instruction (optional)",
    "Свой вариант": "Your own option",
    "Все каналы": "All channels",
    "Создание": "Create",
    "CTA": "CTA",
    "Сохранить как черновик": "Save as draft",
    "Черновик сохранён.": "Draft saved.",
    "Обновить варианты": "Refresh options",
    "Показали базовые варианты. Можно обновить или вписать свой вариант.":
      "Showing default options. You can refresh them or write your own.",
    "Варианты подготовлены на основе выбранного отчёта.":
      "Options were prepared from the selected report.",
    "Подключено": "Connected",
    "Не подключено": "Not connected",
    "да": "yes",
    "нет": "no",
    "Проверяем": "Checking",
    "Обновляем": "Refreshing",
    "Готовим": "Preparing",
    "Отправляем": "Sending",
    "Интеграции": "Integrations",
    "Подключения Growly: Telegram, Notion и автопубликация в соцсети.":
      "Growly connections: Telegram, Notion and social auto-publishing.",
    "Назад к настройкам": "Back to settings",
    "Канал публикации не указан.": "Publishing channel is not set.",
    "Проверить публикацию": "Check publishing",
    "Корневая страница настроена.": "Root page is configured.",
    "Корневая страница не настроена.": "Root page is not configured.",
    "Проверить синхронизацию": "Check sync",
    "API-ключ настроен": "API key configured",
    "Аккаунтов подключено": "Accounts connected",
    "Проверить подключение": "Test connection",
    "Обновить аккаунты": "Refresh accounts",
    "Настроить публикацию": "Set up publishing",
    "Социальные сети": "Social networks",
    "Подключённые аккаунты": "Connected accounts",
    "Обновить список аккаунтов": "Refresh account list",
    "Автопубликация не подключена. Growly может подготовить пакет для ручной публикации.":
      "Auto-publishing is not connected. Growly can prepare a manual publishing package.",
    "Нет подключённого аккаунта.": "No connected account.",
    "Список аккаунтов обновлён.": "Account list refreshed.",
    "Blotato подключён": "Blotato connected",
    "Интеграции и публикация": "Integrations and publishing",
    "Telegram, Notion и автопубликация в соцсети через Blotato.":
      "Telegram, Notion and social auto-publishing via Blotato.",
    "Открыть интеграции": "Open integrations",
    "Администрирование": "Administration",
    "Настройка публикации": "Publishing setup",
    "Сопоставьте аккаунты Blotato с платформами Growly.":
      "Map Blotato accounts to Growly platforms.",
    "Назад к интеграциям": "Back to integrations",
    "Чек-лист подключения": "Setup checklist",
    "Добавьте BLOTATO_API_KEY в секреты бэкенда":
      "Add BLOTATO_API_KEY to the backend secrets",
    "Подключите аккаунты в Blotato": "Connect accounts in Blotato",
    "Обновите аккаунты в Growly": "Refresh accounts in Growly",
    "Сопоставьте аккаунты с платформами": "Map accounts to platforms",
    "Проверьте публикацию": "Test publishing",
    "API-ключ хранится только в секретах бэкенда и не отображается в интерфейсе.":
      "The API key is stored only in backend secrets and is never shown in the UI.",
    "Сопоставление платформ": "Platform mapping",
    "Аккаунты не найдены. Подключите их в Blotato и обновите список.":
      "No accounts found. Connect them in Blotato and refresh the list.",
    "Не публиковать": "Do not publish",
    "Сохранить сопоставление": "Save mapping",
    "Сопоставление аккаунтов сохранено.": "Account mapping saved.",
    "Загружаем черновик": "Loading draft",
    "Публикация": "Publishing",
    "Через Telegram-бота": "Via the Telegram bot",
    "Нет аккаунта": "No account",
    "Опубликовать сейчас": "Publish now",
    "Запланировать": "Schedule",
    "Пакет для ручной публикации": "Manual publishing package",
    "Дата и время публикации": "Publish date and time",
    "Черновик пуст — публикация недоступна.": "The draft is empty — publishing is unavailable.",
    "Подготовить пакет для ручной публикации": "Prepare a manual publishing package",
    "Открыть пост": "Open post",
    "Открыть и опубликовать": "Open and publish",
    "Хук": "Hook",
    "Текст": "Text",
    "Сценарий": "Script",
    "Визуал": "Visual",
    "Хэштеги": "Hashtags",
    "Отправлено": "Submitted",
    "Запланировано": "Scheduled",
    "Пропущено": "Skipped",
    "Не поддерживается": "Not supported",
    "Blotato не подключён. Автопубликация в соцсети временно недоступна.":
      "Blotato is not connected. Social auto-publishing is temporarily unavailable.",
    "Для выбранной платформы не выбран аккаунт публикации.":
      "No publishing account is selected for the chosen platform.",
    "Не удалось отправить публикацию.": "Could not send the publication.",
    "Эта платформа пока не поддерживается для автопубликации.":
      "This platform is not supported for auto-publishing yet.",
    "Не удалось подготовить безопасный текст поста. Измените бриф или попробуйте ещё раз.":
      "Could not prepare a safe post text. Adjust the brief or try again.",
    "Текст публикации": "Post text",
    "{count} слов": "{count} words",
    "Оптимально до 125–150 слов для поста.": "Aim for 125–150 words per post.",
    "Preview": "Preview",
    "Добавьте изображение или видео для Instagram":
      "Add an image or video for Instagram",
    "Куда публикуем": "Where to publish",
    "Недоступные каналы ({count})": "Unavailable channels ({count})",
    "Настроить интеграции": "Set up integrations",
    "Когда публиковать": "When to publish",
    "Пост уйдёт в выбранные соцсети сразу.":
      "The post goes to the selected networks right away.",
    "Выберите дату и время публикации.": "Choose a publish date and time.",
    "Готовый текст и медиа для ручного постинга.":
      "Ready text and media for manual posting.",
    "Тип медиа": "Media type",
    "Загрузить фото/видео": "Upload photo/video",
    "AI-генерация медиа": "AI media generation",
    "Показать все {count}": "Show all {count}",
    "Свернуть": "Collapse",
    "Время указывается в вашем часовом поясе.":
      "Time is shown in your timezone.",
    "История и статус": "History and status",
    "Обновлён": "Updated",
    "Версия": "Version",
    "Создан из контент-плана": "Created from the content plan",
    "Подготовить пакет": "Prepare package",
    "Выберите хотя бы один канал.": "Select at least one channel.",
    "Укажите дату и время публикации.": "Set a publish date and time.",
    "Пост опубликован": "Post published",
    "Пост запланирован": "Post scheduled",
    "Не удалось опубликовать": "Could not publish",
    "Пакет готов": "Package ready",
    "Не удалось подготовить пакет": "Could not prepare the package",
    "Не удалось загрузить черновик. Попробуйте обновить страницу.":
      "Could not load the draft. Try refreshing the page.",
    "Задачи": "Tasks",
    "Что нужно сделать команде: ответственные, сроки и статусы.":
      "What the team needs to do: owners, due dates and statuses.",
    "Команда": "Team",
    "Участники этого workspace и их роли.":
      "Members of this workspace and their roles.",
    "Поделиться с командой": "Share with team",
    "Участники": "Members",
    "Роль": "Role",
    "Присоединился": "Joined",
    "Приглашён": "Invited",
    "Удалить участника": "Remove member",
    "Приглашения": "Invitations",
    "Ожидает": "Pending",
    "Отменить приглашение": "Revoke invitation",
    "Notion используется как внутренний инструмент синхронизации и не является публичным кабинетом клиента.":
      "Notion is an internal sync tool, not the client's public portal.",
    "Владелец": "Owner",
    "Только просмотр": "Viewer",
    "Редактор": "Editor",
    "Пригласить участника": "Invite a member",
    "Скопируйте ссылку и отправьте её участнику ({email}).":
      "Copy the link and send it to {email}.",
    "Приглашение создано": "Invitation created",
    "Приглашение отправлено на {email}.": "Invitation sent to {email}.",
    "Можно также скопировать ссылку и отправить вручную.":
      "You can also copy the link and send it manually.",
    "Скопировать ссылку": "Copy link",
    "Скопировано": "Copied",
    "Сообщение (необязательно)": "Message (optional)",
    "Отмена": "Cancel",
    "Отправить приглашение": "Send invitation",
    "Не удалось скопировать ссылку": "Could not copy the link",
    "Приглашение в Growly": "Invitation to Growly",
    "Присоединяйтесь к команде": "Join the team",
    "Вас пригласили работать с отчётами, контент-планом и черновиками внутри Growly.":
      "You've been invited to work with reports, content plans and drafts in Growly.",
    "Приглашение": "Invitation",
    "Приглашение истекло. Попросите владельца отправить новое.":
      "The invitation has expired. Ask the owner to send a new one.",
    "Приглашение больше недействительно.":
      "This invitation is no longer valid.",
    "Войдите или зарегистрируйтесь, чтобы принять приглашение.":
      "Sign in or sign up to accept the invitation.",
    "Принять приглашение": "Accept invitation",
    "Принимаем": "Accepting",
    "Скопировать ссылку для просмотра": "Copy view-only link",
    "Ссылка защищена паролем": "This link is password-protected",
    "Ссылка недоступна.": "This link is unavailable.",
    "Просмотр только для чтения · Growly": "Read-only view · Growly",
    "Что делать дальше": "What to do next",
    "Без срока": "No due date",
    "Задач пока нет.": "No tasks yet.",
    "Что нужно сделать?": "What needs doing?",
    "Ответственный (email)": "Assignee (email)",
    "Срок": "Due date",
    "Приоритет": "Priority",
    "Создать задачу": "Create task",
    "Изменить статус": "Change status",
    "Удалить": "Delete",
    "К выполнению": "To do",
    "В работе": "In progress",
    "Готово": "Done",
    "Запущено": "Started",
    "Нужно действие": "Action needed",
    "Отменено": "Cancelled",
    "Низкий": "Low",
    "Средний": "Medium",
    "Высокий": "High",
  },
  kk: {
    "Язык": "Тіл",
    "Подключения Growly: автопостинг в ваши соцсети.": "Growly байланыстары: әлеуметтік желілерге автопостинг.",
    "Instagram автопостинг": "Instagram автопостинг",
    "Ожидает подключения": "Қосылуды күтуде",
    "Growly может автоматически публиковать посты в ваш Instagram. Подключение выполняется безопасно через официальный вход Instagram/Meta. Мы никогда не просим и не храним ваш пароль.": "Growly посттарды Instagram-ыңызға автоматты түрде жариялай алады. Қосылу Instagram/Meta ресми кірісі арқылы қауіпсіз орындалады. Біз сіздің құпиясөзіңізді ешқашан сұрамаймыз және сақтамаймыз.",
    "Подключение выполняется вручную администратором Growly на MVP-этапе. Вы не передаёте пароль. Вы сами подтверждаете доступ через официальный экран Instagram/Meta.": "MVP кезеңінде қосылуды Growly әкімшісі қолмен орындайды. Сіз құпиясөзді бермейсіз. Қол жеткізуді ресми Instagram/Meta экраны арқылы өзіңіз растайсыз.",
    "Instagram не подключен": "Instagram қосылмаған",
    "Отправьте заявку, и мы поможем подключить ваш Instagram к автопостингу. Подключение проходит через официальный OAuth, без передачи пароля.": "Өтінім жіберіңіз, біз сіздің Instagram-ды автопостингке қосуға көмектесеміз. Қосылу құпиясөзді берусіз ресми OAuth арқылы өтеді.",
    "Instagram username": "Instagram username",
    "Отправить заявку на подключение": "Қосылуға өтінім жіберу",
    "Заявка на подключение отправлена": "Қосылуға өтінім жіберілді",
    "Администратор Growly свяжется с вами и поможет безопасно подключить Instagram через OAuth. Не отправляйте пароль от Instagram.": "Growly әкімшісі сізбен байланысып, Instagram-ды OAuth арқылы қауіпсіз қосуға көмектеседі. Instagram құпиясөзін жібермеңіз.",
    "Обновить статус": "Статусты жаңарту",
    "Отменить заявку": "Өтінімді болдырмау",
    "Отменяем": "Болдырмаудамыз",
    "Instagram подключен": "Instagram қосылды",
    "Growly может публиковать посты в этот аккаунт через Blotato.": "Growly бұл аккаунтқа Blotato арқылы пост жариялай алады.",
    "ID аккаунта": "Аккаунт ID",
    "Подключён": "Қосылған",
    "Не удалось подключить Instagram": "Instagram-ды қосу мүмкін болмады",
    "Подключение не удалось. Отправьте заявку повторно.": "Қосылу сәтсіз аяқталды. Өтінімді қайта жіберіңіз.",
    "Повторить заявку": "Өтінімді қайталау",
    "Укажите ваш Instagram username.": "Instagram username енгізіңіз.",
    "Заявка отправлена.": "Өтінім жіберілді.",
    "Заявка отменена.": "Өтінім болдырылмады.",
    "Instagram отключён.": "Instagram ажыратылды.",
    "Не удалось загрузить интеграции. Попробуйте ещё раз.": "Интеграцияларды жүктеу мүмкін болмады. Қайталап көріңіз.",
    "Доступ ограничен": "Қол жеткізу шектелген",
    "Доступ только для администратора Growly.": "Тек Growly әкімшісіне рұқсат.",
    "Blotato и подключения": "Blotato және байланыстар",
    "Подключение клиентов к автопостингу выполняется вручную через официальный OAuth.": "Клиенттерді автопостингке қосу ресми OAuth арқылы қолмен орындалады.",
    "Как подключать клиента безопасно": "Клиентті қауіпсіз қалай қосу керек",
    "Никогда не просите пароль от Instagram.": "Instagram құпиясөзін ешқашан сұрамаңыз.",
    "Подключение должно проходить через официальный OAuth.": "Қосылу ресми OAuth арқылы өтуі керек.",
    "Клиент сам входит в Instagram/Meta на своём устройстве.": "Клиент Instagram/Meta-ға өз құрылғысында өзі кіреді.",
    "После подключения нажмите «Обновить аккаунты» в Growly.": "Қосқаннан кейін Growly-де «Аккаунттарды жаңарту» түймесін басыңыз.",
    "Найдите новый accountId из Blotato и свяжите его с заявкой клиента.": "Blotato-дан жаңа accountId табыңыз және оны клиент өтінімімен байланыстырыңыз.",
    "Не подключайте аккаунт клиента, если вы не уверены, что клиент сам дал разрешение через OAuth.": "Клиент OAuth арқылы өзі рұқсат бергеніне сенімді болмасаңыз, оның аккаунтын қоспаңыз.",
    "Статус Blotato": "Blotato күйі",
    "настроен": "бапталған",
    "не настроен": "бапталмаған",
    "Последняя проверка": "Соңғы тексеру",
    "Blotato не отвечает": "Blotato жауап бермейді",
    "Заявки на подключение": "Қосылу өтінімдері",
    "Заявок пока нет.": "Әзірге өтінім жоқ.",
    "Пользователь": "Пайдаланушы",
    "В работу": "Жұмысқа алу",
    "Связать аккаунт": "Аккаунтты байланыстыру",
    "Отметить ошибку": "Қате деп белгілеу",
    "Отменить": "Болдырмау",
    "Статус заявки обновлён.": "Өтінім статусы жаңартылды.",
    "Сначала выберите аккаунт Blotato.": "Алдымен Blotato аккаунтын таңдаңыз.",
    "Аккаунт связан с заявкой.": "Аккаунт өтініммен байланыстырылды.",
    "Аккаунты из Blotato": "Blotato аккаунттары",
    "Нажмите «Обновить аккаунты», чтобы получить список из Blotato.": "Blotato-дан тізімді алу үшін «Аккаунттарды жаңарту» түймесін басыңыз.",
    "Платформа": "Платформа",
    "Связан с": "Байланысты",
    "Instagram автопостинг не подключен. Отправьте заявку на подключение в Интеграциях.": "Instagram автопостинг қосылмаған. Интеграцияларда қосылуға өтінім жіберіңіз.",
    "Заявка на подключение Instagram уже отправлена. После подключения вы сможете публиковать посты автоматически.": "Instagram-ды қосуға өтінім жіберілді. Қосылғаннан кейін посттарды автоматты жариялай аласыз.",
    "Instagram подключен. Пост можно опубликовать или запланировать.": "Instagram қосылды. Постты жариялауға немесе жоспарлауға болады.",
    "Заявка уже отправлена": "Өтінім жіберілген",
    "Администратор подключит ваш Instagram через безопасный OAuth-flow. После подключения публикация станет доступна.": "Әкімші Instagram-ыңызды қауіпсіз OAuth арқылы қосады. Қосылғаннан кейін жариялау қолжетімді болады.",
    "Чтобы Growly мог автоматически публиковать посты, отправьте заявку на подключение Instagram. Пароль не нужен: подключение проходит через официальный OAuth.": "Growly посттарды автоматты жариялауы үшін Instagram-ды қосуға өтінім жіберіңіз. Құпиясөз қажет емес: қосылу ресми OAuth арқылы өтеді.",
    "Instagram через Blotato": "Blotato арқылы Instagram",
    "Instagram подключён": "Instagram қосылды",
    "Выберите аккаунт": "Аккаунтты таңдаңыз",
    "Подключите Blotato для автопостинга": "Автопостинг үшін Blotato қосыңыз",
    "Growly будет отправлять готовые посты в Blotato, а Blotato опубликует их в Instagram.":
      "Growly дайын посттарды Blotato-ға жібереді, ал Blotato оларды Instagram-ға жариялайды.",
    "API-ключ Blotato": "Blotato API кілті",
    "Вставьте BLOTATO_API_KEY": "BLOTATO_API_KEY кілтін қойыңыз",
    "Ключ хранится только на сервере в зашифрованном виде и никогда не возвращается в браузер.":
      "Кілт тек серверде шифрланған түрде сақталады және браузерге ешқашан қайтарылмайды.",
    "Сохранить API ключ": "API кілтін сақтау",
    "Blotato подключён. Выберите Instagram аккаунт для автопостинга.":
      "Blotato қосылды. Автопостинг үшін Instagram аккаунтын таңдаңыз.",
    "Instagram аккаунты не найдены. Сначала подключите Instagram в кабинете Blotato, затем вернитесь сюда и нажмите «Обновить аккаунты».":
      "Instagram аккаунттары табылмады. Алдымен Blotato кабинетінде Instagram-ды қосыңыз, содан кейін осында оралып «Аккаунттарды жаңарту» түймесін басыңыз.",
    "Instagram аккаунт": "Instagram аккаунты",
    "Сохранить аккаунт": "Аккаунтты сақтау",
    "Открыть кабинет Blotato": "Blotato кабинетін ашу",
    "Аккаунт": "Аккаунт",
    "Аккаунтов в Blotato": "Blotato-дағы аккаунттар",
    "Сменить аккаунт": "Аккаунтты ауыстыру",
    "Отключить": "Ажырату",
    "Отключаем": "Ажыратудамыз",
    "Другие соцсети": "Басқа әлеуметтік желілер",
    "Threads, TikTok, YouTube, Facebook, LinkedIn и X публикуются через Blotato.":
      "Threads, TikTok, YouTube, Facebook, LinkedIn және X Blotato арқылы жарияланады.",
    "Введите корректный API-ключ Blotato.": "Дұрыс Blotato API кілтін енгізіңіз.",
    "Blotato подключён. Найдено аккаунтов: {count}.":
      "Blotato қосылды. Табылған аккаунттар: {count}.",
    "Выберите Instagram аккаунт из списка.":
      "Тізімнен Instagram аккаунтын таңдаңыз.",
    "Instagram аккаунт сохранён.": "Instagram аккаунты сақталды.",
    "Выберите другой Instagram аккаунт.": "Басқа Instagram аккаунтын таңдаңыз.",
    "Blotato отключён.": "Blotato ажыратылды.",
    "Опубликовать": "Жариялау",
    "Создать черновик": "Черновик жасау",
    "Открыть черновик": "Черновикті ашу",
    "Посмотреть": "Қарау",
    "Закрыть": "Жабу",
    "Запланирован": "Жоспарланған",
    "Выберите тему из плана и нажмите «Создать черновик», «Опубликовать» или «Запланировать». Для автопостинга в Instagram сначала подключите Blotato в разделе «Интеграции».":
      "Жоспардан тақырып таңдап, «Черновик жасау», «Жариялау» немесе «Жоспарлау» түймесін басыңыз. Instagram-ға автопостинг үшін алдымен «Интеграциялар» бөлімінде Blotato қосыңыз.",
    "Instagram не подключён": "Instagram қосылмаған",
    "Чтобы публиковать посты автоматически, подключите Instagram через Blotato.":
      "Посттарды автоматты түрде жариялау үшін Blotato арқылы Instagram қосыңыз.",
    "Перейти в Интеграции": "Интеграцияларға өту",
    "Ссылка на изображение или видео": "Сурет немесе бейне сілтемесі",
    "Медиа": "Медиа",
    "Фото, видео или карусель для публикации":
      "Жарияланымға арналған фото, бейне немесе карусель",
    "Загрузить фото или видео": "Фото немесе бейне жүктеу",
    "Загружаем медиа": "Медиа жүктелуде",
    "Удалить медиа": "Медианы жою",
    "Генерация в Blotato": "Blotato-да жасау",
    "Карусель изображений": "Суреттер каруселі",
    "AI-видео": "AI-бейне",
    "AI-изображение": "AI-сурет",
    "Что должно быть на фото или видео":
      "Фото немесе бейнеде не болуы керек",
    "Сгенерировать": "Жасау",
    "Генерируем": "Жасалуда",
    "Или вставьте публичную ссылку": "Немесе ашық сілтемені қойыңыз",
    "В очереди": "Кезекте",
    "Подготовка сценария": "Сценарий дайындалуда",
    "Генерация медиа": "Медиа жасалуда",
    "Экспорт медиа": "Медиа экспортталуда",
    "Медиа готово и добавлено к публикации.":
      "Медиа дайын және жарияланымға қосылды.",
    "Можно добавить не более 10 файлов.":
      "10 файлдан артық қосуға болмайды.",
    "Поддерживаются изображения JPG, PNG, WEBP, GIF и видео MP4, MOV, WEBM.":
      "JPG, PNG, WEBP, GIF суреттері және MP4, MOV, WEBM бейнелері қолданылады.",
    "Не удалось загрузить файл в Blotato.":
      "Файлды Blotato-ға жүктеу мүмкін болмады.",
    "Blotato не вернул ID созданного медиа.":
      "Blotato жасалған медианың ID мәнін қайтармады.",
    "Blotato не вернул созданное медиа.":
      "Blotato жасалған медианы қайтармады.",
    "Blotato не удалось сгенерировать медиа.":
      "Blotato медиа жасай алмады.",
    "Генерация заняла слишком много времени. Проверьте результат в Blotato.":
      "Жасау тым ұзаққа созылды. Нәтижені Blotato-дан тексеріңіз.",
    "Для публикации в Instagram добавьте изображение или видео.":
      "Instagram-ға жариялау үшін сурет немесе бейне қосыңыз.",
    "Instagram выбран, но автопостинг ещё не подключён. Подключите Instagram через Blotato в Интеграциях.":
      "Instagram таңдалды, бірақ автопостинг әлі қосылмаған. «Интеграциялар» бөлімінде Blotato арқылы Instagram қосыңыз.",
    "Подключить Instagram": "Instagram қосу",
    "Сохраните API-ключ Blotato на странице «Интеграции»":
      "«Интеграциялар» бетінде Blotato API кілтін сақтаңыз",
    "Рабочее пространство": "Жұмыс кеңістігі",
    "Основная навигация": "Негізгі навигация",
    "Обзор": "Шолу",
    "Чат": "Чат",
    "Анализ рынка": "Нарықты талдау",
    "Отчёты": "Есептер",
    "Контент-план": "Контент-жоспар",
    "Черновики": "Нобайлар",
    "Источники": "Дереккөздер",
    "Настройки": "Баптаулар",
    "Выйти": "Шығу",
    "Открыть меню": "Мәзірді ашу",
    "Закрыть меню": "Мәзірді жабу",
    "Возможности": "Мүмкіндіктер",
    "Как работает": "Қалай жұмыс істейді",
    "Для кого": "Кімге арналған",
    "Открыть Growly": "Growly-ді ашу",
    "Маркетинговое рабочее пространство": "Маркетингтік жұмыс кеңістігі",
    "От рыночных данных до готового контента.":
      "Нарық деректерінен дайын контентке дейін.",
    "Начать работу": "Жұмысты бастау",
    "Посмотреть возможности": "Мүмкіндіктерді көру",
    "Рабочая область": "Жұмыс аймағы",
    "Сегодня": "Бүгін",
    "Система готова": "Жүйе дайын",
    "Следующее действие": "Келесі әрекет",
    "Запустить анализ рынка": "Нарық талдауын бастау",
    "Новый анализ": "Жаңа талдау",
    "Последний отчёт": "Соңғы есеп",
    "Ожидает данных": "Деректер күтілуде",
    "Появится после первого анализа": "Алғашқы талдаудан кейін пайда болады",
    "Не создан": "Жасалмаған",
    "Формируется на основе источников": "Дереккөздер негізінде құрылады",
    "Задача": "Тапсырма",
    "Статус": "Күй",
    "Данные": "Деректер",
    "Не запускался": "Іске қосылмаған",
    "Нет": "Жоқ",
    "Синхронизация Notion": "Notion синхрондауы",
    "По настройке": "Баптауға сай",
    "Сервер": "Сервер",
    "Что делает Growly": "Growly не істейді",
    "Один процесс вместо набора разрозненных инструментов.":
      "Бөлек құралдардың орнына бір үдеріс.",
    "Рабочий процесс": "Жұмыс үдерісі",
    "Каждый вывод остаётся связан с источником.":
      "Әр қорытынды дереккөзбен байланысты қалады.",
    "Укажите нишу и регион": "Ниша мен аймақты көрсетіңіз",
    "Проверьте собранные источники": "Жиналған дереккөздерді тексеріңіз",
    "Получите конкурентный отчёт": "Бәсекелестер есебін алыңыз",
    "Сформируйте контент-план": "Контент-жоспар құрыңыз",
    "Подготовьте и согласуйте посты": "Жазбаларды дайындап, бекітіңіз",
    "Малый бизнес": "Шағын бизнес",
    "Маркетолог": "Маркетолог",
    "Агентство": "Агенттік",
    "Telegram и Instagram": "Telegram және Instagram",
    "Начните с первого анализа рынка.": "Алғашқы нарық талдауынан бастаңыз.",
    "Открыть рабочую область": "Жұмыс аймағын ашу",
    "Контакты": "Байланыс",
    "Рабочее пространство Growly": "Growly жұмыс кеңістігі",
    "Рынок, отчёты и контент в одном процессе.":
      "Нарық, есептер және контент бір үдерісте.",
    "Вернуться на главную": "Басты бетке оралу",
    "Вход": "Кіру",
    "Рабочая почта": "Жұмыс поштасы",
    "Пароль": "Құпиясөз",
    "Проверяем доступ": "Қолжетімділікті тексерудеміз",
    "Войти": "Кіру",
    "Открыть локальный режим": "Жергілікті режимді ашу",
    "Вход временно недоступен": "Кіру уақытша қолжетімсіз",
    "Черновики на согласовании": "Бекітудегі нобайлар",
    "Открыть список": "Тізімді ашу",
    "Активные источники": "Белсенді дереккөздер",
    "Управлять источниками": "Дереккөздерді басқару",
    "Опубликованные материалы": "Жарияланған материалдар",
    "По данным Growly": "Growly деректері бойынша",
    "Последняя синхронизация Notion": "Notion соңғы синхрондауы",
    "Настроен": "Бапталған",
    "Не настроен": "Бапталмаған",
    "Последние результаты": "Соңғы нәтижелер",
    "Что уже готово": "Дайын нәтижелер",
    "Все отчёты": "Барлық есептер",
    "Конкурентный отчёт": "Бәсекелестер есебі",
    "Быстрые действия": "Жылдам әрекеттер",
    "Продолжить работу": "Жұмысты жалғастыру",
    "Новый анализ рынка": "Жаңа нарық талдауы",
    "Создать контент-план": "Контент-жоспар жасау",
    "Подготовить пост": "Жазба дайындау",
    "Согласование": "Бекіту",
    "Черновики в работе": "Жұмыстағы нобайлар",
    "Все черновики": "Барлық нобайлар",
    "Канал не указан": "Арна көрсетілмеген",
    "Исследование": "Зерттеу",
    "Параметры анализа": "Талдау параметрлері",
    "Ниша или продукт": "Ниша немесе өнім",
    "Регион и язык": "Аймақ және тіл",
    "Известные конкуренты": "Белгілі бәсекелестер",
    "Можно оставить пустым": "Бос қалдыруға болады",
    "Анализ выполняется": "Талдау орындалуда",
    "Запустить анализ": "Талдауды бастау",
    "Ищу источники": "Дереккөздерді іздеудемін",
    "Сохраняю данные": "Деректерді сақтаудамын",
    "Анализирую": "Талдаудамын",
    "Формирую отчёт": "Есеп құрудамын",
    "Синхронизирую с Notion": "Notion-мен синхрондаудамын",
    "Не удалось завершить анализ рынка.":
      "Нарық талдауын аяқтау мүмкін болмады.",
    "Анализ занимает больше времени, чем ожидалось.":
      "Талдау күтілгеннен ұзақ уақыт алып жатыр.",
    "Сервер не успел запустить анализ. Повторите попытку.":
      "Сервер талдауды уақытында іске қоса алмады. Қайталап көріңіз.",
    "Открыть отчёт": "Есепті ашу",
    "Открыть отчёты": "Есептерді ашу",
    "Отчёт создан, но ссылка на него не получена. Откройте раздел Отчёты.":
      "Есеп жасалды, бірақ оған сілтеме алынбады. Есептер бөлімін ашыңыз.",
    "База знаний": "Білім базасы",
    "Поиск по отчётам": "Есептерден іздеу",
    "Найти отчёт": "Есепті табу",
    "Всего: {count}": "Барлығы: {count}",
    "{count} источников": "{count} дереккөз",
    "Краткий вывод не указан.": "Қысқаша қорытынды көрсетілмеген.",
    "Пока нет отчётов": "Әзірге есептер жоқ",
    "Планирование": "Жоспарлау",
    "Новый план": "Жаңа жоспар",
    "Цель недели": "Апталық мақсат",
    "Формируем план": "Жоспар құрылуда",
    "Создать план": "Жоспар жасау",
    "Создано элементов: {count}.": "Жасалған элементтер: {count}.",
    "Не удалось создать контент-план.": "Контент-жоспар жасау мүмкін болмады.",
    "Причина: {reason}": "Себебі: {reason}",
    "Созданный план на основе реальных отчётов Growly.":
      "Growly нақты есептері негізінде жасалған жоспар.",
    "Вернуться к планам": "Жоспарларға қайту",
    "Черновик «{name}» создан.": "«{name}» нобайы жасалды.",
    "Календарь": "Күнтізбе",
    "Запланированные материалы": "Жоспарланған материалдар",
    "Контент-план ещё не создан": "Контент-жоспар әлі жасалмаған",
    "Дата": "Күні",
    "Канал": "Арна",
    "Тема": "Тақырып",
    "Цель": "Мақсат",
    "Формат": "Формат",
    "Призыв": "Әрекетке шақыру",
    "Источник идеи": "Идея дереккөзі",
    "Не указан": "Көрсетілмеген",
    "Без темы": "Тақырыпсыз",
    "Не указана": "Көрсетілмеген",
    "Создаём": "Жасалуда",
    "Создан": "Жасалды",
    "Черновик": "Нобай",
    "Фильтр статуса": "Күй сүзгісі",
    "Все статусы": "Барлық күйлер",
    "На согласовании": "Бекітуде",
    "Согласованные": "Бекітілген",
    "Отклонённые": "Қабылданбаған",
    "Опубликованные": "Жарияланған",
    "Показано: {count}": "Көрсетілді: {count}",
    "версия {version}": "{version}-нұсқа",
    "Сохранён в Notion": "Notion-ға сақталды",
    "Не сохранён в Notion": "Notion-ға сақталмаған",
    "Согласовать": "Бекіту",
    "Новая версия": "Жаңа нұсқа",
    "В Notion": "Notion-ға",
    "Отклонить": "Қабылдамау",
    "Черновиков пока нет": "Әзірге нобайлар жоқ",
    "Создать пост": "Жазба жасау",
    "Проверить активные": "Белсенділерді тексеру",
    "Найти источники": "Дереккөздерді табу",
    "Добавить вручную": "Қолмен қосу",
    "Способ добавления": "Қосу тәсілі",
    "Поиск": "Іздеу",
    "Вручную": "Қолмен",
    "Ниша": "Ниша",
    "Регион": "Аймақ",
    "Платформы через запятую": "Платформалар, үтір арқылы",
    "Название": "Атауы",
    "Выполняется": "Орындалуда",
    "Найти кандидатов": "Үміткерлерді табу",
    "Добавить источник": "Дереккөз қосу",
    "Реестр": "Тізілім",
    "Сохранённые источники": "Сақталған дереккөздер",
    "Источников пока нет": "Әзірге дереккөздер жоқ",
    "URL не указан": "URL көрсетілмеген",
    "Командный интерфейс": "Командалық интерфейс",
    "Действия": "Әрекеттер",
    "Конкуренты": "Бәсекелестер",
    "Сохранить в Notion": "Notion-ға сақтау",
    "Сообщение": "Хабарлама",
    "Отправить": "Жіберу",
    "Ошибка": "Қате",
    "Задача выполняется на сервере.": "Тапсырма серверде орындалуда.",
    "Длительные операции могут занять несколько минут.":
      "Ұзақ операциялар бірнеше минутқа созылуы мүмкін.",
    "Конфигурация": "Конфигурация",
    "Профиль бизнеса": "Бизнес профилі",
    "Тон бренда": "Бренд үні",
    "Telegram-канал": "Telegram арнасы",
    "Корневая страница Notion": "Notion түбірлік беті",
    "Настройки сохранены.": "Баптаулар сақталды.",
    "Сохраняем": "Сақталуда",
    "Сохранить": "Сақтау",
    "Режим рабочего пространства": "Жұмыс кеңістігінің режимі",
    "Оплата": "Төлем",
    "Тариф и оплата": "Тариф және төлем",
    "План, оплата и доступ к платёжному кабинету Growly.":
      "Тариф, төлем және Growly төлем кабинетіне қолжетімділік.",
    "Открыть оплату": "Төлемді ашу",
    "Управляйте тарифом Growly, статусом подписки и доступом к платёжному кабинету.":
      "Growly тарифін, жазылым күйін және төлем кабинетіне қолжетімділікті басқарыңыз.",
    "Посмотреть тарифы": "Тарифтерді көру",
    "Не удалось загрузить данные по оплате.": "Төлем деректерін жүктеу мүмкін болмады.",
    "Платёжный кабинет пока не настроен.":
      "Төлем кабинеті әзірге бапталмаған.",
    "Оплата пока не настроена.": "Төлем әзірге бапталмаған.",
    "Текущий тариф": "Ағымдағы тариф",
    "Следующее списание": "Келесі төлем",
    "Нет даты списания": "Төлем күні жоқ",
    "Отмена в конце периода": "Кезең соңында бас тарту",
    "Выбрать тариф": "Тариф таңдау",
    "Изменить тариф": "Тарифті өзгерту",
    "Управлять оплатой": "Төлемді басқару",
    "Тарифы": "Тарифтер",
    "Выберите размер рабочей области": "Жұмыс кеңістігінің өлшемін таңдаңыз",
    "Предпросмотр": "Алдын ала қарау",
    "Имя пользователя Instagram": "Instagram пайдаланушы аты",
    "Мобильный режим": "Мобильді режим",
    "Growly для Telegram": "Telegram үшін Growly",
    "Проверка Telegram-пользователя": "Telegram пайдаланушысын тексеру",
    "Загружаем отчёт": "Есеп жүктелуде",
    "Сформировано Growly": "Growly жасаған",
    "Синхронизирован": "Синхрондалған",
    "Не сохранён": "Сақталмаған",
    "Открыть Notion": "Notion-ды ашу",
    "Вернуться к отчётам": "Есептерге оралу",
    "Главный вывод": "Негізгі қорытынды",
    "Сравнение конкурентов": "Бәсекелестерді салыстыру",
    "Конкурент": "Бәсекелес",
    "Предложение": "Ұсыныс",
    "Цена / ценность": "Баға / құндылық",
    "Сильная сторона": "Күшті жағы",
    "Слабая сторона": "Әлсіз жағы",
    "Возможность": "Мүмкіндік",
    "Не подтверждено": "Расталмаған",
    "Требуется больше данных": "Қосымша дерек қажет",
    "Динамика публикаций": "Жарияланым динамикасы",
    "Повторяющиеся предложения": "Қайталанатын ұсыныстар",
    "Призывы к действию": "Әрекетке шақырулар",
    "Пробелы в контенте": "Контент олқылықтары",
    "Боли аудитории": "Аудитория мәселелері",
    "Рекомендуемое позиционирование": "Ұсынылатын позициялау",
    "Действия на неделю": "Апталық әрекеттер",
    "Идеи контента": "Контент идеялары",
    "Риски и ограничения": "Тәуекелдер мен шектеулер",
    "Полный текст": "Толық мәтін",
    "Загрузка данных": "Деректер жүктелуде",
    "Не удалось загрузить данные": "Деректерді жүктеу мүмкін болмады",
    "Повторить": "Қайталау",
    "Неизвестная ошибка": "Белгісіз қате",
    "Нет данных": "Дерек жоқ",
    "Не синхронизировалось": "Синхрондалмаған",
    "Сервис временно недоступен.": "Сервис уақытша қолжетімсіз.",
    "Не удалось создать черновик. Сервис временно недоступен.":
      "Черновик жасау мүмкін болмады. Сервис уақытша қолжетімсіз.",
    "Задачу не удалось выполнить. Сервис временно недоступен.":
      "Тапсырманы орындау мүмкін болмады. Сервис уақытша қолжетімсіз.",
    "Генерация временно недоступна: лимит AI-сервиса исчерпан. Попробуйте позже.":
      "Генерация уақытша қолжетімсіз: AI сервисінің лимиті бітті. Кейінірек қайталап көріңіз.",
    "Генерация временно недоступна. Попробуйте позже.":
      "Генерация уақытша қолжетімсіз. Кейінірек қайталап көріңіз.",
    "Генерация заняла слишком много времени. Попробуйте ещё раз.":
      "Генерация тым ұзаққа созылды. Қайталап көріңіз.",
    "Активен": "Белсенді",
    "Ожидает анализа": "Талдауды күтуде",
    "Согласован": "Бекітілген",
    "Завершён": "Аяқталған",
    "Отключён": "Өшірілген",
    "Черновик создан": "Нобай жасалды",
    "Готов": "Дайын",
    "Требует проверки": "Тексеруді қажет етеді",
    "Growly сначала сохраняет найденные материалы, затем анализирует их и только после этого формирует план и черновики.":
      "Growly алдымен табылған материалдарды сақтайды, кейін талдап, содан соң жоспар мен нобайлар жасайды.",
    "Growly сначала сохраняет публичные источники, затем формирует выводы и отчёт.":
      "Growly алдымен ашық дереккөздерді сақтайды, кейін қорытынды мен есеп жасайды.",
    "Growly собирает публичные источники, готовит отчёты и помогает вести контент-процесс без разрыва между аналитикой и публикацией.":
      "Growly ашық дереккөздерді жинайды, есептер дайындайды және талдау мен жариялауды бір үдеріске біріктіреді.",
    "Supabase Auth не настроен. В локальном режиме можно открыть интерфейс без авторизации.":
      "Supabase Auth бапталмаған. Жергілікті режимде интерфейсті авторизациясыз ашуға болады.",
    "Supabase Auth не настроен. Вход в рабочую область временно недоступен.":
      "Supabase Auth бапталмаған. Жұмыс кеңістігіне кіру уақытша қолжетімсіз.",
    "Tavily ищет только публично доступные страницы.":
      "Tavily тек ашық қолжетімді беттерді іздейді.",
    "Анализ ещё не запускался. Укажите нишу и регион.":
      "Талдау әлі іске қосылмаған. Ниша мен аймақты көрсетіңіз.",
    "Аналитика, контент и согласование в одной системе.":
      "Талдау, контент және бекіту бір жүйеде.",
    "Быстрый доступ к основным действиям Growly без дублирования бизнес-логики.":
      "Бизнес-логиканы қайталамай Growly әрекеттеріне жылдам қолжетімділік.",
    "Версии материалов, статусы согласования и сохранение в Notion.":
      "Материал нұсқалары, бекіту күйлері және Notion-ға сақтау.",
    "Вести исследование, согласование и отчётность по единой структуре.":
      "Зерттеу, бекіту және есепті бір құрылымда жүргізу.",
    "Войдите, чтобы продолжить работу с источниками, планами и согласованием материалов.":
      "Дереккөздермен, жоспарлармен және материалдарды бекітумен жұмысты жалғастыру үшін кіріңіз.",
    "Выберите действие слева и опишите задачу. Growly вызовет тот же сервисный слой, который используется Telegram-ботом.":
      "Сол жақтан әрекетті таңдап, тапсырманы сипаттаңыз. Growly Telegram-бот қолданатын сервистік қабатты пайдаланады.",
    "Для команд, которым нужен управляемый контент-процесс.":
      "Басқарылатын контент үдерісі қажет командаларға арналған.",
    "Добавьте известный вам официальный источник.":
      "Өзіңіз білетін ресми дереккөзді қосыңыз.",
    "Добавьте известный источник или найдите публичные страницы по нише.":
      "Белгілі дереккөзді қосыңыз немесе ниша бойынша ашық беттерді табыңыз.",
    "Задача выполнена.": "Тапсырма орындалды.",
    "Задачу не удалось выполнить.": "Тапсырманы орындау мүмкін болмады.",
    "Источник добавлен.": "Дереккөз қосылды.",
    "Компактная точка входа, подготовленная для будущего Telegram Mini App.":
      "Болашақ Telegram Mini App үшін дайындалған ықшам кіру беті.",
    "Найдено кандидатов: {count}.": "Табылған үміткерлер: {count}.",
    "Например: доставка здорового питания для офисов":
      "Мысалы: кеңселерге пайдалы тағам жеткізу",
    "Например: объяснить ценность услуги и получить заявки на консультацию":
      "Мысалы: қызмет құндылығын түсіндіріп, кеңеске өтінім алу",
    "Например: спокойно, предметно, без громких обещаний":
      "Мысалы: сабырлы, нақты, асыра уәде бермей",
    "Не удалось войти. Проверьте почту и пароль.":
      "Кіру мүмкін болмады. Пошта мен құпиясөзді тексеріңіз.",
    "Нет черновиков, ожидающих согласования.":
      "Бекітуді күтіп тұрған нобайлар жоқ.",
    "Опишите рынок достаточно конкретно, чтобы поиск не смешивал разные категории.":
      "Іздеу санаттарды араластырмауы үшін нарықты нақты сипаттаңыз.",
    "Отчёт готов. Сохранено источников: {count}.":
      "Есеп дайын. Сақталған дереккөздер: {count}.",
    "Отчёты появятся после анализа рынка, конкурентов или публикаций.":
      "Есептер нарықты, бәсекелестерді немесе жарияланымдарды талдағаннан кейін пайда болады.",
    "План ещё не создан. Сначала подготовьте рыночные данные.":
      "Жоспар әлі жасалмаған. Алдымен нарық деректерін дайындаңыз.",
    "Понять рынок и регулярно готовить материалы без отдельного отдела.":
      "Нарықты түсініп, бөлек бөлімсіз материалдарды тұрақты дайындау.",
    "Последние результаты, состояние данных и быстрые действия.":
      "Соңғы нәтижелер, деректер күйі және жылдам әрекеттер.",
    "Появится после сбора и анализа источников.":
      "Дереккөздерді жинап, талдағаннан кейін пайда болады.",
    "Профиль бизнеса и ссылки на подключённые рабочие пространства.":
      "Бизнес профилі және қосылған жұмыс кеңістіктерінің сілтемелері.",
    "Публичные сайты и каналы, которые Growly использует как рыночные свидетельства.":
      "Growly нарық дәлелі ретінде қолданатын ашық сайттар мен арналар.",
    "Рыночные, конкурентные и результативные отчёты с источниками и ограничениями.":
      "Дереккөздері мен шектеулері бар нарықтық, бәсекелестік және нәтижелік есептер.",
    "Связать анализ предложений с практическими темами и черновиками.":
      "Ұсыныстар талдауын практикалық тақырыптармен және нобайлармен байланыстыру.",
    "Сначала выполните анализ рынка, затем сформируйте цель на неделю.":
      "Алдымен нарықты талдап, кейін апталық мақсатты белгілеңіз.",
    "Собрать наблюдения, аргументы и план в одном рабочем пространстве.":
      "Бақылауларды, дәлелдерді және жоспарды бір жұмыс кеңістігінде жинау.",
    "Сохранено новых материалов: {count}.":
      "Жаңа сақталған материалдар: {count}.",
    "Текущая база Growly использует единую бизнес-область. Supabase Auth управляет входом в веб-интерфейс, но изоляция нескольких компаний требует отдельной миграции данных с полем workspace_id.":
      "Қазіргі Growly базасы бір бизнес кеңістігін қолданады. Supabase Auth вебке кіруді басқарады, ал бірнеше компанияны бөлу үшін workspace_id өрісі бар жеке миграция қажет.",
    "Темы, форматы и задачи на неделю на основе сохранённых источников.":
      "Сақталған дереккөздер негізіндегі апталық тақырыптар, форматтар және тапсырмалар.",
    "Укажите бизнес-цель на неделю. Growly использует последние отчёты и материалы источников.":
      "Апталық бизнес-мақсатты көрсетіңіз. Growly соңғы есептер мен дереккөз материалдарын қолданады.",
    "Укажите нишу и регион. Growly сохранит источники до начала анализа.":
      "Ниша мен аймақты көрсетіңіз. Growly талдауға дейін дереккөздерді сақтайды.",
    "Черновики появятся после генерации поста или создания материала из контент-плана.":
      "Нобайлар жазба генерациясынан немесе контент-жоспардан материал жасағаннан кейін пайда болады.",
    "Эта страница пока использует обычную веб-сессию. При подключении Mini App параметр initData должен проверяться на сервере; данные из initDataUnsafe не используются как доверенный источник.":
      "Бұл бет әзірге кәдімгі веб-сессияны қолданады. Mini App қосылғанда initData серверде тексерілуі тиіс; initDataUnsafe сенімді дереккөз ретінде қолданылмайды.",
    "Эти данные используются при подготовке планов и материалов. Секретные ключи на этой странице не отображаются.":
      "Бұл деректер жоспарлар мен материалдарды дайындауда қолданылады. Құпия кілттер бұл бетте көрсетілмейді.",
    "Отчёт готов: {name}. Откройте раздел «Отчёты» для просмотра.":
      "Есеп дайын: {name}. Көру үшін «Есептер» бөлімін ашыңыз.",
    "Черновик создан: {name}. Он доступен в разделе «Черновики».":
      "Нобай жасалды: {name}. Ол «Нобайлар» бөлімінде қолжетімді.",
    "Готово. Получено элементов: {count}.": "Дайын. Алынған элементтер: {count}.",
    "Синхронизация Notion завершена. Обработано объектов: {count}.":
      "Notion синхрондауы аяқталды. Өңделген нысандар: {count}.",
    "Собирает публичные источники и формирует проверяемый обзор.":
      "Ашық дереккөздерді жинап, тексерілетін шолу жасайды.",
    "Сравнивает предложения, призывы, сильные стороны и рыночные пробелы.":
      "Ұсыныстарды, әрекетке шақыруларды, күшті жақтарды және нарық олқылықтарын салыстырады.",
    "Переводит рыночные наблюдения в темы, форматы и задачи на неделю.":
      "Нарық бақылауларын апталық тақырыптарға, форматтарға және тапсырмаларға айналдырады.",
    "Создаёт посты по брифу и сохраняет версии до согласования.":
      "Бриф бойынша жазба жасап, нұсқаларды бекітуге дейін сақтайды.",
    "Показывает выводы, таблицы, источники, риски и следующие действия.":
      "Қорытындыларды, кестелерді, дереккөздерді, тәуекелдерді және келесі әрекеттерді көрсетеді.",
    "Синхронизирует отчёты, планы, источники и готовые материалы.":
      "Есептерді, жоспарларды, дереккөздерді және дайын материалдарды синхрондайды.",
    "Опишите нишу, продукт и регион": "Ниша, өнім және аймақты сипаттаңыз",
    "Укажите рынок или тему отчёта": "Нарықты немесе есеп тақырыбын көрсетіңіз",
    "Опишите цель на неделю": "Апталық мақсатты сипаттаңыз",
    "Передайте подробный бриф, канал и желаемый призыв":
      "Толық бриф, арна және қажетті әрекетке шақыруды беріңіз",
    "Показать последние черновики": "Соңғы нобайларды көрсету",
    "Показать последние отчёты": "Соңғы есептерді көрсету",
    "Показать сохранённые источники": "Сақталған дереккөздерді көрсету",
    "Синхронизировать последние данные": "Соңғы деректерді синхрондау",
    "Собрать и сохранить публичные источники.":
      "Ашық дереккөздерді жинап, сақтау.",
    "Сформировать недельный план на основе данных.":
      "Деректер негізінде апталық жоспар құру.",
    "Передать бриф и получить черновик.": "Бриф жіберіп, нобай алу.",
    "Запустить новый сбор источников.": "Дереккөздерді жаңадан жинауды бастау.",
    "Проверить материалы на согласовании.": "Бекітудегі материалдарды тексеру.",
    "Открыть последние результаты.": "Соңғы нәтижелерді ашу.",
    "Опубликован": "Жарияланған",
    "Отклонён": "Қабылданбаған",
    "Последний анализ": "Соңғы талдау",
    "Последний анализ: {topic}. Источников: {count}. Что хотите сделать дальше?":
      "Соңғы талдау: {topic}. Дереккөздер: {count}. Әрі қарай не істегіңіз келеді?",
    "Спросите по последнему анализу или выберите действие":
      "Соңғы талдау бойынша сұраңыз немесе әрекетті таңдаңыз",
    "анализ рынка": "нарық талдауы",
    "последний анализ рынка": "соңғы нарық талдауы",
    "Показать идеи": "Идеяларды көрсету",
    "Сформировать конкурентный отчёт": "Бәсекелестер есебін құру",
    "Сохранено в Notion": "Notion-ға сақталды",
    "План будет создан на основе анализа: {topic}":
      "Жоспар талдау негізінде құрылады: {topic}",
    "Изменить источник": "Дереккөзді өзгерту",
    "Контент-план по нише: {topic}": "{topic} нишасы бойынша контент-жоспар",
    "Контент": "Контент",
    "Подготовьте пост на основе анализа, контент-плана или вручную.":
      "Талдау, контент-жоспар негізінде немесе қолмен жазба дайындаңыз.",
    "Создать пост по последнему анализу": "Соңғы талдау бойынша жазба жасау",
    "На основе анализа: {topic}": "Талдау негізінде: {topic}",
    "Сначала выполните анализ рынка.": "Алдымен нарық талдауын жасаңыз.",
    "Создать пост из контент-плана": "Контент-жоспардан жазба жасау",
    "Откройте план и создайте черновик из выбранной темы.":
      "Жоспарды ашып, таңдалған тақырыптан нобай жасаңыз.",
    "Контент-план ещё не создан.": "Контент-жоспар әлі жасалмаған.",
    "Создать вручную": "Қолмен жасау",
    "Передайте свой бриф и канал.": "Брифіңіз бен арнаңызды беріңіз.",
    "Бриф": "Бриф",
    "Формируем пост": "Жазба құрылуда",
    "Формируем пост на сервере...": "Жазба серверде құрылуда...",
    "Опишите задачу подробнее (минимум 10 символов).":
      "Тапсырманы толығырақ сипаттаңыз (кемінде 10 таңба).",
    "Создай продающий пост для канала {channel} на основе последнего анализа рынка. Ниша: {topic}{region}. Используй боли клиентов и офферы из анализа, добавь конкретный призыв к действию.":
      "{channel} арнасына соңғы нарық талдауы негізінде сатылымдық жазба жаз. Ниша: {topic}{region}. Талдаудағы клиент мәселелері мен ұсыныстарды қолданып, нақты әрекетке шақыру қос.",
    "Открыть": "Ашу",
    "Открываем": "Ашудамыз",
    "Конкуренты / источники": "Бәсекелестер / дереккөздер",
    "Повторяющиеся призывы": "Қайталанатын шақырулар",
    "Доминирующие темы": "Басым тақырыптар",
    "Возражения": "Қарсылықтар",
    "Что сделать на этой неделе": "Осы аптада не істеу керек",
    "Боли клиентов": "Клиент мәселелері",
    "Повторяющиеся офферы": "Қайталанатын офферлер",
    "Контентные пробелы": "Контент олқылықтары",
    "Спросите по выбранному отчёту или выберите действие":
      "Таңдалған есеп бойынша сұраңыз немесе әрекетті таңдаңыз",
    "Сначала выберите отчёт или опишите нишу, продукт и регион":
      "Алдымен есепті таңдаңыз немесе ниша, өнім және аймақты сипаттаңыз",
    "Выбор отчёта": "Есепті таңдау",
    "Пока нет отчётов. Сначала запустите анализ рынка.":
      "Әзірге есептер жоқ. Алдымен нарық талдауын бастаңыз.",
    "Использовать этот отчёт": "Осы есепті пайдалану",
    "Не удалось загрузить данные. Попробуйте ещё раз или выберите другой отчёт.":
      "Деректерді жүктеу мүмкін болмады. Қайталап көріңіз немесе басқа есепті таңдаңыз.",
    "Технические детали": "Техникалық мәліметтер",
    "Готовим варианты по отчёту": "Есеп бойынша нұсқалар дайындалуда",
    "Контент-план создан.": "Контент-жоспар жасалды.",
    "Открыть контент-план": "Контент-жоспарды ашу",
    "Сохранённый контент-план": "Сақталған контент-жоспар",
    "Тем в последнем плане: {count}": "Соңғы жоспардағы тақырыптар: {count}",
    "Аудитория": "Аудитория",
    "Оффер": "Оффер",
    "Каналы": "Арналар",
    "Форматы": "Форматтар",
    "Призыв к действию": "Әрекетке шақыру",
    "Дополнительные пожелания": "Қосымша тілектер",
    "Например: спокойный тон, без громких обещаний":
      "Мысалы: сабырлы үн, асыра уәдесіз",
    "Или впишите своё": "Немесе өзіңіздікін жазыңыз",
    "Источников: {count}": "Дереккөздер: {count}",
    "Отчёт": "Есеп",
    "План будет создан на основе отчёта": "Жоспар есеп негізінде құрылады",
    "Изменить отчёт": "Есепті өзгерту",
    "Выберите отчёт, на основе которого создать контент-план":
      "Контент-жоспар құрылатын есепті таңдаңыз",
    "Создать без отчёта": "Есепсіз жасау",
    "Назад к выбору отчёта": "Есепті таңдауға оралу",
    "Чат работает с отчётом «{topic}». Задайте вопрос или выберите действие.":
      "Чат «{topic}» есебімен жұмыс істейді. Сұрақ қойыңыз немесе әрекетті таңдаңыз.",
    "Опишите нишу, продукт и регион — или вернитесь и выберите отчёт.":
      "Ниша, өнім және аймақты сипаттаңыз — немесе оралып, есепті таңдаңыз.",
    "отчёт": "есеп",
    "Выберите отчёт, с которым будет работать чат":
      "Чат жұмыс істейтін есепті таңдаңыз",
    "Продолжить без отчёта": "Есепсіз жалғастыру",
    "Чат работает с отчётом": "Чат есеппен жұмыс істейді",
    "Показать идеи постов": "Жазба идеяларын көрсету",
    "Идеи постов": "Жазба идеялары",
    "Разобрать конкурентов": "Бәсекелестерді талдау",
    "Вопрос по отчёту": "Есеп бойынша сұрақ",
    "Использовать для контент-плана": "Контент-жоспар үшін пайдалану",
    "Использовать в чате": "Чатта пайдалану",
    "Не удалось выбрать отчёт. Попробуйте ещё раз.":
      "Есепті таңдау мүмкін болмады. Қайталап көріңіз.",
    "Выбрать другой отчёт": "Басқа есепті таңдау",
    "Загружаю контекст отчёта…": "Есеп контексі жүктелуде…",
    "Готовлю варианты для контент-плана…":
      "Контент-жоспар нұсқалары дайындалуда…",
    "Показаны базовые варианты по теме отчёта.":
      "Есеп тақырыбы бойынша негізгі нұсқалар көрсетілді.",
    "Обновить": "Жаңарту",
    "Я работаю с отчётом «{topic}». Выберите действие или задайте вопрос по этому рынку.":
      "Мен «{topic}» есебімен жұмыс істеймін. Әрекетті таңдаңыз немесе осы нарық бойынша сұрақ қойыңыз.",
    "Выберите быстрое действие выше или задайте вопрос ниже.":
      "Жоғарыдан жылдам әрекетті таңдаңыз немесе төменде сұрақ қойыңыз.",
    "Шаг {step}": "{step}-қадам",
    "Что должен сделать контент на этой неделе?":
      "Осы аптада контент нені орындау керек?",
    "Для кого создаём контент?": "Контент кімге арналған?",
    "Что продвигаем?": "Нені жылжытамыз?",
    "Где публикуем?": "Қайда жариялаймыз?",
    "Какое действие должен совершить клиент?":
      "Клиент қандай әрекет жасауы керек?",
    "Дополнительная инструкция (необязательно)":
      "Қосымша нұсқау (міндетті емес)",
    "Свой вариант": "Өз нұсқаңыз",
    "Все каналы": "Барлық арналар",
    "Создание": "Жасау",
    "CTA": "CTA",
    "Сохранить как черновик": "Нобай ретінде сақтау",
    "Черновик сохранён.": "Нобай сақталды.",
    "Обновить варианты": "Нұсқаларды жаңарту",
    "Показали базовые варианты. Можно обновить или вписать свой вариант.":
      "Негізгі нұсқалар көрсетілді. Жаңартуға немесе өз нұсқаңызды жазуға болады.",
    "Варианты подготовлены на основе выбранного отчёта.":
      "Нұсқалар таңдалған есеп негізінде дайындалды.",
    "Подключено": "Қосылған",
    "Не подключено": "Қосылмаған",
    "да": "иә",
    "нет": "жоқ",
    "Проверяем": "Тексерудеміз",
    "Обновляем": "Жаңартудамыз",
    "Готовим": "Дайындаудамыз",
    "Отправляем": "Жіберудеміз",
    "Интеграции": "Интеграциялар",
    "Подключения Growly: Telegram, Notion и автопубликация в соцсети.":
      "Growly қосылымдары: Telegram, Notion және әлеуметтік желіге автожариялау.",
    "Назад к настройкам": "Баптауларға оралу",
    "Канал публикации не указан.": "Жариялау арнасы көрсетілмеген.",
    "Проверить публикацию": "Жариялауды тексеру",
    "Корневая страница настроена.": "Түбірлік бет бапталған.",
    "Корневая страница не настроена.": "Түбірлік бет бапталмаған.",
    "Проверить синхронизацию": "Синхрондауды тексеру",
    "API-ключ настроен": "API кілті бапталған",
    "Аккаунтов подключено": "Қосылған аккаунттар",
    "Проверить подключение": "Қосылымды тексеру",
    "Обновить аккаунты": "Аккаунттарды жаңарту",
    "Настроить публикацию": "Жариялауды баптау",
    "Социальные сети": "Әлеуметтік желілер",
    "Подключённые аккаунты": "Қосылған аккаунттар",
    "Обновить список аккаунтов": "Аккаунттар тізімін жаңарту",
    "Автопубликация не подключена. Growly может подготовить пакет для ручной публикации.":
      "Автожариялау қосылмаған. Growly қолмен жариялау пакетін дайындай алады.",
    "Нет подключённого аккаунта.": "Қосылған аккаунт жоқ.",
    "Список аккаунтов обновлён.": "Аккаунттар тізімі жаңартылды.",
    "Blotato подключён": "Blotato қосылды",
    "Интеграции и публикация": "Интеграциялар және жариялау",
    "Telegram, Notion и автопубликация в соцсети через Blotato.":
      "Telegram, Notion және Blotato арқылы әлеуметтік желіге автожариялау.",
    "Открыть интеграции": "Интеграцияларды ашу",
    "Администрирование": "Әкімшілік",
    "Настройка публикации": "Жариялауды баптау",
    "Сопоставьте аккаунты Blotato с платформами Growly.":
      "Blotato аккаунттарын Growly платформаларымен сәйкестендіріңіз.",
    "Назад к интеграциям": "Интеграцияларға оралу",
    "Чек-лист подключения": "Қосылу тізімі",
    "Добавьте BLOTATO_API_KEY в секреты бэкенда":
      "BLOTATO_API_KEY кілтін бэкенд құпияларына қосыңыз",
    "Подключите аккаунты в Blotato": "Blotato-да аккаунттарды қосыңыз",
    "Обновите аккаунты в Growly": "Growly-де аккаунттарды жаңартыңыз",
    "Сопоставьте аккаунты с платформами": "Аккаунттарды платформалармен сәйкестендіріңіз",
    "Проверьте публикацию": "Жариялауды тексеріңіз",
    "API-ключ хранится только в секретах бэкенда и не отображается в интерфейсе.":
      "API кілті тек бэкенд құпияларында сақталады және интерфейсте көрсетілмейді.",
    "Сопоставление платформ": "Платформаларды сәйкестендіру",
    "Аккаунты не найдены. Подключите их в Blotato и обновите список.":
      "Аккаунттар табылмады. Оларды Blotato-да қосып, тізімді жаңартыңыз.",
    "Не публиковать": "Жарияламау",
    "Сохранить сопоставление": "Сәйкестендіруді сақтау",
    "Сопоставление аккаунтов сохранено.": "Аккаунттарды сәйкестендіру сақталды.",
    "Загружаем черновик": "Нобай жүктелуде",
    "Публикация": "Жариялау",
    "Через Telegram-бота": "Telegram-бот арқылы",
    "Нет аккаунта": "Аккаунт жоқ",
    "Опубликовать сейчас": "Қазір жариялау",
    "Запланировать": "Жоспарлау",
    "Пакет для ручной публикации": "Қолмен жариялау пакеті",
    "Дата и время публикации": "Жариялау күні мен уақыты",
    "Черновик пуст — публикация недоступна.": "Нобай бос — жариялау қолжетімсіз.",
    "Подготовить пакет для ручной публикации": "Қолмен жариялау пакетін дайындау",
    "Открыть пост": "Жазбаны ашу",
    "Открыть и опубликовать": "Ашып, жариялау",
    "Хук": "Хук",
    "Текст": "Мәтін",
    "Сценарий": "Сценарий",
    "Визуал": "Визуал",
    "Хэштеги": "Хэштегтер",
    "Отправлено": "Жіберілді",
    "Запланировано": "Жоспарланды",
    "Пропущено": "Өткізілді",
    "Не поддерживается": "Қолдау көрсетілмейді",
    "Blotato не подключён. Автопубликация в соцсети временно недоступна.":
      "Blotato қосылмаған. Әлеуметтік желіге автожариялау уақытша қолжетімсіз.",
    "Для выбранной платформы не выбран аккаунт публикации.":
      "Таңдалған платформа үшін жариялау аккаунты таңдалмаған.",
    "Не удалось отправить публикацию.": "Жарияланымды жіберу мүмкін болмады.",
    "Эта платформа пока не поддерживается для автопубликации.":
      "Бұл платформа автожариялау үшін әзірге қолдау көрсетпейді.",
    "Не удалось подготовить безопасный текст поста. Измените бриф или попробуйте ещё раз.":
      "Қауіпсіз жазба мәтінін дайындау мүмкін болмады. Брифті өзгертіп немесе қайталап көріңіз.",
    "Текст публикации": "Жарияланым мәтіні",
    "{count} слов": "{count} сөз",
    "Оптимально до 125–150 слов для поста.":
      "Жазбаға 125–150 сөз оңтайлы.",
    "Preview": "Алдын ала қарау",
    "Добавьте изображение или видео для Instagram":
      "Instagram үшін сурет немесе бейне қосыңыз",
    "Куда публикуем": "Қайда жариялаймыз",
    "Недоступные каналы ({count})": "Қолжетімсіз арналар ({count})",
    "Настроить интеграции": "Интеграцияларды баптау",
    "Когда публиковать": "Қашан жариялау",
    "Пост уйдёт в выбранные соцсети сразу.":
      "Жазба таңдалған желілерге бірден жіберіледі.",
    "Выберите дату и время публикации.":
      "Жариялау күні мен уақытын таңдаңыз.",
    "Готовый текст и медиа для ручного постинга.":
      "Қолмен жариялауға дайын мәтін мен медиа.",
    "Тип медиа": "Медиа түрі",
    "Загрузить фото/видео": "Фото/бейне жүктеу",
    "AI-генерация медиа": "AI медиа генерациясы",
    "Показать все {count}": "Барлығын көрсету ({count})",
    "Свернуть": "Жию",
    "Время указывается в вашем часовом поясе.":
      "Уақыт сіздің сағаттық белдеуіңізде көрсетіледі.",
    "История и статус": "Тарих және күй",
    "Обновлён": "Жаңартылды",
    "Версия": "Нұсқа",
    "Создан из контент-плана": "Контент-жоспардан жасалды",
    "Подготовить пакет": "Топтаманы дайындау",
    "Выберите хотя бы один канал.": "Кемінде бір арна таңдаңыз.",
    "Укажите дату и время публикации.":
      "Жариялау күні мен уақытын көрсетіңіз.",
    "Пост опубликован": "Жазба жарияланды",
    "Пост запланирован": "Жазба жоспарланды",
    "Не удалось опубликовать": "Жариялау мүмкін болмады",
    "Пакет готов": "Топтама дайын",
    "Не удалось подготовить пакет": "Топтаманы дайындау мүмкін болмады",
    "Не удалось загрузить черновик. Попробуйте обновить страницу.":
      "Жобаны жүктеу мүмкін болмады. Бетті жаңартып көріңіз.",
    "Задачи": "Тапсырмалар",
    "Что нужно сделать команде: ответственные, сроки и статусы.":
      "Команда не істеу керек: жауаптылар, мерзімдер және күйлер.",
    "Команда": "Команда",
    "Участники этого workspace и их роли.":
      "Осы workspace қатысушылары және олардың рөлдері.",
    "Поделиться с командой": "Командамен бөлісу",
    "Участники": "Қатысушылар",
    "Роль": "Рөл",
    "Присоединился": "Қосылды",
    "Приглашён": "Шақырылды",
    "Удалить участника": "Қатысушыны жою",
    "Приглашения": "Шақырулар",
    "Ожидает": "Күтуде",
    "Отменить приглашение": "Шақыруды болдырмау",
    "Notion используется как внутренний инструмент синхронизации и не является публичным кабинетом клиента.":
      "Notion ішкі синхрондау құралы ретінде қолданылады, клиенттің ашық кабинеті емес.",
    "Владелец": "Иесі",
    "Только просмотр": "Тек қарау",
    "Редактор": "Редактор",
    "Пригласить участника": "Қатысушыны шақыру",
    "Скопируйте ссылку и отправьте её участнику ({email}).":
      "Сілтемені көшіріп, {email} мекенжайына жіберіңіз.",
    "Приглашение создано": "Шақыру жасалды",
    "Приглашение отправлено на {email}.": "Шақыру {email} мекенжайына жіберілді.",
    "Можно также скопировать ссылку и отправить вручную.":
      "Сілтемені көшіріп, қолмен жіберуге де болады.",
    "Скопировать ссылку": "Сілтемені көшіру",
    "Скопировано": "Көшірілді",
    "Сообщение (необязательно)": "Хабарлама (міндетті емес)",
    "Отмена": "Болдырмау",
    "Отправить приглашение": "Шақыру жіберу",
    "Не удалось скопировать ссылку": "Сілтемені көшіру мүмкін болмады",
    "Приглашение в Growly": "Growly-ге шақыру",
    "Присоединяйтесь к команде": "Командаға қосылыңыз",
    "Вас пригласили работать с отчётами, контент-планом и черновиками внутри Growly.":
      "Сізді Growly ішіндегі есептермен, контент-жоспармен және жобалармен жұмыс істеуге шақырды.",
    "Приглашение": "Шақыру",
    "Приглашение истекло. Попросите владельца отправить новое.":
      "Шақыру мерзімі бітті. Иесінен жаңасын жіберуді сұраңыз.",
    "Приглашение больше недействительно.":
      "Бұл шақыру енді жарамсыз.",
    "Войдите или зарегистрируйтесь, чтобы принять приглашение.":
      "Шақыруды қабылдау үшін кіріңіз немесе тіркеліңіз.",
    "Принять приглашение": "Шақыруды қабылдау",
    "Принимаем": "Қабылдаудамыз",
    "Скопировать ссылку для просмотра": "Қарауға арналған сілтемені көшіру",
    "Ссылка защищена паролем": "Сілтеме құпиясөзбен қорғалған",
    "Ссылка недоступна.": "Сілтеме қолжетімсіз.",
    "Просмотр только для чтения · Growly": "Тек оқуға арналған · Growly",
    "Что делать дальше": "Әрі қарай не істеу керек",
    "Без срока": "Мерзімсіз",
    "Задач пока нет.": "Әзірге тапсырма жоқ.",
    "Что нужно сделать?": "Не істеу керек?",
    "Ответственный (email)": "Жауапты (email)",
    "Срок": "Мерзімі",
    "Приоритет": "Басымдық",
    "Создать задачу": "Тапсырма жасау",
    "Изменить статус": "Күйін өзгерту",
    "Удалить": "Жою",
    "К выполнению": "Орындауға",
    "В работе": "Жұмыста",
    "Готово": "Дайын",
    "Запущено": "Іске қосылды",
    "Нужно действие": "Әрекет қажет",
    "Отменено": "Болдырылмады",
    "Низкий": "Төмен",
    "Средний": "Орташа",
    "Высокий": "Жоғары",
  },
};

function interpolate(value: string, variables?: Variables): string {
  if (!variables) return value;
  return Object.entries(variables).reduce(
    (text, [key, replacement]) =>
      text.replaceAll(`{${key}}`, String(replacement)),
    value,
  );
}

export function translate(
  locale: Locale,
  source: string,
  variables?: Variables,
): string {
  return interpolate(
    locale === "ru" ? source : translations[locale][source] || source,
    variables,
  );
}

type LanguageContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (source: string, variables?: Variables) => string;
};

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("ru");

  useEffect(() => {
    const stored = window.localStorage.getItem("growly_locale");
    const browser = navigator.language.toLowerCase().split("-")[0];
    const next: Locale =
      stored === "ru" || stored === "en" || stored === "kk"
        ? stored
        : browser === "en" || browser === "kk"
          ? browser
          : "ru";
    setLocaleState(next);
    document.documentElement.lang = next;
  }, []);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    window.localStorage.setItem("growly_locale", next);
    document.cookie = `growly_locale=${next}; path=/; max-age=31536000; samesite=lax`;
    document.documentElement.lang = next;
  }, []);

  const t = useCallback(
    (source: string, variables?: Variables) =>
      translate(locale, source, variables),
    [locale],
  );

  const value = useMemo(
    () => ({ locale, setLocale, t }),
    [locale, setLocale, t],
  );

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage(): LanguageContextValue {
  const value = useContext(LanguageContext);
  if (!value) throw new Error("useLanguage requires LanguageProvider");
  return value;
}

export function localeTag(locale: Locale): string {
  return locale === "en" ? "en-US" : locale === "kk" ? "kk-KZ" : "ru-RU";
}
