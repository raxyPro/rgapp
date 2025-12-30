from datetime import datetime
from typing import Optional

from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from passlib.hash import bcrypt
import uuid