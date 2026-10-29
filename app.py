"""Streamlit interface for the student task manager."""

from __future__ import annotations

import streamlit as st

from task_manager import (
    PRIORITIES,
    STATUSES,
    User,
    add_task,
    authenticate,
    get_task_metrics,
    get_tasks,
    initialize_database,
)


def _login_page() -> None:
    st.title("Student Task Manager")
    st.write("Sign in to manage your tasks.")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in", type="primary")
    if submitted:
        user = authenticate(username, password)
        if user is None:
            st.error("Incorrect username or password.")
        else:
            st.session_state["user"] = user
            st.rerun()
    st.caption("Demo account: admin / admin123")


def _dashboard(user: User) -> None:
    st.title("Dashboard")
    metrics = get_task_metrics(user.id)
    columns = st.columns(4)
    for column, label in zip(columns, metrics):
        column.metric(label, metrics[label])

    st.subheader("Tasks by status")
    chart_data = {
        "Status": list(STATUSES),
        "Tasks": [metrics[status] for status in STATUSES],
    }
    st.bar_chart(chart_data, x="Status", y="Tasks", color="#4F46E5")


def _add_task_page(user: User) -> None:
    st.title("Add Task")
    with st.form("add_task_form"):
        name = st.text_input("Task name", max_chars=100)
        priority = st.selectbox("Priority", PRIORITIES)
        due_date = st.date_input("Due date")
        status = st.selectbox("Status", STATUSES)
        submitted = st.form_submit_button("Save task", type="primary")

    if submitted:
        try:
            add_task(user.id, name, priority, due_date, status)
        except ValueError as error:
            st.error(str(error))
        else:
            st.success("Task saved.")


def _view_tasks_page(user: User) -> None:
    st.title("View Tasks")
    tasks = get_tasks(user.id)
    if tasks:
        st.dataframe(tasks, hide_index=True)
    else:
        st.info("You haven't added any tasks yet.")


def main() -> None:
    st.set_page_config(page_title="Student Task Manager", page_icon="✅", layout="wide")
    initialize_database()

    user = st.session_state.get("user")
    if not isinstance(user, User):
        _login_page()
        return

    with st.sidebar:
        st.write(f"Signed in as **{user.username}**")
        if st.button("Log out"):
            del st.session_state["user"]
            st.rerun()
        page = st.radio("Navigate", ("Dashboard", "Add Task", "View Tasks"))

    if page == "Dashboard":
        _dashboard(user)
    elif page == "Add Task":
        _add_task_page(user)
    else:
        _view_tasks_page(user)


if __name__ == "__main__":
    main()
