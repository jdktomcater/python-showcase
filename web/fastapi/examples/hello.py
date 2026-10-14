"""第 1 课：路由、路径参数、查询参数、自动校验。"""

from typing import Annotated

from fastapi import FastAPI, Path, Query

app = FastAPI(title="01 · 请求与校验")


@app.get("/hello")
async def hello(name: Annotated[str, Query(min_length=1, max_length=30)] = "世界"):
    return {"message": f"你好，{name}！"}


@app.get("/items/{item_id}")
async def read_item(
    item_id: Annotated[int, Path(gt=0)],
    detail: bool = False,
):
    return {"item_id": item_id, "detail": detail}
