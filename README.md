# Streamsauce

You [chop](https://github.com/teosibileau/streamchop), then you make sauce from the pieces.

Streamsauce consumes camera events from [streamchop](https://github.com/teosibileau/streamchop) edge deployments via RabbitMQ and processes them as durable DBOS workflows. Each snapshot or video segment event from an edge camera becomes an exactly-once workflow, with idempotency guaranteed by epoch-based workflow IDs.

## Architecture

```
Edge (streamchop)          Cloud (streamsauce)
+-----------+    MQTT     +------------+    AMQP     +---------------+
|  chopper  | --------->  | RabbitMQ   | --------->  | AMQP Consumer |
|  emitter  |   1883      | (broker)   |   5672      |               |
+-----------+             | amq.topic  |             | DBOS Workflows|
                          +------------+             +---------------+
                           MQTT plugin                    |
                           bridges to                     v
                           amq.topic               +------------+
                           exchange                | PostgreSQL |
                                                   +------------+
```

- **streamchop** runs on edge devices, monitoring cameras via RTSP. It chops streams into HLS segments and JPEG snapshots, then publishes events via MQTT.
- **RabbitMQ** with the MQTT plugin bridges MQTT messages to the `amq.topic` AMQP exchange, converting topic separators from `/` to `.` (e.g., `streamchop/cam1/snapshot` becomes `streamchop.cam1.snapshot`).
- **Streamsauce** binds a durable queue to the exchange, consumes events, and dispatches DBOS workflows. Workflow IDs are derived from `{camera_id}-{event_type}-{epoch}`, ensuring exactly-once processing even if messages are replayed.

## Project Structure

```
app/
  main.py         # FastAPI + DBOS + consumer lifecycle (lifespan)
  config.py       # DBOS and AMQP configuration from env vars
  consumer.py     # AMQPConsumer class (aio-pika, message dispatch)
  schemas.py      # Pydantic models for snapshot/segment events
  workflows.py    # DBOS workflows and steps
  api.py          # REST endpoints (health, workflow list/detail)
tests/            # Unit tests for all modules
docker-compose.yml
.ahoy.yml         # Ahoy command helpers
.env.example      # Environment variable template
```

## Getting Started

### Prerequisites

- Python 3.12+
- [Poetry](https://python-poetry.org/)
- Docker and Docker Compose v2
- [Ahoy](https://github.com/ahoy-cli/ahoy) (optional, for command shortcuts)

### Setup

```bash
cp .env.example .env          # Configure environment variables
ahoy setup install            # Install Python dependencies (or: poetry install)
ahoy docker compose up        # Start postgres + broker
ahoy dbos start               # Start the application
```

## Docker Services

### Core

These services are required to run the application:

| Service    | Image                           | Ports              | Description                                          |
|------------|---------------------------------|--------------------|------------------------------------------------------|
| `postgres` | `postgres:15`                   | 5432               | DBOS system database for workflow state               |
| `broker`   | `rabbitmq:4-management-alpine`  | 5672, 1883, 15672  | RabbitMQ with MQTT plugin (AMQP + MQTT + Management) |

### Development

These services simulate the streamchop edge pipeline for development without real camera hardware:

| Service   | Image                                           | Ports | Description                                                  |
|-----------|-------------------------------------------------|-------|--------------------------------------------------------------|
| `cam`     | `bluenviron/mediamtx:latest`                    | 8554  | MediaMTX RTSP server. Accepts video streams to simulate a camera source |
| `chopper` | `ghcr.io/teosibileau/streamchop/chopper:v0.1.1` | -     | Connects to an RTSP source, chops into HLS segments + snapshots |
| `emitter` | `ghcr.io/teosibileau/streamchop/emitter:v0.1.1` | -     | Watches output directory, publishes segment/snapshot events to MQTT |
| `nginx`   | `ghcr.io/teosibileau/streamchop/nginx:v0.1.1`   | 8080  | Serves HLS files and snapshots over HTTP                      |

## Docker Profiles

Services are organized into profiles to start only what you need:

| Profile | Services                            | Use case                        |
|---------|-------------------------------------|---------------------------------|
| `main`  | postgres, broker                    | Run the application             |
| `chop`  | chopper, emitter, nginx, broker     | Streamchop edge pipeline        |
| `input` | cam (mediamtx)                      | Simulated camera input          |

Use the `ahoy profile` command to compose profiles:

```bash
ahoy profile chop docker compose up     # Start chop services
ahoy profile input docker compose up    # Start mediamtx
```

Or combine them:

```bash
ahoy profile chop profile input docker compose up   # Start chop + input
```

## Ahoy Commands

| Command                        | Description                                           |
|--------------------------------|-------------------------------------------------------|
| `ahoy docker compose up`      | Start core services (postgres + broker)               |
| `ahoy dbos start`             | Start the streamsauce application                     |
| `ahoy stream <file>`          | Stream a video from `input/` to mediamtx in a loop    |
| `ahoy stream`                 | Interactive menu to select a video file                |
| `ahoy clean`                  | Remove generated jpg, ts, and m3u8 files from output  |
| `ahoy docker log <service>`   | Tail logs for a docker service                        |
| `ahoy docker ps`              | List running containers                               |
| `ahoy setup install`          | Install Python dependencies via Poetry                |

## Simulating Camera Input

To develop without a real camera:

1. Place a video file in `input/` (e.g., `people_walking.mp4`)
2. Start mediamtx: `ahoy profile input docker compose up`
3. Stream the video: `ahoy stream people_walking.mp4`
4. Set `CAM1_RTSP_URL=rtsp://cam:8554/cam1` in `.env`
5. Start the chop pipeline: `ahoy profile chop docker compose up`

The chopper will connect to mediamtx, chop the looped video into segments and snapshots, the emitter will publish events to MQTT, and the streamsauce consumer will pick them up as DBOS workflows.

## API Endpoints

The application exposes a REST API on port 8000:

| Endpoint                      | Description                                           |
|-------------------------------|-------------------------------------------------------|
| `GET /health`                 | Health check                                          |
| `GET /workflows`              | List workflows (query params: `status`, `start_time`, `end_time`, `name`, `limit`, `offset`, `sort_desc`) |
| `GET /workflows/{workflow_id}` | Get workflow detail (input, output, error, timestamps) |

The workflow list defaults to `status=PENDING`. Available statuses: `PENDING`, `SUCCESS`, `ERROR`, `CANCELLED`, `ENQUEUED`.

## Testing

```bash
poetry run pytest
```
