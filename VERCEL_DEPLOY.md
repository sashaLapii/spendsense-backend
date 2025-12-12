# Развертывание SpendSense Backend на Vercel

## Пошаговая инструкция

### 1. Подготовка проекта

1. **Создайте новый репозиторий на GitHub:**
   - Зайдите на github.com
   - Создайте новый репозиторий (например, `spendsense-backend`)
   - Сделайте его публичным или приватным

2. **Загрузите файлы бэкенда:**
   ```bash
   # Создайте новую папку для проекта
   mkdir spendsense-backend
   cd spendsense-backend
   
   # Инициализируйте git
   git init
   
   # Скопируйте все файлы из папки backend/ в корень проекта:
   # - vercel.json
   # - requirements.txt
   # - api/index.py
   # - api/unified_parser.py
   # - api/excel_writer.py
   # - api/csv_writer.py
   ```

### 2. Структура проекта для Vercel

Ваша структура должна выглядеть так:
```
spendsense-backend/
├── vercel.json
├── requirements.txt
├── api/
│   ├── index.py
│   ├── unified_parser.py
│   ├── excel_writer.py
│   └── csv_writer.py
└── README.md
```

### 3. Загрузка на GitHub

```bash
# Добавьте файлы
git add .
git commit -m "Initial commit: SpendSense backend for Vercel"

# Подключите к GitHub репозиторию
git remote add origin https://github.com/YOUR_USERNAME/spendsense-backend.git
git branch -M main
git push -u origin main
```

### 4. Развертывание на Vercel

1. **Зайдите на vercel.com:**
   - Войдите через GitHub аккаунт
   - Нажмите "New Project"

2. **Импортируйте репозиторий:**
   - Выберите ваш `spendsense-backend` репозиторий
   - Нажмите "Import"

3. **Настройте проект:**
   - **Project Name:** `spendsense-backend` (или любое другое имя)
   - **Framework Preset:** Other
   - **Root Directory:** `.` (корень)
   - Нажмите "Deploy"

4. **Дождитесь развертывания:**
   - Vercel автоматически установит зависимости
   - Процесс займет 2-3 минуты

### 5. Получите URL API

После успешного развертывания вы получите URL вида:
```
https://spendsense-backend.vercel.app
```

### 6. Обновите фронтенд

В файле `src/lib/api.ts` замените:
```typescript
const API_BASE = process.env.NODE_ENV === 'production' 
  ? 'https://your-vercel-app.vercel.app/api' 
  : 'http://localhost:8000/api';
```

На:
```typescript
const API_BASE = process.env.NODE_ENV === 'production' 
  ? 'https://spendsense-backend.vercel.app/api' 
  : 'http://localhost:8000/api';
```

### 7. Тестирование

1. **Проверьте API:**
   - Откройте `https://your-app.vercel.app/api/health`
   - Должен вернуть: `{"status":"healthy","service":"SpendSense Web API"}`

2. **Опубликуйте обновленный фронтенд:**
   - Пересоберите фронтенд с новым API URL
   - Опубликуйте на MGX или другой платформе

## Важные моменты

### Ограничения Vercel
- **Время выполнения:** максимум 60 секунд на запрос
- **Размер файла:** до 50MB для загрузки
- **Память:** ограничена для бесплатного плана

### Безопасность
- Файлы автоматически удаляются после обработки
- Сессии хранятся в памяти (сбрасываются при перезапуске)
- CORS настроен для работы с любыми доменами

### Мониторинг
- Логи доступны в панели Vercel
- Можно отслеживать использование и ошибки
- Автоматические уведомления о проблемах

## Альтернативные платформы

Если Vercel не подходит, можно использовать:
- **Railway:** railway.app
- **Render:** render.com  
- **Heroku:** heroku.com
- **DigitalOcean App Platform:** digitalocean.com

## Поддержка

При возникновении проблем:
1. Проверьте логи в панели Vercel
2. Убедитесь, что все файлы загружены правильно
3. Проверьте CORS настройки
4. Тестируйте API эндпоинты отдельно