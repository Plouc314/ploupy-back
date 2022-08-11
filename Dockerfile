# first compile rust code into a wheel
FROM konstin2/maturin AS build_rust

RUN pip3 install maturin

ADD ./game_logic /opt/build/
WORKDIR /opt/build

RUN maturin build --interpreter $(which python3.10) --release

FROM python:3.10

ADD requirements.txt /tmp/requirements.txt

RUN pip3 install -r /tmp/requirements.txt

ADD ./src /opt/webapp/src
WORKDIR /opt/webapp

ADD ./.env /opt/webapp/

COPY --from=build_rust /opt/build/target/wheels ./

RUN pip3 install $(ls | grep *.whl)

ENV RUST_LOG="WARN"

RUN useradd -m myuser
USER myuser

CMD gunicorn -w 1 -k uvicorn.workers.UvicornWorker src.sio.main:app --bind 0.0.0.0:$PORT