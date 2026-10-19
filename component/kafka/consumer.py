"""消费 UTF-8 消息，业务处理成功后同步提交 offset。"""

import argparse
import logging
import os

from confluent_kafka import Consumer, KafkaError, KafkaException


def handle_message(message):
    """在这里添加业务逻辑；异常会终止消费，该消息不会提交位点。"""
    key = message.key()
    value = message.value()
    logging.info(
        "收到消息 topic=%s partition=%s offset=%s key=%s value=%s",
        message.topic(), message.partition(), message.offset(),
        key.decode("utf-8") if key is not None else None,
        value.decode("utf-8") if value is not None else None,
    )


def main():
    parser = argparse.ArgumentParser(description="Kafka 消息消费者（Ctrl+C 退出）")
    parser.add_argument("--bootstrap-servers", default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"))
    parser.add_argument("--topic", default=os.getenv("KAFKA_TOPIC", "python-demo"))
    parser.add_argument("--group-id", default=os.getenv("KAFKA_GROUP_ID", "python-demo-group"))
    parser.add_argument("--auto-offset-reset", choices=("earliest", "latest"), default="earliest",
                        help="消费组没有有效已提交位点时的起始位置")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    consumer = Consumer({
        "bootstrap.servers": args.bootstrap_servers,
        "group.id": args.group_id,
        "auto.offset.reset": args.auto_offset_reset,
        "enable.auto.commit": False,
        "enable.auto.offset.store": False,
        "allow.auto.create.topics": False,
    })
    try:
        consumer.subscribe([args.topic])
        logging.info("开始消费 topic=%s group=%s", args.topic, args.group_id)
        while True:
            message = consumer.poll(timeout=1.0)
            if message is None:
                continue
            if message.error():
                if message.error().code() == KafkaError._PARTITION_EOF:
                    continue
                raise KafkaException(message.error())
            handle_message(message)
            consumer.commit(message=message, asynchronous=False)
    except KeyboardInterrupt:
        logging.info("停止消费")
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
