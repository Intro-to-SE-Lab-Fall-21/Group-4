from os import error
from flask import render_template, request, flash
from app.forms import LoginForm, SignupForm
from smtplib import SMTP_SSL, SMTPAuthenticationError
from app import app
from .models import User
from . import db
from flask_login import LoginManager

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html', user='Connor')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if request.method == 'POST':
        email = form.email.data
        password = form.password.data

        server = SMTP_SSL('smtp.gmail.com', 465)
        try:
            server.login(email, password)
            flash('Success! You logged into your email!', category='success')
        except SMTPAuthenticationError:
            flash('Error, these credentials are not valid.', category ='error')

    return render_template('login.html', form=form)

@app.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    form = SignupForm()

    if request.method == 'POST':
        email = form.email.data
        first_name = form.first_name.data
        last_name = form.last_name.data
        password1 = form.password1.data
        password2 = form.password2.data
        server = SMTP_SSL('smtp.gmail.com', 465)

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Error! This email already has an account', category='error')
        elif password1 != password2:
            flash('Error! Passwords do not match', category='error')
        else:
            try:
                server.login(email, password1)
                new_user = User(email=email, password=password1, first_name=first_name, last_name=last_name)
                db.session.add(new_user)
                db.session.commit()
                flash('Success! You logged into your email!', category='success')
            except SMTPAuthenticationError:
                flash('Error, these credentials are not valid.', category ='error')

    return render_template("signup.html", form=form)





