FROM python:3.10

ADD requirements.txt /tmp/requirements.txt

RUN pip3 install -r /tmp/requirements.txt

ADD ./src /opt/webapp/src
WORKDIR /opt/webapp

ENV PYTHONUNBUFFERED=1

RUN useradd -m myuser
USER myuser

CMD gunicorn -w 1 -k uvicorn.workers.UvicornWorker src.api.api:app --bind 0.0.0.0:$PORT