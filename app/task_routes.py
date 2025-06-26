# task_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime, date
from .models import db, Task

task_bp = Blueprint('task', __name__)

from functools import wraps
def login_required(view):
  @wraps(view)
  def wrapped_view(**kwargs):
    if 'user_code' not in session:
      flash("Please log in to access this page.", 'info')
      return redirect(url_for('auth.login'))
    return view(**kwargs)
  return wrapped_view


@task_bp.route('/add_task', methods=['GET', 'POST'])
@login_required
def add_task():
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
      user_code = session.get('user_code')
      new_task = Task(name=task_name, description=description, due_date=due_date, user_code=user_code)
      db.session.add(new_task)
      db.session.commit()
      flash('Task added successfully!', 'success')
      return redirect(url_for('auth.dashboard'))

  return render_template('add_edit_task.html', title='Add Task')


@task_bp.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
  task = Task.query.get_or_404(task_id)
  user_code = session.get('user_code')
  if task.user_code != user_code:
    flash('You are not authorized to edit this task.', 'danger')
    return redirect(url_for('dashboard'))

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
      task.due_date = None

    if not task.name:
      flash('Task name cannot be empty!', 'danger')
    else:
      db.session.commit()
      flash('Task updated successfully!', 'success')
      return redirect(url_for('auth.dashboard'))

  return render_template('add_edit_task.html', title='Edit Task', task=task)


@task_bp.route('/mark_task_complete/<int:task_id>')
@login_required
def mark_task_complete(task_id):
  task = Task.query.get_or_404(task_id)
  if task.user_code != session.get('user_code'):
    flash('You are not authorized to modify this task.', 'danger')
  else:
    task.status = 'Completed'
    db.session.commit()
    flash('Task marked as complete!', 'success')

  return redirect(url_for('auth.dashboard'))


@task_bp.route('/delete_task/<int:task_id>')
@login_required
def delete_task(task_id):
  task = Task.query.get_or_404(task_id)
  if task.user_code != session.get('user_code'):
    flash('You are not authorized to delete this task.', 'danger')
  else:
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted successfully!', 'success')

  return redirect(url_for('auth.dashboard'))
