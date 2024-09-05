FROM python:3.8

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpython3-dev \
    build-essential \
    cython3 \
    python3-pip \
    python3-dev

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir --upgrade pip --prefer-binary -r requirements.txt
RUN python -m spacy download en_core_web_sm

COPY . .

CMD ["python", "app.py", "--host", "0.0.0.0", "--port", "9647"]
