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