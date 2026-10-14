"""第 2–4 课：模型、CRUD、依赖注入；数据仅保存在当前进程内。"""

from typing import Annotated, Optional

from fastapi import Depends, FastAPI, HTTPException, Path, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=100)
    completed: bool = False


class TaskRead(TaskCreate):
    id: int


class TaskStore:
    """教学用存储；真实并发写入应交给数据库及事务。"""

    def __init__(self):
        self.tasks: dict[int, TaskRead] = {}
        self.next_id = 1


def get_store() -> TaskStore:
    return store


store = TaskStore()
Store = Annotated[TaskStore, Depends(get_store)]
TaskId = Annotated[int, Path(gt=0)]
app = FastAPI(title="02 · 任务管理 API", version="1.0.0")


def require_task(task_id: int, db: TaskStore) -> TaskRead:
    task = db.tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@app.post("/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskCreate, db: Store):
    task = TaskRead(id=db.next_id, **payload.model_dump())
    db.tasks[task.id] = task
    db.next_id += 1
    return task


@app.get("/tasks", response_model=list[TaskRead])
async def list_tasks(
    db: Store,
    completed: Optional[bool] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    tasks = [t for t in db.tasks.values() if completed is None or t.completed == completed]
    return tasks[offset : offset + limit]


@app.get("/tasks/{task_id}", response_model=TaskRead)
async def read_task(task_id: TaskId, db: Store):
    return require_task(task_id, db)


@app.put("/tasks/{task_id}", response_model=TaskRead)
async def replace_task(task_id: TaskId, payload: TaskCreate, db: Store):
    # PUT 替换完整资源；省略 completed 时会采用默认值 False。
    require_task(task_id, db)
    task = TaskRead(id=task_id, **payload.model_dump())
    db.tasks[task_id] = task
    return task


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: TaskId, db: Store):
    require_task(task_id, db)
    del db.tasks[task_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)
