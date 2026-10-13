# api-docker-k8s

API em **Python (FastAPI)** com **Redis**, empacotada com **Docker** e implantada em **Kubernetes**.
Projeto de estudo que cobre o ciclo completo: código, container, orquestração, escala e CI.

## O que o projeto demonstra

- **Dockerfile** com cache de camadas, usuário sem privilégios e `HEALTHCHECK`
- **Docker Compose** com API + Redis e `depends_on` com healthcheck
- **Kubernetes**: Namespace, ConfigMap, Deployments, Services, Ingress e HPA
- **Probes**: `/saude` (liveness) e `/pronto` (readiness, depende do Redis)
- **Rolling update** sem indisponibilidade (`maxUnavailable: 0`)
- **Autoescalonamento** por CPU (HPA, de 3 a 8 réplicas)
- **Limites de recursos** e `securityContext` (não roda como root)
- **CI** com GitHub Actions: testes e build da imagem

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/` | Mensagem de boas-vindas |
| GET | `/info` | Nome do pod, ambiente e versão |
| POST | `/visitas` | Incrementa o contador (Redis) |
| GET | `/visitas` | Lê o contador |
| GET | `/saude` | Liveness probe |
| GET | `/pronto` | Readiness probe |

A documentação interativa fica em `/docs`.

## Estrutura

```
.
├── app/main.py
├── tests/test_api.py
├── Dockerfile
├── docker-compose.yml
├── k8s/
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── redis.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── hpa.yaml
│   ├── ingress.yaml
│   └── kustomization.yaml
└── .github/workflows/ci.yml
```

## Rodando com Docker Compose

```bash
docker compose up --build
curl http://localhost:8000/info
curl -X POST http://localhost:8000/visitas
```

## Rodando no Kubernetes (kind ou minikube)

Pré-requisitos: Docker, `kubectl` e um cluster local ([kind](https://kind.sigs.k8s.io/) ou [minikube](https://minikube.sigs.k8s.io/)).

```bash
# 1. construir a imagem
docker build -t api-docker-k8s:1.0.0 .

# 2. disponibilizar a imagem no cluster
kind load docker-image api-docker-k8s:1.0.0      # kind
# minikube image load api-docker-k8s:1.0.0       # minikube

# 3. aplicar os manifestos
kubectl apply -k k8s/

# 4. acompanhar
kubectl get pods -n tarefas
kubectl rollout status deployment/api -n tarefas

# 5. acessar
kubectl port-forward -n tarefas svc/api 8000:80
curl http://localhost:8000/info
```

### Vendo o balanceamento de carga

Com o `port-forward` ativo, o tráfego fica fixo em um pod. Para ver o balanceamento,
chame a API de dentro do cluster:

```bash
kubectl run teste -n tarefas --rm -it --image=curlimages/curl --restart=Never -- \
  sh -c 'for i in 1 2 3 4 5 6; do curl -s http://api/info; echo; done'
```

O campo `pod` muda entre as respostas. O contador de `/visitas` continua correto porque
o estado está no Redis, não nos pods.

### Testando a resiliência

```bash
kubectl delete pod -n tarefas -l app=api --wait=false   # o Deployment recria os pods
kubectl scale deployment/api -n tarefas --replicas=5    # escala manual
```

### Atualização sem downtime

```bash
docker build -t api-docker-k8s:1.1.0 .
kind load docker-image api-docker-k8s:1.1.0
kubectl set image deployment/api api=api-docker-k8s:1.1.0 -n tarefas
kubectl rollout status deployment/api -n tarefas
kubectl rollout undo deployment/api -n tarefas          # reverter, se necessário
```

### Ingress e HPA (opcionais)

- O **Ingress** exige um controller NGINX instalado (`minikube addons enable ingress` ou o manifesto do ingress-nginx para kind) e a entrada `api.local` no `/etc/hosts`.
- O **HPA** exige o `metrics-server` (`minikube addons enable metrics-server`).

## Testes locais

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

## Limpeza

```bash
kubectl delete -k k8s/
docker compose down
```

## Próximos passos

- Persistência do Redis com `StatefulSet` e `PersistentVolumeClaim`
- Chart Helm
- Publicar a imagem em um registry (GHCR) pelo CI
- Observabilidade com Prometheus e Grafana
