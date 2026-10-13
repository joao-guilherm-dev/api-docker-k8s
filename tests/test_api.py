import pytest
import redis
from fastapi.testclient import TestClient

from app.main import app, get_redis


class RedisFalso:
    def __init__(self):
        self.dados = {}

    def incr(self, chave):
        self.dados[chave] = int(self.dados.get(chave, 0)) + 1
        return self.dados[chave]

    def get(self, chave):
        valor = self.dados.get(chave)
        return None if valor is None else str(valor)

    def ping(self):
        return True


class RedisQuebrado:
    def incr(self, chave):
        raise redis.ConnectionError("fora do ar")

    def get(self, chave):
        raise redis.ConnectionError("fora do ar")

    def ping(self):
        raise redis.ConnectionError("fora do ar")


@pytest.fixture
def client():
    falso = RedisFalso()
    app.dependency_overrides[get_redis] = lambda: falso
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_raiz(client):
    assert client.get("/").status_code == 200


def test_info_tem_pod_e_versao(client):
    corpo = client.get("/info").json()
    assert {"pod", "ambiente", "versao"} <= corpo.keys()


def test_visitas_incrementa(client):
    assert client.get("/visitas").json() == {"visitas": 0}
    client.post("/visitas")
    resposta = client.post("/visitas").json()
    assert resposta["visitas"] == 2
    assert client.get("/visitas").json() == {"visitas": 2}


def test_saude_nao_depende_do_redis():
    app.dependency_overrides[get_redis] = lambda: RedisQuebrado()
    try:
        assert TestClient(app).get("/saude").status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_pronto_retorna_503_sem_redis():
    app.dependency_overrides[get_redis] = lambda: RedisQuebrado()
    try:
        assert TestClient(app).get("/pronto").status_code == 503
    finally:
        app.dependency_overrides.clear()


def test_pronto_ok(client):
    assert client.get("/pronto").status_code == 200
