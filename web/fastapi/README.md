# FastAPI 快速学习：从请求校验到可测试的任务 API

适合：会 Python 函数、类型注解、字典和基本异常处理，第一次接触 FastAPI。
目标：约 5 小时后，能独立写出带校验、错误处理和测试的 CRUD API；这不等于掌握生产部署。
环境：Python 3.9+，Pydantic v2。依赖独立维护在本目录，不需要安装仓库根目录的 AI 相关依赖。

## 先运行（15 分钟）

在仓库根目录执行，以下命令使用你当前激活的 Python 环境：

```bash
cd web/fastapi
python -m pip install -r requirements.txt
python -m uvicorn examples.hello:app --reload
```

打开 <http://127.0.0.1:8000/docs>，执行 `/hello` 和 `/items/{item_id}`。
另外可查看 `/redoc` 和 `/openapi.json`。按 Ctrl+C 停止服务，再启动综合示例：

```bash
python -m uvicorn examples.tasks:app --reload
```

如果提示找不到 `examples`，先确认当前目录是 `web/fastapi`。不要将文件命名为 `fastapi.py`，以免遮蔽第三方包。

## 学习安排

| 阶段 | 时间 | 阅读/操作 | 验收标准 |
| --- | --- | --- | --- |
| 1. HTTP 与路由 | 40 分钟 | 阅读 `examples/hello.py`，访问 docs，尝试路径 `1`、`abc`、`0` 和查询参数 `detail=true` | 能解释路径参数、查询参数分别从哪里来，以及为什么返回 422 |
| 2. 请求体与响应模型 | 50 分钟 | 阅读 `TaskCreate`、`TaskRead` 和 POST，提交正常、空白、超长及多余字段 | 能解释输入模型为什么不含 id、201 与 422 的差别 |
| 3. CRUD 与 HTTP 语义 | 60 分钟 | 完成创建→列表→读取→PUT→删除，尝试过滤与分页 | 能解释 PUT 的替换语义、404、删除后的空响应 204 |
| 4. 依赖注入与 async | 45 分钟 | 追踪 `Depends(get_store)`，阅读测试 fixture，回答下方问题 | 能说明依赖覆盖如何隔离测试，以及 async 的适用条件 |
| 5. 测试与独立练习 | 90 分钟 | 运行测试，再独立完成下方挑战 | 失败输入也有测试；能不用复制代码新增一个端点 |

每阶段先预测响应，再执行请求，最后解释差异。只在 Swagger 点通几个接口，不能证明你理解了框架。

## 文件导览

- `examples/hello.py`：最小应用、类型转换、参数约束。
- `examples/tasks.py`：请求/响应模型、CRUD、依赖注入、过滤分页、HTTPException。
- `tests/test_api.py`：TestClient、依赖覆盖、完整业务流程和非法输入。
- `requests.http`：可在 PyCharm HTTP Client 中依次执行的请求。
- `requirements.txt`：教学用兼容范围，非精确锁定文件；正式协作需锁定实际验证版本。

## 手动走通业务

先启动 tasks 应用，另开终端：

```bash
curl -i -X POST http://127.0.0.1:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{"title":"学习 FastAPI"}'
# 预期 201，返回 {"title":"学习 FastAPI","completed":false,"id":1}

curl 'http://127.0.0.1:8000/tasks?completed=false&offset=0&limit=10'

curl -i -X PUT http://127.0.0.1:8000/tasks/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"完成入门","completed":true}'

curl -i -X DELETE http://127.0.0.1:8000/tasks/1
curl -i http://127.0.0.1:8000/tasks/1
# 分别预期 204（无响应体）和 404。
```

这里的 id=1 假设服务刚启动、没有其他请求；实际以创建响应中的 id 为准。

## 运行测试

在 `web/fastapi` 目录执行；测试不需要先启动 Uvicorn：

```bash
python -m pytest -q
```

测试通过依赖覆盖为每个用例注入新存储。不要让测试依赖上一个用例留下的数据，也不要只测 200。

## 必须想清楚的几个问题

1. **async def 一定更快吗？** 不是。只有等待可异步执行的 I/O 时，事件循环才能处理其他请求。在 async 路由中直接调用 `requests.get()` 或 `time.sleep()` 会阻塞事件循环；同步阻塞库通常放在普通 `def` 路由，或明确卸载到线程池。CPU 密集任务应考虑独立进程/任务系统。本示例的 async 路由没有阻塞 I/O，也不展示数据库异步访问。
2. **422 是业务错误吗？** 此处通常是请求未通过声明的类型或约束校验；404 是请求格式正确但资源不存在。Pydantic 默认可能转换类型，例如可转换的布尔字符串，不等于严格类型检查。
3. **PUT 是只修改给出的字段吗？** 本示例是完整替换，省略 completed 会重置为 False。部分更新应另加 PATCH，区分“未提供”和“显式 null”。
4. **类型注解等于数据库约束吗？** 不是。请求校验不负责跨请求唯一性、事务或持久化。
5. **Depends 会为每次请求创建新的 store 吗？** 这里函数返回同一个模块级对象。依赖注入让获取资源的方式可替换，并不会自动决定资源生命周期。

## 独立练习（先自己实现）

- [ ] 增加 `GET /health`，返回 `{"status":"ok"}`，写一个最小测试。
- [ ] 为列表增加标题搜索，明确空字符串、大小写与分页顺序的规则。
- [ ] 增加 `PATCH /tasks/{task_id}`：只更新提供的字段；使用 `model_dump(exclude_unset=True)`；禁止 title/completed 显式为 null。测试 `{}`、`{"completed":false}`、`{"title":null}`，防止把 False 当成“未提供”。
- [ ] 通过依赖替换把内存存储迁移到 SQLite，重启后验证数据保留，并思考事务、连接生命周期和并发写入。

验收时关闭示例文件，从空文件重写其中一个接口，并解释每个参数来源。再故意破坏一条校验，确认测试能捕获。

## 示例边界与下一步

内存数据在重启/热重载后清空，多 worker 之间不共享；不适合作为生产存储。没有认证、用户隔离和并发写入保障。开发时的 `--reload` 仅用于本地。学完后再逐项补上数据库、迁移、配置管理、认证授权和部署，不要一开始堆 JWT、Redis、Docker 分散注意力。

官方资料（按学习顺序）：[入门教程](https://fastapi.tiangolo.com/tutorial/)、[请求体](https://fastapi.tiangolo.com/tutorial/body/)、[依赖注入](https://fastapi.tiangolo.com/tutorial/dependencies/)、[测试](https://fastapi.tiangolo.com/tutorial/testing/)、[部分更新](https://fastapi.tiangolo.com/tutorial/body-updates/)、[异步原理](https://fastapi.tiangolo.com/async/)。

本次验证环境：Python 3.9.6、FastAPI 0.128.8、Pydantic 2.12.5、Uvicorn 0.39.0、HTTPX 0.28.1、pytest 8.4.2，13 个测试通过。新建环境建议使用 Python 3.11+；当前示例兼容项目现有的 3.9 解释器。
