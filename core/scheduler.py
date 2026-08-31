"""Background Task Scheduler and System Watcher for Iris."""

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
import psutil


@dataclass
class ScheduledTask:
    name: str
    callback: Callable[..., Any]
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    interval_seconds: Optional[float] = None
    next_run_time: float = 0.0
    recurring: bool = False
    created_at: str = ""
    last_run_at: Optional[str] = None


class TaskScheduler:
    """Threaded background scheduler for one-shot timers and recurring interval jobs."""

    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Starts the background scheduler daemon."""
        if self._worker_thread is not None and self._worker_thread.is_alive():
            return

        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._run_loop, daemon=True)
        self._worker_thread.start()

    def _run_loop(self) -> None:
        """Continuous execution loop checking due tasks."""
        while not self._stop_event.is_set():
            now = time.time()
            due_tasks = []

            with self._lock:
                for name, task in list(self._tasks.items()):
                    if now >= task.next_run_time:
                        due_tasks.append(task)
                        if task.recurring and task.interval_seconds:
                            task.next_run_time = now + task.interval_seconds
                            task.last_run_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            del self._tasks[name]

            # Execute due tasks outside the lock
            for task in due_tasks:
                try:
                    task.callback(*task.args, **task.kwargs)
                except Exception as e:
                    print(f"[Scheduler Error in task '{task.name}']: {e}")

            if self._stop_event.wait(0.05):
                break

    def schedule_once(
        self,
        name: str,
        delay_seconds: float,
        callback: Callable[..., Any],
        *args,
        **kwargs,
    ) -> None:
        """Schedules a task to run once after a delay."""
        now = time.time()
        task = ScheduledTask(
            name=name,
            callback=callback,
            args=args,
            kwargs=kwargs,
            interval_seconds=None,
            next_run_time=now + delay_seconds,
            recurring=False,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        with self._lock:
            self._tasks[name] = task
        self.start()

    def schedule_interval(
        self,
        name: str,
        interval_seconds: float,
        callback: Callable[..., Any],
        *args,
        **kwargs,
    ) -> None:
        """Schedules a recurring task to execute at fixed intervals."""
        now = time.time()
        task = ScheduledTask(
            name=name,
            callback=callback,
            args=args,
            kwargs=kwargs,
            interval_seconds=interval_seconds,
            next_run_time=now + interval_seconds,
            recurring=True,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        with self._lock:
            self._tasks[name] = task
        self.start()

    def cancel(self, name: str) -> bool:
        """Cancels a scheduled task by name."""
        with self._lock:
            if name in self._tasks:
                del self._tasks[name]
                return True
            return False

    def list_tasks(self) -> List[Dict[str, Any]]:
        """Returns summary of all active scheduled jobs."""
        with self._lock:
            results = []
            now = time.time()
            for name, task in self._tasks.items():
                secs_remaining = max(0, round(task.next_run_time - now, 1))
                results.append({
                    "name": name,
                    "recurring": task.recurring,
                    "interval_seconds": task.interval_seconds,
                    "seconds_until_next_run": secs_remaining,
                    "created_at": task.created_at,
                    "last_run_at": task.last_run_at,
                })
            return results

    def start_battery_watcher(
        self,
        threshold_percent: int = 20,
        on_low_battery: Optional[Callable[[int], None]] = None,
    ) -> None:
        """Registers a background watcher checking for low battery every 60 seconds."""
        def check_battery():
            battery = psutil.sensors_battery()
            if battery and not battery.power_plugged and battery.percent <= threshold_percent:
                if on_low_battery:
                    on_low_battery(battery.percent)

        self.schedule_interval("battery_watcher", 60.0, check_battery)

    def shutdown(self) -> None:
        """Stops the scheduler and cancels all tasks."""
        self._stop_event.set()
        with self._lock:
            self._tasks.clear()


# Global scheduler singleton
scheduler = TaskScheduler()
