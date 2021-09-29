from os import error
from flask import render_template, request, flash, redirect
from flask.helpers import url_for
from app.forms import LoginForm, SignupForm
from smtplib import SMTP_SSL, SMTPAuthenticationError
from app import app
from .models import User
from app import db
from flask_login import LoginManager
from imap_tools import MailBox, AND

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html', email = [], user='Connor')

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
            return redirect(url_for('viewEmails'))
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


@app.route('/view-emails')
def viewEmails():
    user = "tcctesteremail@gmail.com"
    pwd = "123BigTest654"
    with MailBox('imap.gmail.com').login(user, pwd, 'INBOX') as mailbox:
        bodies = [msg.text for msg in mailbox.fetch()]

        mailbox = MailBox('imap.gmail.com')
        mailbox.login(user, pwd, initial_folder='INBOX')  # or mailbox.folder.set instead 3d arg
        subjects = [msg.subject for msg in mailbox.fetch(AND(all=True))]
        mailbox.logout()
        emails = []
        for i in range(len(subjects)):
            emailSubject = {
                    'subject': subjects[i],
                    'body': bodies[i]
                }
            emails.insert(0, emailSubject)
        
    return render_template('index.html', user="Connor", emails=emails)

