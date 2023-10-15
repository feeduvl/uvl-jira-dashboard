FROM python:3.8

WORKDIR /app

COPY requirements.txt requirements.txt

RUN python -m spacy download en_core_web_sm

RUN pip install -r requirements.txt

COPY . .

CMD ["python", "app.py", "--host", "0.0.0.0", "--port", "9647"]
