FROM python:3.13.2-alpine

WORKDIR /usr/app/src

COPY requirements.txt ./

RUN apk update && apk add --no-cache \
    bash \
    chromium \
    chromium-chromedriver \
    build-base \
    musl-dev

RUN pip install -r requirements.txt

COPY ./backend .

CMD ["python" "main.py"]