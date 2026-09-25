"""
Punto de entrada para desarrollo en Windows.
Fuerza WindowsSelectorEventLoopPolicy antes de que uvicorn cree el event loop,
lo que resuelve la incompatibilidad de asyncpg con ProactorEventLoop en Python 3.12+.
"""
import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
