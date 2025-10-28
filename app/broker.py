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

        # 🧩 Add log callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

    @staticmethod
    def _parse_host(url: str):
        if "://" in url:
            _, rest = url.split("://", 1)
        else:
            rest = url
        host, port = rest.split(":")
        return host, int(port)

    def _on_connect(self, client, userdata, flags, rc):
        print(f"🔗 on_connect called: rc={rc}")
        if rc == 0:
            print("✅ Connected successfully to Solace MQTT broker!")
        else:
            print(f"❌ Connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        print(f"⚠️ Disconnected: rc={rc}")

    def on_message(self, handler: Callable[[str, bytes], None]):
        """Register a message handler callback.

        Each handler receives (topic, payload) for every message.
        """
        self._on_msg_handlers.append(handler)

    def subscribe(self, topic: str, qos: int = 0):
        """Subscribe to a topic."""
        print(f"📡 Subscribing to topic: {topic}")
        self.client.subscribe(topic, qos)

    def publish(self, topic: str, payload: dict, qos: int = 0, retain: bool = False):
        """Publish a JSON payload to a topic."""
        import json
        msg = json.dumps(payload)
        print(f"📤 Publishing to {topic}: {msg}")
        self.client.publish(topic, msg, qos=qos, retain=retain)

    def connect(self):
        self.client.on_message = lambda c, u, m: [h(m.topic, m.payload) for h in self._on_msg_handlers]
        print(f"🔍 Connecting to host={self.host}, port={self.port}")
        try:
            self.client.connect(self.host, self.port, keepalive=30)
            print("🕐 Waiting for on_connect callback...")
        except Exception as e:
            print(f"❌ MQTT connection failed immediately: {e}")
            raise
        self.client.loop_start()
