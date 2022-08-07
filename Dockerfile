FROM python:3.10-alpine3.16

RUN apk add --no-cache \
    gcc \
    libc-dev \
    libffi-dev 

WORKDIR /usr/src/app

COPY ./app .

COPY ./app/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH=/usr/src

CMD [ "python", "main.py" ]
