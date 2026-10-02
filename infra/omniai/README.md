# OmniAI modular compose

Default profile starts only the FastAPI gateway. Optional profiles:

- `distributed`: NATS + LangGraph agent + Go realtime gateway;
- `learning`: LlamaIndex service;
- `ml`: TensorFlow service (requires a trained local artifact);
- `polyglot`: Go/NestJS/Spring learning services.

Example:

```bash
docker compose -f infra/omniai/docker-compose.yml up --build gateway
docker compose -f infra/omniai/docker-compose.yml --profile distributed up --build
```

The compose file is an integration scaffold; live Docker results remain
`not_run` until executed on the target machine.
