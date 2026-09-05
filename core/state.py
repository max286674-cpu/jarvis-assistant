"""Runtime state machine and cancellation primitives for low-latency voice interaction."""
from __future__ import annotations
from enum import Enum
from threading import Event, Lock

class RuntimeState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"
    EXECUTING = "executing"
    ERROR = "error"
    STOPPED = "stopped"

class CancellationToken:
    def __init__(self):
        self._event = Event()
    def cancel(self) -> None:
        self._event.set()
    def reset(self) -> None:
        self._event.clear()
    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

class RuntimeStateMachine:
    def __init__(self):
        self._state = RuntimeState.IDLE
        self._lock = Lock()
    @property
    def state(self) -> RuntimeState:
        with self._lock:
            return self._state
    def set(self, state: RuntimeState) -> RuntimeState:
        with self._lock:
            self._state = state
            return state
    def interrupt(self) -> RuntimeState:
        return self.set(RuntimeState.INTERRUPTED)
    def stop(self) -> RuntimeState:
        return self.set(RuntimeState.STOPPED)
