FROM python:3.8.10

WORKDIR /app
COPY myproject .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "myproject/manage.py", "runserver"]

