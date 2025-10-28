import json, ssl, os, time
import paho.mqtt.client as mqtt
from typing import Callable

class MqttBus:
    def __init__(self, client_id: str | None = None):
        self.client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
        host = os.getenv("SOLACE_HOST", "ssl://localhost:8883")
        if host.startswith("ssl://") or host.endswith(":8883"):
            self.client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
        self.client.username_pw_set(os.getenv("SOLACE_USERNAME", ""), os.getenv("SOLACE_PASSWORD", ""))
        self.host, self.port = self._parse_host(host)
        self._on_msg_handlers: list[Callable[[str, bytes], None]] = []

    @staticmethod
    def _parse_host(url: str):
        scheme, rest = url.split("://", 1)
        host, port = rest.split(":")
        return host, int(port)

    def connect(self):
        self.client.on_message = lambda c, u, m: [h(m.topic, m.payload) for h in self._on_msg_handlers]
        self.client.connect(self.host, self.port, keepalive=30)
        self.client.loop_start()

    def publish(self, topic: str, payload: dict, qos: int = 1):
        self.client.publish(topic, json.dumps(payload).encode("utf-8"), qos=qos)

    def subscribe(self, topic: str):
        self.client.subscribe(topic, qos=1)

    def on_message(self, handler: Callable[[str, bytes], None]):
        self._on_msg_handlers.append(handler)
