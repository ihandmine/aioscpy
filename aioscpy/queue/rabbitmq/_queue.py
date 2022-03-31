import pika

from queue import BaseQueue


class PriorityQueue(BaseQueue):
    def qsize(self) -> int:
        return self.server.get_waiting_message_count()

    def push(self, request: dict):
        data = self._encode_request(request)
        score = request.get('priority', 1)

        self.server.basic_publish(
            properties=pika.BasicProperties(priority=score),
            exchange='',
            routing_key=self.key,
            body=data
        )

    def on_message(self, ch, method, properties, body):
        pass

    def m_pop(self, on_message_callback=None, auto_ack=False):
        if not on_message_callback:
            on_message_callback = self.on_message
        self.server.basic_consume(
            on_message_callback=on_message_callback,
            queue=self.key,
            auto_ack=auto_ack
        )
        self.server.start_consuming()

    def pop(self, auto_ack=False):
        _method, _, _body = self.server.basic_get(queue=self.key, auto_ack=auto_ack)
        if all([isinstance(_body, bytes), _body is not None]):
            return _method, self._decode_request(_body)
        return None, None

    def finish(self, method):
        self.server.basic_ack(delivery_tag=method.delivery_tag)


class RabbitMq:
    __mq_instance = None
    __mq_connection_instance = None

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = self.validator(kwargs)

    @staticmethod
    def validator(params: dict) -> dict:
        params.setdefault('host', '127.0.0.1')
        params.setdefault('port', 5672)
        params.setdefault('username', 'admin')
        params.setdefault('password', 'admin')
        params.setdefault('max_priority', 100)
        params.setdefault('key', 'rabbitmq:queue')
        return params

    @property
    def get_channel(self):
        if not self.__mq_instance:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=self.kwargs['host'],
                    port=self.kwargs['port'],
                    credentials=pika.PlainCredentials(
                        username=self.kwargs['username'],
                        password=self.kwargs['password']
                    )
                )
            )
            channel = connection.channel()
            channel.queue_declare(
                queue=self.kwargs['key'],
                arguments={"x-max-priority": self.kwargs['max_priority']}
            )
            self.__mq_instance, self.__mq_connection_instance = channel, connection
        return self.__mq_instance

    def close(self):
        if self.__mq_instance:
            self.__mq_instance.close()
            self.__mq_connection_instance.close()


def priority_queue(key: str, mq: dict) -> PriorityQueue:
    server = RabbitMq(**mq).get_channel
    return PriorityQueue(server=server, key=key)


spider_priority_queue = priority_queue

"""
# unit test example
def run():
    queue = rabbitmq_client('message:queue')
    for i in range(5):
        queue.push({"url": f"https://www.baidu.com/?kw={i}", "task_id": '123'})
    while 1:
        method, msg = queue.pop()
        print(msg)
        if not msg:
            break
        time.sleep(1)
        if method:
            queue.finish(method)

run()

"""

