These are one-time setup commands — run them on every new environment (your laptop, your friend's laptop, Render):

# 1. install dependencies
pip install django djangorestframework djangorestframework-simplejwt django-cors-headers cloudinary django-cloudinary-storage python-dotenv gunicorn django-q2 easyocr opencv-python numpy pillow pillow-heif psycopg2-binary

# 2. apply database migrations (Do commands per model change)
python manage.py makemigrations
python manage.py migrate

# 3. create superadmin account
python manage.py createsuperuser

# 4. set up the OCR validation schedule
python manage.py setup_schedule

Commands to run every time to start the project:
# terminal 1 — web server
python manage.py runserver

# terminal 2 — background worker
python manage.py qcluster
