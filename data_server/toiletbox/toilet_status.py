
import threading
from collections import deque
from datetime import datetime, timedelta
from enum import Enum, auto


class ToiletState(Enum):
    EMPTY = auto()
    STATIC = auto()
    MOVE = auto()


class ToiletAlert(Enum):
    FAST_EXIT = auto()
    LONG_STATIC = auto()


class ToiletStateMachine:
    def __init__(self):
        self._status = ToiletState.EMPTY

        # LONG_STATIC：目前這段連續 STATIC 的起點
        self._static_started_at = None

        # FAST_EXIT：最近一次進入 STATIC 的時間
        self._last_static_at = None

        # EMPTY 緩衝確認的起點
        self._empty_started_at = None

        self.fast_exit_threshold = timedelta(seconds=1)
        self.static_threshold = timedelta(seconds=5)
        self.empty_grace_period = timedelta(milliseconds=500)

        self._static_alert_sent = False
        self._alerts = deque()
        self._lock = threading.Lock()

    @property
    def status(self):
        with self._lock:
            return self._status

    def update(
        self,
        someone: bool,
        motion: bool,
        timestamp: datetime
    ):
        """由 ESP32 API 更新狀態，回傳狀態是否改變。"""

        if not someone and motion:
            return False

        if not someone:
            new_state = ToiletState.EMPTY
        elif motion:
            new_state = ToiletState.MOVE
        else:
            new_state = ToiletState.STATIC

        with self._lock:
            old_state = self._status

            # ---------- EMPTY 緩衝確認 ----------
            if new_state == ToiletState.EMPTY:

                # 原本就已經是 EMPTY
                if old_state == ToiletState.EMPTY:
                    return False

                # 第一次收到 EMPTY，開始緩衝計時
                if self._empty_started_at is None:
                    self._empty_started_at = timestamp

                    # 離開 STATIC 前檢查 LONG_STATIC
                    if old_state == ToiletState.STATIC:
                        self._check_static_timeout(timestamp)

                    return False

                # EMPTY 尚未持續達到緩衝時間
                if (timestamp - self._empty_started_at
                        < self.empty_grace_period):
                    return False

                # EMPTY 已確認
                # FAST_EXIT 使用第一次收到 EMPTY 的時間
                if (
                    self._last_static_at is not None
                    and timedelta(0)
                    <= self._empty_started_at - self._last_static_at
                    < self.fast_exit_threshold
                ):
                    self._alerts.append(ToiletAlert.FAST_EXIT)

                self._status = ToiletState.EMPTY
                self._static_started_at = None
                self._last_static_at = None
                self._empty_started_at = None
                self._static_alert_sent = False

                return True

            # ---------- 取消 EMPTY 緩衝 ----------
            # 在確認時間內再次偵測到有人
            if self._empty_started_at is not None:
                self._empty_started_at = None

            # ---------- 狀態沒有改變 ----------
            if old_state == new_state:
                if new_state == ToiletState.STATIC:
                    self._check_static_timeout(timestamp)
                return False

            # 禁止 EMPTY -> STATIC
            if (
                old_state == ToiletState.EMPTY
                and new_state == ToiletState.STATIC
            ):
                return False

            # 離開 STATIC 前檢查 LONG_STATIC
            if old_state == ToiletState.STATIC:
                self._check_static_timeout(timestamp)

            # ---------- 更新狀態 ----------
            self._status = new_state

            if new_state == ToiletState.STATIC:

                # 每次進入 STATIC，重新計算 LONG_STATIC
                self._static_started_at = timestamp
                self._static_alert_sent = False

                # 更新最近一次 STATIC，供 FAST_EXIT 使用
                self._last_static_at = timestamp

            elif new_state == ToiletState.MOVE:

                # 中斷 LONG_STATIC
                # 但保留 FAST_EXIT 的時間基準
                self._static_started_at = None
                self._static_alert_sent = False

            return True

    def _check_static_timeout(self, now: datetime):
        """檢查是否連續 STATIC 超過門檻。"""

        if (
            self._status == ToiletState.STATIC
            and self._static_started_at is not None
            and not self._static_alert_sent
            and now - self._static_started_at
            > self.static_threshold
        ):
            self._alerts.append(ToiletAlert.LONG_STATIC)
            self._static_alert_sent = True

    def get_alerts(self):
        """取得並清空尚未處理的警告。"""

        with self._lock:
            alerts = list(self._alerts)
            self._alerts.clear()
            return alerts
