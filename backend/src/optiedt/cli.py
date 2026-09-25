"""Command-line entry point: ``optiedt <command>``."""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from collections.abc import Callable

from sqlalchemy import select

Command = Callable[[argparse.Namespace], int]


def _migrate(_: argparse.Namespace) -> int:
    from optiedt.db.migrate import upgrade_to_head

    upgrade_to_head()
    print("Database schema is at the latest revision.")
    return 0


def _create_admin(args: argparse.Namespace) -> int:
    from optiedt.db.session import get_session_factory
    from optiedt.models import RoleAssignment, User
    from optiedt.security import passwords
    from optiedt.services import audit

    password = os.environ.get("OPTIEDT_ADMIN_PASSWORD")
    if password is None and sys.stdin.isatty():
        password = getpass.getpass("Password for the new administrator: ")
    generated = password is None
    if password is None:
        from optiedt.services.users import temporary_password

        password = temporary_password()
    problems = passwords.policy_violations(password, username=args.username)
    if problems:
        print("Password rejected: " + " ".join(problems), file=sys.stderr)
        return 2

    with get_session_factory()() as db:
        username = args.username.strip().lower()
        if db.scalar(select(User.id).where(User.username == username)):
            print(f"User {username!r} already exists.", file=sys.stderr)
            return 1
        user = User(
            username=username,
            display_name=args.display_name,
            email=args.email,
            password_hash=passwords.hash_password(password),
            must_change_password=generated,
        )
        user.roles = [RoleAssignment(role="system_admin")]
        db.add(user)
        db.flush()
        audit.record(
            db,
            None,
            action="user.create",
            entity_type="user",
            entity_id=user.id,
            summary=f"Created system administrator {username} from the command line",
        )
        db.commit()
    print(f"Created system administrator {username!r}.")
    if generated:
        print(f"Temporary password (change it at first sign-in): {password}")
    return 0


def _worker(args: argparse.Namespace) -> int:
    from optiedt.config import get_settings
    from optiedt.db.session import get_session_factory
    from optiedt.logging_setup import configure_logging
    from optiedt.worker.main import Worker

    settings = get_settings()
    configure_logging(settings.log_level, settings.log_format)
    worker = Worker(settings, get_session_factory())
    if args.once:
        worker.run_once()
        return 0
    worker.install_signal_handlers()
    worker.run_forever()
    return 0


def _check_config(_: argparse.Namespace) -> int:
    from optiedt.config import Settings

    settings = Settings()
    print(f"Configuration valid for environment {settings.environment!r}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="optiedt", description="OptiEDT management commands")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("migrate", help="apply database migrations").set_defaults(func=_migrate)
    sub.add_parser("check-config", help="validate configuration").set_defaults(func=_check_config)

    admin = sub.add_parser("create-admin", help="create a system administrator account")
    admin.add_argument("--username", required=True)
    admin.add_argument("--display-name", required=True)
    admin.add_argument("--email")
    admin.set_defaults(func=_create_admin)

    worker = sub.add_parser("worker", help="run the solver worker")
    worker.add_argument("--once", action="store_true", help="process at most one queued run")
    worker.set_defaults(func=_worker)

    for register in _extra_commands():
        register(sub)

    args = parser.parse_args(argv)
    func: Command = args.func
    return func(args)


def _extra_commands() -> list[
    Callable[[argparse._SubParsersAction[argparse.ArgumentParser]], None]
]:
    return []


if __name__ == "__main__":
    raise SystemExit(main())
