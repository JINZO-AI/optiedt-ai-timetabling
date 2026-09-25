"""The worker loop: claim a queued run, solve it in a child process, store the result.

While the child works, the worker keeps the run's lease alive, records progress at most once
a second, forwards cancellation, and stops the child when it outlives its time limit. On
shutdown it stops the child and puts the run back in the queue for another worker.
"""

from __future__ import annotations

import logging
import multiprocessing
import os
import signal
import socket
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from multiprocessing.connection import Connection
from typing import Any

from sqlalchemy.orm import Session

from optiedt.config import Settings
from optiedt.context import run_id_var
from optiedt.models import ProblemSnapshot, SolverRun
from optiedt.services.run_results import store_result
from optiedt.worker import child, queue

logger = logging.getLogger(__name__)

CANCEL_GRACE_SECONDS = 30.0
"""How long a cancelled child may take to return its best timetable before it is killed."""
OVERRUN_FACTOR = 3.0
OVERRUN_MARGIN_SECONDS = 300.0
PROGRESS_INTERVAL_SECONDS = 1.0
HOUSEKEEPING_SECONDS = 600.0


@dataclass
class Outcome:
    kind: str
    """``result``, ``error``, ``requeue`` or ``lost``."""
    data: dict[str, Any]


class Worker:
    def __init__(
        self,
        settings: Settings,
        session_factory: Callable[[], Session],
        *,
        worker_id: str | None = None,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.hostname = socket.gethostname()
        self.id = worker_id or f"{self.hostname}:{os.getpid()}:{uuid.uuid4().hex[:6]}"
        self.stopping = threading.Event()
        self._housekept = 0.0

    # ── loop ──────────────────────────────────────────────────────────

    def install_signal_handlers(self) -> None:
        def stop(signum: int, _frame: object) -> None:
            logger.info("worker stopping", extra={"signal": signum})
            self.stopping.set()

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)

    def run_forever(self) -> None:
        logger.info("worker started", extra={"worker": self.id})
        try:
            while not self.stopping.is_set():
                if not self.run_once():
                    self.stopping.wait(self.settings.worker_poll_seconds)
        finally:
            with self.session_factory() as db:
                queue.forget_worker(db, self.id)
            logger.info("worker stopped", extra={"worker": self.id})

    def run_once(self) -> bool:
        """Claims and processes one run; False when the queue was empty."""
        with self.session_factory() as db:
            queue.heartbeat(db, self.id, self.hostname, None)
            queue.recover_expired(db, self.settings.run_max_attempts)
            if time.monotonic() - self._housekept > HOUSEKEEPING_SECONDS:
                queue.purge(db)
                self._housekept = time.monotonic()
            run_id = queue.claim(db, self.id, self.settings.worker_lease_seconds)
        if run_id is None:
            return False
        token = run_id_var.set(str(run_id))
        try:
            self.process(run_id)
        finally:
            run_id_var.reset(token)
        return True

    # ── one run ───────────────────────────────────────────────────────

    def process(self, run_id: uuid.UUID) -> None:
        with self.session_factory() as db:
            run = db.get(SolverRun, run_id)
            snapshot = db.get(ProblemSnapshot, run.snapshot_id) if run else None
            if run is None or snapshot is None:
                return
            payload = {"config": run.config, "snapshot": snapshot.payload}
            limit = float(run.config["time_limit_seconds"])
        logger.info("run started", extra={"run_id": str(run_id), "kind": payload["config"]["kind"]})
        started = time.monotonic()
        outcome = self._supervise(run_id, payload, limit)
        with self.session_factory() as db:
            if outcome.kind == "result":
                run = db.get(SolverRun, run_id, with_for_update=True)
                if run is not None and run.worker_id == self.id and run.status == "running":
                    try:
                        store_result(db, run, outcome.data)
                        db.commit()
                    except Exception:
                        db.rollback()
                        logger.exception(
                            "storing a run result failed", extra={"run_id": str(run_id)}
                        )
                        queue.fail(
                            db,
                            run_id,
                            self.id,
                            "store_failed",
                            "The timetables were computed but could not be stored; the error "
                            "was logged.",
                        )
            elif outcome.kind == "error":
                queue.fail(db, run_id, self.id, outcome.data["code"], outcome.data["message"])
            elif outcome.kind == "requeue":
                queue.requeue(db, run_id, self.id, outcome.data["reason"])
        logger.info(
            "run finished",
            extra={
                "run_id": str(run_id),
                "outcome": outcome.kind,
                "seconds": round(time.monotonic() - started, 1),
            },
        )

    def _supervise(self, run_id: uuid.UUID, payload: dict[str, Any], limit: float) -> Outcome:
        context = multiprocessing.get_context("spawn")
        receiver, sender = context.Pipe(duplex=False)
        stop = context.Event()
        process = context.Process(
            target=child.main, args=(payload, sender, stop), name=f"optiedt-run-{run_id}"
        )
        process.start()
        sender.close()
        outcome: Outcome | None = None
        deadline = time.monotonic() + limit * OVERRUN_FACTOR + OVERRUN_MARGIN_SECONDS
        stop_sent: float | None = None
        last_lease = last_progress = 0.0
        pending: dict[str, Any] | None = None
        shutdown = closed = False
        try:
            while True:
                message, closed = self._receive(receiver, closed)
                if message is not None:
                    kind, data = message
                    if kind == "progress":
                        pending = data
                    else:
                        outcome = Outcome(kind, data)
                now = time.monotonic()
                if pending is not None and now - last_progress >= PROGRESS_INTERVAL_SECONDS:
                    with self.session_factory() as db:
                        queue.record_progress(db, run_id, self.id, pending)
                    pending, last_progress = None, now
                if now - last_lease >= self.settings.worker_heartbeat_seconds:
                    last_lease = now
                    with self.session_factory() as db:
                        state = queue.renew(db, run_id, self.id, self.settings.worker_lease_seconds)
                        queue.heartbeat(db, self.id, self.hostname, run_id)
                    if state == "lost":
                        stop.set()
                        process.terminate()
                        return Outcome("lost", {})
                    if state == "cancel" and stop_sent is None:
                        stop.set()
                        stop_sent = now
                if self.stopping.is_set() and stop_sent is None:
                    shutdown = True
                    stop.set()
                    stop_sent = now
                if stop_sent is not None and now - stop_sent > CANCEL_GRACE_SECONDS:
                    process.terminate()
                if now > deadline and process.is_alive():
                    stop.set()
                    process.terminate()
                    outcome = Outcome(
                        "error",
                        {
                            "code": "timeout",
                            "message": "The solver did not stop within its time limit and was "
                            "ended.",
                        },
                    )
                if not process.is_alive() and (closed or not receiver.poll()):
                    break
        finally:
            process.join(timeout=10)
            if process.is_alive():
                process.kill()
                process.join(timeout=5)
            receiver.close()
        if shutdown:
            return Outcome("requeue", {"reason": "The worker was shutting down."})
        if outcome is not None:
            return outcome
        return Outcome(
            "error",
            {
                "code": "worker_crash",
                "message": "The solver process stopped unexpectedly "
                f"(exit code {process.exitcode}). The run can be requested again.",
            },
        )

    @staticmethod
    def _receive(
        receiver: Connection, closed: bool
    ) -> tuple[tuple[str, dict[str, Any]] | None, bool]:
        """The next message, if one arrives within a moment, and whether the child has
        closed its end of the pipe."""
        if closed:
            time.sleep(0.2)
            return None, True
        try:
            if receiver.poll(0.2):
                kind, data = receiver.recv()
                return (str(kind), dict(data)), False
        except (EOFError, OSError):
            return None, True
        return None, False
