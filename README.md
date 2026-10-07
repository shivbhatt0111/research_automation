# Run Server

python manage.py runserver

# Restart Celery Worker

celery -A config worker -l info --pool=threads --concurrency=20

# Check Task Status

Use the task_id received in the API response:

curl http://localhost:8000/api/research/id/status/

Replace X with the actual task_id.

# Get Food Data

To retrieve food-related data:

curl "http://localhost:8000/api/data/?industry=food"

# Get Restaurant Data

To retrieve restaurant-related data:

curl "http://localhost:8000/api/data/?industry=restaurant"

# Get Statistics

To get statistics for both food and restaurant data:

curl "http://localhost:8000/api/data/stats/"







# part 2 
# Terminal 1: Redis (Start Redis if it is not already running)
redis-server

# Terminal 2: Celery Worker (Processes background tasks)
celery -A config worker -l info --pool=threads --concurrency=20

# Terminal 3: Celery Beat (Scheduler - Required for scheduled tasks)
celery -A config beat -l info

# Terminal 4: Django Development Server
python manage.py runserver






research_automation/
│
├── research/                 # Aapka main Django app
│   ├── templates/            # HTML files yahan aayengi
│   │   ── index.html        # Ye hamara main Homepage (SPA Shell) hoga
│   │
│   ├── static/               # CSS, JS, Images yahan aayengi
│   │   ├── css/
│   │   │   └── custom.css    # Custom styles
│   │   ├── js/
│   │   │   ├── app.js        # Main logic
│   │   │   ├── api.js        # API calls (Fetch)
│   │   │   └── components/   # UI ke alag-alag hisse
│   │   │       ├── navbar.js
│   │   │       └── home.js
│   │   └── images/           # Logos, icons
│   │
│   ├── views.py              # Yahan se index.html render hoga
│   ├── urls.py               # Homepage ka URL yahan set hoga
│   └── ... (baaki files)
│
├── config/
└── manage.py