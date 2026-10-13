"""API de exemplo para demonstrar Docker e Kubernetes.

Endpoints:
  GET  /          mensagem de boas-vindas
  GET  /info      mostra o hostname (nome do pod) e o ambiente
  POST /visitas   incrementa um contador compartilhado no Redis
  GET  /visitas   lê o contador
  GET  /saude     liveness probe  (o processo está vivo?)
  GET  /pronto    readiness probe (o Redis está acessível?)
"""
import os
import socket

import redis
from fastapi import Depends, FastAPI, HTTPException

VERSAO = os.getenv("APP_VERSION", "1.0.0")
AMBIENTE = os.getenv("APP_ENV", "dev")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
CHAVE_VISITAS = "visitas"

app = FastAPI(title="API Docker + Kubernetes", version=VERSAO)


def get_redis() -> redis.Redis:
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


@app.get("/")
def raiz():
    return {"mensagem": "API no ar", "docs": "/docs"}


@app.get("/info")
def info():
    # Em um Deployment com várias réplicas, o hostname muda a cada requisição
    # conforme o Service balanceia a carga entre os pods.
    return {"pod": socket.gethostname(), "ambiente": AMBIENTE, "versao": VERSAO}


@app.post("/visitas")
def registrar_visita(r: redis.Redis = Depends(get_redis)):
    try:
        total = r.incr(CHAVE_VISITAS)
    except redis.RedisError:
        raise HTTPException(status_code=503, detail="Redis indisponível")
    return {"visitas": total, "pod": socket.gethostname()}


@app.get("/visitas")
def ler_visitas(r: redis.Redis = Depends(get_redis)):
    try:
        total = int(r.get(CHAVE_VISITAS) or 0)
    except redis.RedisError:
        raise HTTPException(status_code=503, detail="Redis indisponível")
    return {"visitas": total}


@app.get("/saude")
def saude():
    return {"status": "ok"}


@app.get("/pronto")
def pronto(r: redis.Redis = Depends(get_redis)):
    try:
        r.ping()
    except redis.RedisError:
        raise HTTPException(status_code=503, detail="Redis indisponível")
    return {"status": "pronto"}
