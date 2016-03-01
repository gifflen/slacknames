FROM ubuntu

ENV APP_DIR /usr/local/bin/my_app

ENV SLACK_TOKEN null

RUN apt-get update
RUN apt-get install -y python python-pip zlib1g-dev libjpeg-dev #zlib-devel libjpeg-devel
RUN apt-get install -y python-dev

RUN pip install -U pip setuptools

COPY . ${APP_DIR}
WORKDIR ${APP_DIR}

RUN pip install -r requirements.txt

CMD ["python", "rtmbot.py"]