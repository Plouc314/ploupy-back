FROM python:3.10

# install dependecies
ADD requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt

# add python source code
ADD ./src /opt/webapp/src
WORKDIR /opt/webapp

# this enable output from python code
ENV PYTHONUNBUFFERED=1

# add user (cause recommended in doc)
RUN useradd -m myuser
USER myuser

CMD gunicorn -w 1 -k uvicorn.workers.UvicornWorker src.api.api:app --bind 0.0.0.0:$PORT