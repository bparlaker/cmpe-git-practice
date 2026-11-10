# The Docker image for my project (NFR-5).
FROM python:3.12-slim

# Python prints logs right away and does not write .pyc files.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# I copy requirements.txt first, so Docker can reuse this layer when only my
# code changes and the packages stay the same.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Prepare the database, then start the development server.
CMD ["sh", "-c", "python manage.py migrate && python manage.py load_initial_data && python manage.py runserver 0.0.0.0:8000"]
