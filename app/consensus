import time, math
from collections import defaultdict, deque
from typing import Dict, Tuple
from .schema import Intent, ConsensusCmd

class VectorConsensus:
    def __init__(self, tick_ms=200, deadlock_s=3.0, eps=0.07, alpha=0.4, vmax=0.6, wmax=0.8):
        self.tick_ms = tick_ms
        self.deadlock_s = deadlock_s
        self.eps = eps
        self.alpha = alpha
        self.vmax = vmax
        self.wmax = wmax
        self.buffer: Dict[str, list[Intent]] = defaultdict(list)
        self.last_nonzero_ts = time.time()
        self.sv_v = 0.0  # smoothed
        self.sv_w = 0.0
        self.tick = 0

    def ingest(self, intent: Intent):
        self.buffer[intent.session].append(intent)

    def _aggregate(self, session: str) -> Tuple[float, float, int]:
        intents = self.buffer.pop(session, [])
        if not intents:
            return 0.0, 0.0, 0
        # Weighted clipped mean
        total_w = sum(max(1, min(3, i.priority)) for i in intents)
        if total_w == 0:
            return 0.0, 0.0, len(intents)
        v = sum(i.v * max(1, min(3, i.priority)) for i in intents) / total_w
        w = sum(i.w * max(1, min(3, i.priority)) for i in intents) / total_w
        # clip
        v = max(-1.0, min(1.0, v)) * self.vmax
        w = max(-1.0, min(1.0, w)) * self.wmax
        return v, w, len(intents)

    def tick_once(self, session: str) -> ConsensusCmd:
        self.tick += 1
        v_raw, w_raw, n = self._aggregate(session)
        # EMA smoothing
        self.sv_v = self.alpha * v_raw + (1 - self.alpha) * self.sv_v
        self.sv_w = self.alpha * w_raw + (1 - self.alpha) * self.sv_w
        mag = math.hypot(self.sv_v, self.sv_w)
        standstill = mag < self.eps
        if not standstill:
            self.last_nonzero_ts = time.time()
        elif time.time() - self.last_nonzero_ts > self.deadlock_s:
            # tie-break shimmy
            self.sv_w = 0.3 * self.wmax
        return ConsensusCmd(
            session=session,
            ts=int(time.time()*1000),
            tick=self.tick,
            v=0.0 if standstill else self.sv_v,
            w=0.0 if standstill else self.sv_w,
            reason="vector_mean",
            contributors=n,
            standstill=standstill,
        )
