import uvicorn
from dbos import DBOS

from .api import app
from .config import dbos_config

DBOS(fastapi=app, config=dbos_config)


if __name__ == "__main__":
    from dbos import DBOS

    DBOS.launch()
    uvicorn.run(app, host="0.0.0.0", port=8000)
