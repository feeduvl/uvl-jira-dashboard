FROM python:3.8

WORKDIR /app

RUN apt-get update && apt-get install -y \
    python3-dev \
    git \

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm

COPY . .

CMD ["python", "app.py", "--host", "0.0.0.0", "--port", "9647"]
