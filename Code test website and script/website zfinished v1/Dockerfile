# Use the official Python base image
FROM python:3.8.10

# Set the working directory
WORKDIR /app

# Copy the project files
COPY myproject .

# Install project dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the Django development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]