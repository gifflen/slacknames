FROM frolvlad/alpine-glibc

ENV APP_DIR /usr/local/bin/my_app

ENV SLACK_TOKEN null

RUN apk add --update \
    python \
    py-pip \
    openssl && \
    rm -rf /var/cache/apk/*

COPY . ${APP_DIR}
WORKDIR ${APP_DIR}

RUN pip install -r requirements.txt

CMD ["python", "rtmbot.py"]