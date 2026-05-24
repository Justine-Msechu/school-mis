"""
Background task worker — runs callables off the main thread via a thread-safe queue.

Usage:
    from core.background import background_worker

    def done(result, error):
        if error:
            show_error(str(error))
        else:
            update_ui(result)

    background_worker.submit("Generate report", my_func, arg1, arg2, callback=done)

The callback is invoked on the *main* thread via Qt signal, so UI updates are safe.
"""

import traceback
from queue import Queue, Empty
from typing import Callable

from PyQt6.QtCore import QThread, pyqtSignal, QObject


class _Job:
    __slots__ = ("name", "fn", "args", "kwargs", "callback")

    def __init__(self, name: str, fn: Callable, args: tuple, kwargs: dict,
                 callback: Callable | None):
        self.name     = name
        self.fn       = fn
        self.args     = args
        self.kwargs   = kwargs
        self.callback = callback


class _Dispatcher(QObject):
    """Lives on the main thread; receives results via signal and calls the callback."""
    result_ready = pyqtSignal(object, object, object)   # (callback, result, error)

    def __init__(self):
        super().__init__()
        self.result_ready.connect(self._dispatch)

    @staticmethod
    def _dispatch(callback, result, error):
        if callback is not None:
            try:
                callback(result, error)
            except Exception:
                traceback.print_exc()


class BackgroundWorker(QThread):
    """
    Single persistent worker thread.  Jobs are queued and executed FIFO.
    One shared instance (`background_worker`) is created at module level.
    """

    job_started   = pyqtSignal(str)   # job name
    job_finished  = pyqtSignal(str)   # job name
    job_failed    = pyqtSignal(str, str)  # job name, error message

    def __init__(self):
        super().__init__()
        self._queue      = Queue()
        self._dispatcher = _Dispatcher()
        self.setDaemon(True)

    # ── Public API ────────────────────────────────────────────────────────────

    def submit(self, name: str, fn: Callable, *args,
               callback: Callable | None = None, **kwargs) -> None:
        """
        Queue a job.

        :param name:     Human-readable label for logging/signals.
        :param fn:       Callable to run off the main thread.
        :param args:     Positional args passed to fn.
        :param callback: Optional callable(result, error) invoked on the main thread.
        :param kwargs:   Keyword args passed to fn.
        """
        self._queue.put(_Job(name, fn, args, kwargs, callback))
        if not self.isRunning():
            self.start()

    # ── QThread entry point ───────────────────────────────────────────────────

    def run(self):
        while True:
            try:
                job = self._queue.get(timeout=30)
            except Empty:
                # No work for 30 s — exit thread (it will be restarted on next submit)
                break

            self.job_started.emit(job.name)
            result = error = None
            try:
                result = job.fn(*job.args, **job.kwargs)
            except Exception as exc:
                error = exc
                self.job_failed.emit(job.name, str(exc))
                traceback.print_exc()

            self.job_finished.emit(job.name)
            self._dispatcher.result_ready.emit(job.callback, result, error)
            self._queue.task_done()


# Module-level singleton — import and use directly
background_worker = BackgroundWorker()
