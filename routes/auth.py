from flask import Blueprint, render_template, redirect, url_for, flash, request
from extensions import db, bcrypt, login_manager
from models import User
from forms import RegisterForm, LoginForm
from flask_login import login_user, logout_user, login_required, current_user

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
@auth_bp.route('/home')
def home():
    return render_template('home.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash("That username already exists. Please choose a different one.", "error")
            return render_template('register.html', form=form)

        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        new_user = User(username=form.username.data, password=hashed_password)
        try:
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)  
            flash("Registration successful! You are now logged in.", "success")
            return redirect(url_for('apps.dashboard'))
        except Exception:
            db.session.rollback()
            flash("An error occurred during registration. Please try again.", "error")

    return render_template('register.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('apps.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if not user:
            flash("Username does not exist.", "error")
        elif not bcrypt.check_password_hash(user.password, form.password.data):
            flash("Incorrect password.", "error")
        else:
            login_user(user)
            flash("Logged in successfully!", "success")
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('apps.dashboard'))

    return render_template('login.html', form=form)



@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

from extensions import login_manager
from models import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))