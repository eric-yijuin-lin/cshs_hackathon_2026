from enum import Enum
from datetime import datetime
from threading import RLock


class State(str, Enum):
    STATIC = "static"
    MOVE = "move"
    EMPTY = "empty"


class ToiletStateMachine:
    def __init__(self):
        self.state = State.EMPTY

        self.FAST_EMPTY = False
        self.LONG_STATIC = False

        self.last_static: datetime | None = None
        self.from_static = False

        self.lock = RLock()

    def update(self, someone: bool, motion: bool):
        with self.lock:
            # 無效資料，忽略
            if not someone and motion:
                return

            if someone and motion:
                new_state = State.MOVE
            elif someone:
                new_state = State.STATIC
            else:
                new_state = State.EMPTY

            # empty -> static 視為雜訊
            if self.state == State.EMPTY and new_state == State.STATIC:
                return

            # 狀態沒有改變，不更新時間
            if new_state == self.state:
                return

            now = datetime.now()
            old_state = self.state

            if new_state == State.EMPTY:
                if (
                    self.from_static
                    and self.last_static is not None
                    and (now - self.last_static).total_seconds() < 1
                ):
                    self.FAST_EMPTY = True

                self.from_static = False

            elif new_state == State.STATIC:
                self.last_static = now
                self.from_static = True

            elif new_state == State.MOVE:
                if old_state != State.STATIC:
                    self.from_static = False

            self.state = new_state

    def check_long_static(self, seconds: float):
        with self.lock:
            if (
                self.state == State.STATIC
                and self.last_static is not None
                and (datetime.now() - self.last_static).total_seconds()
                >= seconds
            ):
                self.LONG_STATIC = True

    def snapshot(self):
        with self.lock:
            return {
                "state": self.state.value,
                "fast_empty": self.FAST_EMPTY,
                "long_static": self.LONG_STATIC,
                "last_static": self.last_static,
            }

    def reset_warnings(self):
        with self.lock:
            self.FAST_EMPTY = False
            self.LONG_STATIC = False
