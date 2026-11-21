# Dockerfile - recipe that packages the Notes API into an image.

# Start from a small official Python image.
FROM python:3.12-slim

# All following commands run inside /app in the container.
WORKDIR /app

# Copy requirements first so Docker can cache the install layer when only code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code.
COPY app.py .

# Document that the app listens on port 5000.
EXPOSE 5000

# Command that starts the backend when the container runs.
CMD ["python", "app.py"]
