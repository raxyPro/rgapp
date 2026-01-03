import os
import sys

# Add the directory containing this file to the Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import your Flask app
from app import app as application  # <-- this line fixes the problem

# Optional Passenger-specific configurations
# os.environ['MY_SETTING'] = 'some_value'
