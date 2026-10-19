"""发送 UTF-8 消息：python component/kafka/producer.py --message '你好 Kafka'。"""

import argparse
import logging
import os

from confluent_kafka import Producer


def main():
    parser = argparse.ArgumentParser(description="Kafka 消息生产者")
    parser.add_argument("--bootstrap-servers", default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"))
    parser.add_argument("--topic", default=os.getenv("KAFKA_TOPIC", "python-demo"))
    parser.add_argument("--message", required=True, help="消息内容，可传入 JSON 字符串")
    parser.add_argument("--key", help="消息键，相同键通常进入同一分区")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    producer = Producer({
        "bootstrap.servers": args.bootstrap_servers,
        "enable.idempotence": True,
        "acks": "all",
        "delivery.timeout.ms": 30000,
    })
    errors = []

    def on_delivery(error, message):
        if error is not None:
            errors.append(str(error))
            logging.error("发送失败: %s", error)
        else:
            logging.info("发送成功 topic=%s partition=%s offset=%s",
                         message.topic(), message.partition(), message.offset())

    producer.produce(
        args.topic,
        value=args.message.encode("utf-8"),
        key=args.key.encode("utf-8") if args.key is not None else None,
        on_delivery=on_delivery,
    )
    remaining = producer.flush(timeout=35)
    if remaining or errors:
        raise RuntimeError("消息发送失败或等待确认超时")


if __name__ == "__main__":
    main()
