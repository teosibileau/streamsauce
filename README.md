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

## Snapshot Detection Pipeline

When a snapshot event arrives, the workflow runs the following steps:

```
log_snapshot -> detect_objects -> persist_detection -> annotate_snapshot
```

1. **log_snapshot** - Logs receipt of the snapshot event
2. **detect_objects** - Downloads the JPEG, runs YOLO inference via ONNX Runtime, returns detection results (bounding boxes, classes, confidences, latency). Returns `None` if nothing detected, short-circuiting the pipeline.
3. **persist_detection** - Saves detection results as JSON to `output/annotations/{camera_id}/{epoch}.json`
4. **annotate_snapshot** - Downloads the JPEG, draws bounding boxes and labels using supervision, saves annotated image to `output/annotations/{camera_id}/{epoch}.jpg`

Each step emits a DBOS event (`SNAPSHOT_RECEIVED`, `DETECTION_COMPLETE`, `ANNOTATION_SAVED`) that external consumers can subscribe to via `DBOS.get_event()`.

### Detection Stack

- **ONNX Runtime** for inference (CoreML on Mac, CUDA on NVIDIA GPUs)
- **supervision** (MIT) for postprocessing (NMS, class filtering, annotation)
- **YOLO model** exported to `.onnx` format (export is a dev-only step using ultralytics)
- Target COCO classes: person, car, motorcycle, bus, truck, and animals (bird through giraffe)

### Model Export

Export a YOLO model to ONNX format for use by the detection engine:

```bash
ahoy setup export-model                        # Default: yolo11n
ahoy setup export-model -- --model yolo11s     # Specify model variant
ahoy setup export-model -- --force             # Overwrite existing
```

The `.onnx` file is saved to `.data/` and is not tracked in git.

## Project Structure

```
app/
  main.py                           # FastAPI + DBOS + consumer lifecycle
  config.py                         # DBOS, AMQP, and ONNX configuration
  consumer.py                       # AMQPConsumer class (aio-pika, message dispatch)
  schemas.py                        # Pydantic models for snapshot/segment events
  api.py                            # REST endpoints (health, workflow list/detail)
  detection/
    engine.py                       # OnnxDetector class (singleton, lazy init)
  pipelines/
    snapshot/
      workflow.py                   # process_snapshot (DBOS workflow)
      steps.py                      # log, detect, persist, annotate (DBOS steps)
      events.py                     # SnapshotEvent enum
    segment/
      workflow.py                   # process_segment (DBOS workflow)
      steps.py                      # log_segment (DBOS step)
scripts/
  export_model.py                   # Typer CLI for YOLO -> ONNX export
tests/                              # Unit tests for all modules
.data/                              # Model weights and ONNX exports (gitignored)
docker-compose.yml
.ahoy.yml                           # Ahoy command helpers
.env.example                        # Environment variable template
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
ahoy setup export-model       # Export YOLO model to ONNX
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
| `chopper` | `ghcr.io/teosibileau/streamchop/chopper:v0.1.2` | -     | Connects to an RTSP source, chops into HLS segments + snapshots. Outputs to `output/chopper/cam1/` |
| `emitter` | `ghcr.io/teosibileau/streamchop/emitter:v0.1.2` | -     | Watches `output/chopper/`, publishes segment/snapshot events to MQTT |
| `nginx`   | `ghcr.io/teosibileau/streamchop/nginx:v0.1.2`   | 8080  | Serves HLS files and snapshots from `output/chopper/` over HTTP |

## Docker Profiles

Services are organized into profiles to start only what you need:

| Profile | Services                            | Use case                        |
|---------|-------------------------------------|---------------------------------|
| `chop`  | chopper, emitter, nginx, broker     | Streamchop edge pipeline        |
| `input` | cam (mediamtx)                      | Simulated camera input          |

Use the `ahoy profile` command to compose profiles:

```bash
ahoy profile chop docker up     # Start chop services
ahoy profile input docker up    # Start mediamtx
```

Or combine them:

```bash
ahoy profile chop profile input docker up   # Start chop + input
```

Or use all:
```bash
ahoy profile all docker up
```


## Output Directories

| Directory | Contents | Written by |
|-----------|----------|------------|
| `output/chopper/{camera_id}/` | HLS segments (.ts), playlists (.m3u8), snapshots (.jpg) | streamchop chopper |
| `output/annotations/{camera_id}/` | Annotated JPEGs and detection JSON | streamsauce pipeline |

## Ahoy Commands

| Command                        | Description                                           |
|--------------------------------|-------------------------------------------------------|
| `ahoy docker compose up`      | Start core services (postgres + broker)               |
| `ahoy dbos start`             | Start the streamsauce application                     |
| `ahoy setup install`          | Install Python dependencies via Poetry                |
| `ahoy setup export-model`     | Export YOLO model to ONNX format                      |
| `ahoy stream <file>`          | Stream a video from `input/` to mediamtx in a loop    |
| `ahoy stream`                 | Interactive menu to select a video file                |
| `ahoy clean`                  | Remove generated jpg, ts, and m3u8 files from output  |
| `ahoy docker log <service>`   | Tail logs for a docker service                        |
| `ahoy docker ps`              | List running containers                               |

## Environment Variables

### ONNX Detection

| Variable | Default | Description |
|----------|---------|-------------|
| `ONNX_MODEL_PATH` | `.data/yolo11n.onnx` | Path to the ONNX model file |
| `ONNX_EXECUTION_PROVIDER` | `CPUExecutionProvider` | ONNX Runtime provider (`CPUExecutionProvider`, `CoreMLExecutionProvider`, `CUDAExecutionProvider`) |
| `ONNX_CONFIDENCE_THRESHOLD` | `0.25` | Minimum confidence score for detections |

See `.env.example` for all available environment variables.

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
