from datetime import date

import pytest

from task_manager import (
    add_task,
    authenticate,
    get_task_metrics,
    get_tasks,
    initialize_database,
    validate_task,
)


@pytest.fixture
def database_path(tmp_path):
    path = tmp_path / "tasks.db"
    initialize_database(path)
    return path


def test_seeded_account_authenticates_against_database(database_path):
    user = authenticate("admin", "admin123", database_path)

    assert user is not None
    assert user.username == "admin"
    assert authenticate("admin", "wrong", database_path) is None


def test_tasks_and_metrics_are_isolated_by_user(database_path):
    admin = authenticate("admin", "admin123", database_path)
    assert admin is not None
    add_task(admin.id, "Read chapter", "High", date(2026, 11, 1), "Pending", database_path)
    add_task(admin.id, "Submit lab", "Medium", "2026-11-02", "Completed", database_path)

    assert len(get_tasks(admin.id, database_path)) == 2
    assert get_tasks(admin.id + 1, database_path) == []
    assert get_task_metrics(admin.id, database_path) == {
        "Total": 2,
        "Pending": 1,
        "In Progress": 0,
        "Completed": 1,
    }
    assert get_task_metrics(admin.id + 1, database_path)["Total"] == 0


@pytest.mark.parametrize(
    ("name", "priority", "due_date", "status"),
    [
        ("  ", "Low", "2026-11-01", "Pending"),
        ("Read", "Urgent", "2026-11-01", "Pending"),
        ("Read", "Low", "not-a-date", "Pending"),
        ("Read", "Low", "2026-11-01", "Blocked"),
        ("x" * 101, "Low", "2026-11-01", "Pending"),
    ],
)
def test_invalid_task_values_are_rejected(name, priority, due_date, status):
    with pytest.raises(ValueError):
        validate_task(name, priority, due_date, status)


def test_valid_task_values_are_normalized():
    assert validate_task("  Read chapter  ", "Low", date(2026, 11, 1), "Pending") == (
        "Read chapter",
        "Low",
        "2026-11-01",
        "Pending",
    )
