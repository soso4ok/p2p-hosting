from typing import Union

from fastapi import FastAPI

from app.api.check_status.db_check import router as db_router
from app.api.check_status.redis_check import router as redis_router

app = FastAPI()
app.include_router(redis_router)
app.include_router(db_router)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}
