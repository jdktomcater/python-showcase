# Kafka 生产者和消费者

在项目根目录运行。需要已启动且可连接的 Kafka，以及已创建的 `python-demo` Topic
（或通过 `--topic` 指定现有 Topic）。示例连接使用 PLAINTEXT，无认证。

```bash
python -m pip install -r component/kafka/requirements.txt

# 终端一：启动消费者
python component/kafka/consumer.py

# 终端二：发送一条消息，确认结果后退出
python component/kafka/producer.py --message '你好 Kafka'
python component/kafka/producer.py --key order-1 --message '{"order_id": 1, "status": "created"}'
```

使用项目对应的 Python 环境执行上述命令。

两个程序均支持 `--bootstrap-servers host1:9092,host2:9092` 和 `--topic my-topic`。
消费者还支持 `--group-id my-group`、`--auto-offset-reset earliest|latest`。
连接地址、Topic、消费组也可通过 `KAFKA_BOOTSTRAP_SERVERS`、`KAFKA_TOPIC`、
`KAFKA_GROUP_ID` 环境变量配置，命令行参数优先。

在 `consumer.py` 的 `handle_message()` 中添加业务逻辑。消息按 UTF-8 文本处理，
JSON 以字符串传输；Kafka tombstone（空值）显示为 `None`。
处理成功后同步提交该消息的下一位点，处理或提交异常会退出，避免继续提交后续消息。
处理成功但提交前崩溃仍可能造成重复消费，业务操作需要幂等。
处理时间应小于消费者的 `max.poll.interval.ms`，耗时任务需要额外设计。

`earliest` 仅在消费组没有有效位点时生效；重新读取历史消息可指定新的消费组。
生产者启用幂等写入以避免客户端重试导致的重复，但手动重复运行命令仍会产生新消息。
生产者等待发送确认，失败时以非零状态退出；消费者使用 Ctrl+C 关闭连接。

客户端用法参考 [Confluent 官方文档](https://docs.confluent.io/kafka-clients/python/current/overview.html)。
