from os import error
from flask import render_template, request, flash, redirect, url_for
from app.forms import LoginForm, SignupForm
from smtplib import SMTP_SSL, SMTPAuthenticationError
from app import app, db
from .models import User
from flask_login import current_user, login_user, logout_user, login_required
from imap_tools import MailBox, AND
import imaplib
import email

class userEmail():
    def __init__(self, uid, subject, body, sender):
        self.uid = uid
        self.subject = subject
        self.body = body
        self.sender = sender


emails = []

@app.route('/')
@app.route('/index')
@login_required
def index():
    user = current_user.email
    pwd = current_user.password
    with MailBox('imap.gmail.com').login(user, pwd, 'INBOX') as mailbox:
        uids = [msg.uid for msg in mailbox.fetch()]
        bodies = [msg.text for msg in mailbox.fetch()]
        subjects = [msg.subject for msg in mailbox.fetch(AND(all=True))]
        senders = [msg.from_ for msg in mailbox.fetch()]
        length = 0
        uids.reverse()
        subjects.reverse()
        bodies.reverse()
        senders.reverse()
        for i in range(len(subjects)):
            email = userEmail(uids[i], subjects[i], bodies[i], senders[i]) 
            emails.append(email)
            length += 1

    return render_template('index.html', user=current_user.first_name, subjects=subjects, uids = uids, length1 = length)

@app.route('/view_email/<subject>', methods=['GET', 'POST'])
def view_email(subject):
    print(subject)
    return render_template('index.html')
    

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password')
            return redirect(url_for('login'))
        server = SMTP_SSL('smtp.gmail.com', 465)
        try:
            login_user(user)
            server.login(user.email, user.password)
            flash('Success! You logged into your email!', category='success')
            return redirect(url_for('index'))
        except SMTPAuthenticationError:
            flash('Error, these credentials are not valid.', category ='error')
            return redirect(url_for('login'))

    return render_template('login.html', form=form)

@app.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    form = SignupForm()

    if form.validate_on_submit():
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

@app.route('/viewEmail/<uid>')
@login_required
def view(uid):
    for email in emails:
        x = int(email.uid)
        y = int(uid)
        if x == y:
            return render_template('viewEmail.html', body=email.body, sender = email.sender, receiver = current_user.email, subject = email.subject)

    return redirect(url_for('login'))
'''
        if email.id == id:
            return render_template("viewEmail.html", subject = id)
        else:
            return render_template("index.html")'''


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))