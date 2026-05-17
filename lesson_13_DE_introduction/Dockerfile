FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY lesson_13_DE_introduction_hometask.py .

CMD ["python", "lesson_13_DE_introduction_hometask.py"]