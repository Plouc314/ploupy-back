## Dev

### ploupy-back
* Run `maturin develop` in `/game_logic`
* Run `gunicorn -w 1 -k uvicorn.workers.UvicornWorker src.api.api:app -b :5000`
* Run `gunicorn -w 1 -k uvicorn.workers.UvicornWorker src.sio.main:app`

### ploupy-front
* Run `npm run dev`