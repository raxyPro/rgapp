from flask import Flask, render_template, request, redirect, flash, session
from flask_sqlalchemy import SQLAlchemy
import secrets
import xml.etree.ElementTree as ET

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# MySQL config (adjust DB names as needed)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://rcc:900@localhost/rcmain'
app.config['SQLALCHEMY_BINDS'] = {
    'rcmain': 'mysql+mysqlconnector://rcc:900@localhost/rcmain'
}
db = SQLAlchemy(app)

# SQLAlchemy models
class UserCV(db.Model):
    __tablename__ = 'user_cv'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, unique=True)
    name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    cv_data = db.Column(db.Text)

class Vemp(db.Model):
    __bind_key__ = 'rcmain'
    __tablename__ = 'vemp'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    fullname = db.Column(db.String(255))
    email = db.Column(db.String(255))


@app.before_request
def set_user_session():
    session['user_id'] = 9  # fixed for now


@app.route('/')
def edit_cv():
    user_id = session['user_id']
    user_cv = UserCV.query.filter_by(user_id=user_id).first()
    vemp = Vemp.query.filter_by(user_id=user_id).first()

    if not user_cv:
        user_cv = UserCV(user_id=user_id, cv_data="<cv></cv>", name=vemp.fullname if vemp else "", email=vemp.email if vemp else "")
        db.session.add(user_cv)
        db.session.commit()

    return render_template("edit_cv.html", cv_data=user_cv.cv_data)


@app.route('/save', methods=['POST'])
def save_cv():
    user_id = session['user_id']
    new_data = request.form['cv_data']
    
    # Validate XML
    try:
        ET.fromstring(new_data)
    except ET.ParseError as e:
        flash(f"XML Error: {e}", "error")
        return render_template("edit_cv.html", cv_data=new_data)

    user_cv = UserCV.query.filter_by(user_id=user_id).first()
    if user_cv:
        user_cv.cv_data = new_data
        db.session.commit()
        flash("CV Saved successfully", "success")

    return redirect('/')


@app.route('/view')
def view_cv():
    user_id = session['user_id']
    user_cv = UserCV.query.filter_by(user_id=user_id).first()
    return render_template("view_cv.html", cv_data=user_cv.cv_data if user_cv else "<cv></cv>")


from xml.etree import ElementTree as ET
from markupsafe import Markup

@app.route('/preview')
def preview_cv():

    user_id = session['user_id']
    user_cv = UserCV.query.filter_by(user_id=user_id).first()
    print(user_cv.cv_data)
    xml_data = user_cv.cv_data if user_cv else "<cv></cv>"
    
    try:
        root = ET.fromstring(xml_data)
        def extract(tag):
            el = root.find(tag)
            return el.text.strip() if el is not None and el.text else ''

        # Example extraction
        cv = {
            'name': extract('name'),
            'email': extract('email'),
            'mobile': extract('mobile'),
            'headline': extract('headline'),
            'summary': extract('summary'),
            'skills': [s.text for s in root.findall('keyskills/skill')],
            'roles': [r.text for r in root.findall('role-looking-for/role')],
            'experiences': [{
                'org': e.findtext('organization', ''),
                'from': e.findtext('from', ''),
                'to': e.findtext('to', ''),
                'role': e.findtext('role', ''),
                'achievements': e.findtext('keyachievements', ''),
                'remark': e.findtext('remark', '')
            } for e in root.findall('experience')],
            'education': [{
                'title': ed.findtext('title', ''),
                'institute': ed.findtext('institute', ''),
                'from': ed.findtext('from', ''),
                'to': ed.findtext('to', ''),
                'remark': ed.findtext('remark', '')
            } for ed in root.findall('education')],
        }

    except ET.ParseError as e:
        return f"<h3>Malformed XML:</h3><pre>{e}</pre>"

    return render_template("preview_cv.html", cv=cv)


if __name__ == '__main__':
    #db.create_all()  # Ensure tables are created
    app.run(debug=True)