# Student Task Manager

A local task-management app for students, built with Streamlit and SQLite. Tasks are private to the account that created them.

## Run locally

1. Create and activate a virtual environment.
2. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Start the app:

   ```powershell
   streamlit run app.py
   ```

4. Sign in with the seeded demo account: **admin / admin123**.

The app creates `tasks.db` beside `task_manager.py` on first run. Set `TASK_MANAGER_DB` to use a different local SQLite database file. The demo account is created only when it does not already exist; its password is stored as a salted PBKDF2 hash.

## Features

- Dashboard metrics for total, pending, in-progress, and completed tasks.
- A bar chart summarizing tasks by status.
- Forms to add tasks with a name, priority, due date, and status.
- A table of the signed-in user's tasks.
- Server-side validation and SQLite constraints for task fields.
- Database-backed login with per-user task isolation.
