# Langflow Production Deployment

**Designed for:** Robust production environments, teams, and high-availability setups.

| Feature | Details |
| :--- | :--- |
| **Complexity** | 🔴 High (~10 services) |
| **Architecture** | Microservices (Frontend, Backend, Workers, Queue, DB) |
| **Networking** | Traefik Reverse Proxy (Port 80/443), SSL support |
| **Monitoring** | Prometheus + Grafana included |
| **Intended Use** | Teams, SSL requirements, Heavy async workloads |

> **Note:** For a simpler, minimal configuration, see the `simple_langflow` (or `docker_example`) directory.

## Overview

This represents a "Production Ready" stack with:
*   **Traefik**: Reverse proxy for routing and SSL.
*   **Celery + RabbitMQ + Redis**: Scalable async task processing.
*   **Prometheus + Grafana**: Full observability stack.
*   **pgAdmin**: Database management GUI.

## Docker compose
To run Langflow with Docker compose, you need to have Docker and Docker compose installed on your machine. You can install Docker and Docker compose by following the instructions on the [official Docker documentation](https://docs.docker.com/get-docker/).

The docker-compose file uses `latest` tag; it's recommended to pull the latest version of the images before running the docker-compose file.

```bash
docker compose pull
```

To start the Langflow services, run the following command:

```bash
docker compose up
```

After running the command, you can access the Langflow services at the following url: http://localhost:80.

Edit the `.env` file to change the port or other configurations.