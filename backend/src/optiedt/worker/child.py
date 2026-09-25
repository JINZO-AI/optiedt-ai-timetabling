"""Entry point of the child process that solves one run.

The worker starts a fresh interpreter per run (``spawn``), so a crash or a runaway search
inside OR-Tools can only end this process; the worker records the failure and carries on.
Messages go to the worker through a pipe: ``("progress", event)``, then exactly one of
``("result", result)`` or ``("error", {"code", "message"})``.
"""

from __future__ import annotations

import logging
import threading
from multiprocessing.connection import Connection
from multiprocessing.synchronize import Event
from typing import Any

from optiedt.solver.engine import EngineError
from optiedt.worker.execute import RunError, execute

logger = logging.getLogger("optiedt.worker.child")


def main(payload: dict[str, Any], sender: Connection, stop: Event) -> None:
    logging.basicConfig(level=logging.WARNING)
    lock = threading.Lock()

    def send(kind: str, data: dict[str, Any]) -> None:
        # Progress arrives from solver threads as well as the main thread.
        with lock:
            sender.send((kind, data))

    try:
        result = execute(payload, lambda event: send("progress", event), stop.is_set)
        send("result", result)
    except RunError as error:
        send("error", {"code": error.code, "message": error.message})
    except EngineError as error:
        send("error", {"code": "no_solution", "message": str(error)})
    except MemoryError:
        send(
            "error",
            {
                "code": "out_of_memory",
                "message": "The solver ran out of memory. Reduce the problem or give the "
                "worker more memory.",
            },
        )
    except Exception:
        logger.exception("solver run failed")
        send(
            "error",
            {
                "code": "internal",
                "message": "The solver failed unexpectedly; the error was logged.",
            },
        )
    finally:
        sender.close()
