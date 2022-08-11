## Dev deploy

### ploupy-back
* Run `maturin develop` in `/game_logic`
* Run `gunicorn -w 1 -k uvicorn.workers.UvicornWorker src.api.api:app -b :5000`
* Run `gunicorn -w 1 -k uvicorn.workers.UvicornWorker src.sio.main:app`

#### Docker
> Use docker for **sio** server
* Run `docker build -t ploupy-sio .`
* Run `docker run --network="host" -p 8000:8000 -e PORT=8000 -t ploupy-sio`

### ploupy-front
* Run `npm run dev`