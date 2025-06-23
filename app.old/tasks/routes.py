# my_flask_app/tasks/routes.py
from flask import render_template, request, redirect, url_for, session, flash, current_app
from datetime import date, datetime

from . import tasks_bp
from .. import db # Import db from the main app package
from ..models import Task, User # Import Task and User models

# Access the login_required decorator from the application's globals
login_required = current_app.jinja_env.globals['login_required']


@tasks_bp.route('/dashboard')
@login_required
def dashboard():
    # user_id from MS Access login, assuming it corresponds to MySQL User.id
    current_user_id = session.get('user_id')
    user_name = session.get('user_fullname', session.get('user_email', 'Guest'))

    if not current_user_id:
        flash("User ID not found in session. Please log in.", 'danger')
        return redirect(url_for('auth.login'))

    # Fetch tasks for the current user from MySQL DB
    user_tasks = Task.query.filter_by(user_id=current_user_id).order_by(Task.due_date.asc(), Task.created_at.desc()).all()

    # Add a 'due_soon' flag for styling
    for t in user_tasks:
        if t.due_date:
            days_left = (t.due_date - date.today()).days
            # Task is due soon if it's due today or in the next 3 days and not completed
            t.due_soon = (days_left >= 0 and days_left <= 3) and t.status != 'Completed'
            t.overdue = (days_left < 0) and t.status != 'Completed' # Check for overdue tasks
        else:
            t.due_soon = False
            t.overdue = False

    return render_template('dashboard.html', user_name=user_name, tasks=user_tasks)


@tasks_bp.route('/add_task', methods=['GET', 'POST'])
@login_required
def add_task():
    current_user_id = session.get('user_id')
    if not current_user_id:
        flash("User ID not found. Please log in.", 'danger')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        task_name = request.form.get('task_name')
        due_date_str = request.form.get('due_date')
        description = request.form.get('description')

        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
                return render_template('add_edit_task.html', title='Add Task')

        if not task_name:
            flash('Task name cannot be empty!', 'danger')
        else:
            new_task = Task(name=task_name, description=description, due_date=due_date, user_id=current_user_id)
            db.session.add(new_task)
            db.session.commit()
            flash('Task added successfully!', 'success')
            return redirect(url_for('tasks.dashboard'))
    return render_template('add_edit_task.html', title='Add Task')

@tasks_bp.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    current_user_id = session.get('user_id')
    task = Task.query.get_or_404(task_id)

    # Ensure the logged-in user owns this task
    if task.user_id != current_user_id:
        flash('You are not authorized to edit this task.', 'danger')
        return redirect(url_for('tasks.dashboard'))

    if request.method == 'POST':
        task.name = request.form.get('task_name')
        due_date_str = request.form.get('due_date')
        task.description = request.form.get('description')
        task.status = request.form.get('status')

        if due_date_str:
            try:
                task.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
                return render_template('add_edit_task.html', title='Edit Task', task=task)
        else:
            task.due_date = None # Allow clearing the due date

        if not task.name:
            flash('Task name cannot be empty!', 'danger')
        else:
            db.session.commit()
            flash('Task updated successfully!', 'success')
            return redirect(url_for('tasks.dashboard'))

    return render_template('add_edit_task.html', title='Edit Task', task=task)

@tasks_bp.route('/mark_task_complete/<int:task_id>')
@login_required
def mark_task_complete(task_id):
    current_user_id = session.get('user_id')
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user_id:
        flash('You are not authorized to modify this task.', 'danger')
    else:
        task.status = 'Completed'
        db.session.commit()
        flash('Task marked as complete!', 'success')
    return redirect(url_for('tasks.dashboard'))

@tasks_bp.route('/delete_task/<int:task_id>')
@login_required
def delete_task(task_id):
    current_user_id = session.get('user_id')
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user_id:
        flash('You are not authorized to delete this task.', 'danger')
    else:
        db.session.delete(task)
        db.session.commit()
        flash('Task deleted successfully!', 'success')
    return redirect(url_for('tasks.dashboard'))