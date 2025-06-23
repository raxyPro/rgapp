# run.py
from rgapp import create_app, db  # Change 'rgapp' to your actual package/module name if different

app = create_app()

# This is a good place to create MySQL tables if they don't exist,
# especially during development. In production, you'd typically use
# a migration tool (like Flask-Migrate).
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True) # debug=True is for development only.