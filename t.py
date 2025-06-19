import os
from datetime import timedelta
# --- Templating (HTML Files) ---
# These will be in the 'templates/' directory

# templates/layout.html
# This is the base template for consistent header and footer.
# It includes Tailwind CSS for basic styling.
# NOTE: Tailwind CSS is loaded via CDN for simplicity.
# For a production app, you'd integrate it properly with PostCSS.
layout_html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}My App{% endblock %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
        .flash {
            padding: 0.75rem 1.25rem;
            margin-bottom: 1rem;
            border: 1px solid transparent;
            border-radius: 0.25rem;
        }
        .flash.success {
            color: #155724;
            background-color: #d4edda;
            border-color: #c3e6cb;
        }
        .flash.danger {
            color: #721c24;
            background-color: #f8d7da;
            border-color: #f5c6cb;
        }
        .flash.info {
            color: #0c5460;
            background-color: #d1ecf1;
            border-color: #bee5eb;
        }
    </style>
</head>
<body class="bg-gray-100 flex flex-col min-h-screen">
    <header class="bg-gradient-to-r from-blue-600 to-indigo-700 text-white p-4 shadow-md">
        <div class="container mx-auto flex justify-between items-center">
            <h1 class="text-3xl font-bold rounded-md">
                <a href="{{ url_for('index') }}" class="hover:text-blue-200 transition duration-300">My Secure App</a>
            </h1>
            <nav>
                <ul class="flex space-x-6 text-lg">
                    {% if 'user_id' in session %}
                        <li><a href="{{ url_for('dashboard') }}" class="hover:text-blue-200 transition duration-300">Dashboard</a></li>
                        <li><a href="{{ url_for('logout') }}" class="hover:text-blue-200 transition duration-300">Logout</a></li>
                    {% else %}
                        <li><a href="{{ url_for('login') }}" class="hover:text-blue-200 transition duration-300">Login</a></li>
                    {% endif %}
                </ul>
            </nav>
        </div>
    </header>

    <main class="container mx-auto mt-8 p-4 flex-grow">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                <div class="mb-4">
                    {% for category, message in messages %}
                        <div class="flash {{ category }} rounded-md shadow-sm" role="alert">
                            {{ message }}
                        </div>
                    {% endfor %}
                </div>
            {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </main>

    <footer class="bg-gray-800 text-white p-4 text-center mt-8 shadow-inner">
        <div class="container mx-auto">
            <p>&copy; {{ now().year }} My Secure App. All rights reserved.</p>
        </div>
    </footer>
    <script>
        // Function to get current year for the footer
        function now() {
            return new Date().getFullYear();
        }
    </script>
</body>
</html>
"""

# templates/login.html
login_html_content = """
{% extends 'layout.html' %}

{% block title %}Login{% endblock %}

{% block content %}
<div class="flex items-center justify-center min-h-full py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8 p-10 bg-white rounded-xl shadow-lg border border-gray-200">
        <div class="text-center">
            <h2 class="mt-6 text-3xl font-extrabold text-gray-900 rounded-md">
                Log in to your account
            </h2>
        </div>
        <form class="mt-8 space-y-6" method="POST">
            <div class="rounded-md shadow-sm -space-y-px">
                <div>
                    <label for="email" class="sr-only">Email address</label>
                    <input id="email" name="email" type="email" autocomplete="email" required
                           class="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                           placeholder="Email address">
                </div>
                <div>
                    <label for="pin" class="sr-only">4-digit PIN</label>
                    <input id="pin" name="pin" type="password" maxlength="4" pattern="[0-9]{4}" title="Please enter a 4-digit number" required
                           class="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                           placeholder="4-digit PIN">
                </div>
            </div>

            <div class="flex items-center justify-between">
                <div class="text-sm">
                    <a href="{{ url_for('forgot_pin') }}" class="font-medium text-indigo-600 hover:text-indigo-500 transition duration-300">
                        Forgot/Set PIN?
                    </a>
                </div>
            </div>

            <div>
                <button type="submit"
                        class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition duration-300 shadow-md">
                    Sign in
                </button>
            </div>
        </form>
    </div>
</div>
{% endblock %}
"""

# templates/dashboard.html
dashboard_html_content = """
{% extends 'layout.html' %}

{% block title %}Dashboard{% endblock %}

{% block content %}
<div class="text-center p-8 bg-white rounded-xl shadow-lg border border-gray-200">
    <h2 class="text-4xl font-extrabold text-gray-900 mb-4">Welcome, {{ user_name }}!</h2>
    <p class="text-lg text-gray-600">You are successfully logged in to your personalized dashboard.</p>
    <div class="mt-8">
        <a href="{{ url_for('logout') }}" class="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-full shadow-sm text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition duration-300">
            Logout
        </a>
    </div>
</div>
{% endblock %}
"""

# templates/forgot_pin.html
forgot_pin_html_content = """
{% extends 'layout.html' %}

{% block title %}Forgot/Set PIN{% endblock %}

{% block content %}
<div class="flex items-center justify-center min-h-full py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8 p-10 bg-white rounded-xl shadow-lg border border-gray-200">
        <div class="text-center">
            <h2 class="mt-6 text-3xl font-extrabold text-gray-900 rounded-md">
                Forgot or Set PIN
            </h2>
            <p class="mt-2 text-sm text-gray-600">
                Enter your email address and we'll send you a link to set your PIN.
            </p>
        </div>
        <form class="mt-8 space-y-6" method="POST">
            <div class="rounded-md shadow-sm -space-y-px">
                <div>
                    <label for="email" class="sr-only">Email address</label>
                    <input id="email" name="email" type="email" autocomplete="email" required
                           class="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                           placeholder="Email address">
                </div>
            </div>

            <div>
                <button type="submit"
                        class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition duration-300 shadow-md">
                    Send PIN Set Link
                </button>
            </div>
        </form>
    </div>
</div>
{% endblock %}
"""

# templates/set_pin.html
set_pin_html_content = """
{% extends 'layout.html' %}

{% block title %}Set Your PIN{% endblock %}

{% block content %}
<div class="flex items-center justify-center min-h-full py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8 p-10 bg-white rounded-xl shadow-lg border border-gray-200">
        <div class="text-center">
            <h2 class="mt-6 text-3xl font-extrabold text-gray-900 rounded-md">
                Set Your New 4-digit PIN
            </h2>
        </div>
        <form class="mt-8 space-y-6" method="POST">
            <div class="rounded-md shadow-sm -space-y-px">
                <div>
                    <label for="new_pin" class="sr-only">New 4-digit PIN</label>
                    <input id="new_pin" name="new_pin" type="password" maxlength="4" pattern="[0-9]{4}" title="Please enter a 4-digit number" required
                           class="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                           placeholder="New 4-digit PIN">
                </div>
                <div>
                    <label for="confirm_pin" class="sr-only">Confirm 4-digit PIN</label>
                    <input id="confirm_pin" name="confirm_pin" type="password" maxlength="4" pattern="[0-9]{4}" title="Please confirm your 4-digit number" required
                           class="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                           placeholder="Confirm 4-digit PIN">
                </div>
            </div>

            <div>
                <button type="submit"
                        class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition duration-300 shadow-md">
                    Set PIN
                </button>
            </div>
        </form>
    </div>
</div>
{% endblock %}
"""

# templates/message.html
message_html_content = """
{% extends 'layout.html' %}

{% block title %}Message{% endblock %}

{% block content %}
<div class="text-center p-8 bg-white rounded-xl shadow-lg border border-gray-200">
    <h2 class="text-3xl font-extrabold text-gray-900 mb-4">Information</h2>
    <p class="text-lg text-gray-600">{{ message }}</p>
    <div class="mt-8">
        <a href="{{ url_for('login') }}" class="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-full shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition duration-300">
            Go to Login
        </a>
    </div>
</div>
{% endblock %}
"""

# Create the 'templates' directory and save the HTML content
os.makedirs('templates', exist_ok=True)

with open('templates/layout.html', 'w') as f:
    f.write(layout_html_content)

with open('templates/login.html', 'w') as f:
    f.write(login_html_content)

with open('templates/dashboard.html', 'w') as f:
    f.write(dashboard_html_content)

with open('templates/forgot_pin.html', 'w') as f:
    f.write(forgot_pin_html_content)

with open('templates/set_pin.html', 'w') as f:
    f.write(set_pin_html_content)

with open('templates/message.html', 'w') as f:
    f.write(message_html_content)

# To run this Flask app, save the above code as `app.py`
# and create a `templates` directory with the HTML files inside it.
# Then, from your terminal, navigate to the directory containing `app.py` and run:
# flask --app app run
# Or if you don't have flask in your path:
# python -m flask --app app run
# You can then access the application in your browser at http://127.0.0.1:5000/
#
# For initial testing, you can manually insert a user:
# 1. Run the app once to create database.db
# 2. Open `database.db` with a SQLite browser (e.g., DB Browser for SQLite)
# 3. Insert a user: INSERT INTO users (email, pin_hash) VALUES ('test@example.com', 'PBKDF2:sha256:260000$hN4pTq8xYvZwXc$b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3');
#    (The hash for '1234' is generated using `generate_password_hash('1234')`)
#    Alternatively, you can just go to /forgot_pin with a new email, and it will essentially "register" that email when you set the PIN.

# For demo purposes, let's create a dummy user upon first run if no users exist
