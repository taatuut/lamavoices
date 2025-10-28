from .schema import ConsensusCmd

class SafetyGate:
    def __init__(self, max_v=0.6, max_w=0.8, obstacle=False):
        self.max_v=max_v; self.max_w=max_w; self.obstacle=obstacle

    def apply(self, cmd: ConsensusCmd) -> ConsensusCmd:
        if self.obstacle:
            cmd.v = 0.0; cmd.w = 0.0; cmd.reason += "+obstacle"
            cmd.standstill = True
            return cmd
        cmd.v = max(-self.max_v, min(self.max_v, cmd.v))
        cmd.w = max(-self.max_w, min(self.max_w, cmd.w))
        return cmd
