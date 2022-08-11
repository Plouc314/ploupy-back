# step 1: compile rust code
FROM konstin2/maturin AS build_rust

RUN pip3 install maturin

# add rust source code
ADD ./game_logic /opt/build/
WORKDIR /opt/build

# compile in release mode for ONLY python3.10
RUN maturin build --interpreter $(which python3.10) --release

# step 2: sio
FROM python:3.10

# install dependecies
ADD requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt

# add python source code
ADD ./src /opt/webapp/src
WORKDIR /opt/webapp

# copy previously created wheel
COPY --from=build_rust /opt/build/target/wheels ./

# install wheel as dependency
RUN pip3 install $(ls | grep *.whl)

# set rust logger level
ENV RUST_LOG="WARN"
# this enable output from python code
ENV PYTHONUNBUFFERED=1

# add user (cause recommended in doc)
RUN useradd -m myuser
USER myuser

CMD gunicorn -w 1 -k uvicorn.workers.UvicornWorker src.sio.main:app --bind 0.0.0.0:$PORT