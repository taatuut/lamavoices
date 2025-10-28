from pydantic import BaseModel, Field
from typing import Literal

class Intent(BaseModel):
    opId: str
    session: str
    ts: int
    mode: Literal["vector", "discrete"] = "vector"
    v: float = 0.0  # -1..1
    w: float = 0.0  # -1..1
    priority: int = 1
    auth: str | None = None

class ConsensusCmd(BaseModel):
    session: str
    ts: int
    tick: int
    v: float
    w: float
    reason: str
    contributors: int
    standstill: bool = False

class Event(BaseModel):
    severity: Literal["INFO","WARN","ERROR"] = "INFO"
    code: str
    msg: str
    ts: int
