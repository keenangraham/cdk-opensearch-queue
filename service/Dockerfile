FROM --platform=linux/x86_64 python:3.9.9-slim-buster

ENV PYTHONDONTWRITEBYTECODE 1

ENV PYTHONUNBUFFERED 1

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY command.py command.py

EXPOSE 8000

CMD ["uvicorn", "command:app", "--host", "0.0.0.0", "--port", "8000"]