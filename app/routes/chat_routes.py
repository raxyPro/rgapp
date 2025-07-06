# task_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime, date
from ..models import db, Task

chat_bp = Blueprint('chat', __name__)

from functools import wraps
def login_required(view):
  @wraps(view)
  def wrapped_view(**kwargs):
    if 'user_code' not in session:
      flash("Please log in to access this page.", 'info')
      return redirect(url_for('auth.login'))
    return view(**kwargs)
  return wrapped_view


@chat_bp.route('/chat', methods=['GET', 'POST'])
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



