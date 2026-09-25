"""
Punto de entrada para desarrollo en Windows.

Con reload=True uvicorn spawna un proceso hijo que NO hereda el event loop
policy del padre. Por eso creamos el loop explícitamente aquí con
WindowsSelectorEventLoopPolicy antes de pasárselo a uvicorn.

En Linux / Docker se usa el comando uvicorn directo (sin este script).
"""
import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn
from uvicorn.config import Config
from uvicorn.main import Server


def main() -> None:
    config = Config(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,   # reload=True spawna subprocesos sin la policy
        log_level="info",
    )
    server = Server(config=config)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(server.serve())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
