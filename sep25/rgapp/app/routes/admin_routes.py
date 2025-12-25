from flask import Blueprint, redirect, render_template, request, url_for, session
from app.models import Vemp
from flask import flash
from flask_mail import Message
from app import mail

admin_bp = Blueprint('admin', __name__)



# --- Index ---
@admin_bp.route('/admin', methods=['GET'])
def admin():
    user_action= request.args.get('action')
    if user_action == 'invite':
        user_id = request.args.get('user_id')
        # Here you would implement the logic to send an invitation to the user
        # For now, we will just print a message
        send_invitation = Vemp.query.filter_by(ID=user_id).first()
        if not send_invitation:
            flash(f"User with ID: {user_id} not found.", "error")
            return redirect(url_for('admin.admin'))
        # Example: send invitation email (replace with your actual email sending logic)

        msg = Message(
            subject="You're Invited to Join rcPro Connect",
            recipients=[send_invitation.email],
            body=f"Hello {send_invitation.name},\n\nYou are invited to join rcPro Connect. Please follow the link to complete your registration.\n\nBest regards,\nrcPro Connect Team"
        )
        mail.send(msg)
        flash(f"Invitation sent to user with ID: {user_id}", "success")
        
        return redirect(url_for('admin.admin'))
        
    if 'user_code' in session:
        users = Vemp.query.all()
        return render_template('admin.html', users=users)        
    return redirect(url_for('auth.login'))


