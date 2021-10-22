from os import error
from flask import render_template, request, flash, redirect, url_for, Blueprint, current_app
from app.forms import ForwardReplyForm, LoginForm, SignupForm, ComposeForm
from smtplib import SMTP_SSL, SMTPAuthenticationError
from app import  db
from .models import User, Emails, send_composed_message, authorize
from flask_login import current_user, login_user, logout_user, login_required
from imap_tools import MailBox, AND
from flask_mail import Message, Mail
from mimetypes import guess_type
import sys
from bs4 import BeautifulSoup

view = Blueprint('view', __name__)


user_emails = Emails()
'''
def getEmails():
    user = current_user.email
    pwd = current_user.password
    with MailBox('imap.gmail.com').login(user, pwd, 'INBOX') as mailbox:
        uids = [msg.uid for msg in mailbox.fetch()]
        bodies = [msg.text for msg in mailbox.fetch()]
        bodiesHTML = [msg.html for msg in mailbox.fetch()]
        subjects = [msg.subject for msg in mailbox.fetch(AND(all=True))]
        senders = [msg.from_ for msg in mailbox.fetch()]
        uids.reverse()
        subjects.reverse()
        bodiesHTML.reverse()
        bodies.reverse()
        senders.reverse()
        for i in range(len(subjects)):
            email = userEmail(uids[i], subjects[i], bodiesHTML[i], senders[i], False) 
            soup = BeautifulSoup(email.body, 'html.parser')
            email.body = soup.decode_contents()
            if(bodiesHTML[i] == ""):
                email.body = bodies[i]
                email.isHTML = False
            else:
                email.isHTML = True
            emails.append(email) '''

@view.route('/', methods=['GET', 'POST'])
@view.route('/index/<refresh>', methods=['GET','POST'])
@login_required
def index(refresh="False"):
    search1 = ""
    if request.method == 'POST':
        search1 = request.form.get('search')
        if search1:
            return redirect(url_for('view.searchResults', search=search1))
        else:
            return redirect(url_for('view.index'))

    if not user_emails.emails or refresh == "True":
        user_emails.clearAll
        user_emails.getEmails(current_user)
    return render_template('index.html', search = 0, user=current_user.first_name, subjects = user_emails.subjects, uids = user_emails.uids, length1 = len(user_emails.subjects))


@view.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('view.index'))

    form = LoginForm()
    if form.validate_on_submit():
        return authorize(form)
    return render_template('login.html', form=form)


@view.route('/sign-up', methods=['GET', 'POST'])
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


@view.route('/viewEmail/<uid>', methods=['GET', 'POST'])
@login_required
def viewEmail(uid):
    forward = False
    reply_flag = False
    form = ForwardReplyForm()

    email = user_emails.selectEmail(uid)

    if uid:
        if form.is_submitted():
            if form.forward.data:
                forward = True
                reply_flag = False
                form.compose.body.data = email.body
                form.compose.subject.data = 'FW: (' + email.sender + ') ' + email.subject
                return render_template('viewEmail.html', form=form, isHTML = email.isHTML, body = email.body, sender = email.sender, receiver = current_user.email, subject = email.subject, uid = email.uid, forward=forward, reply_flag=reply_flag)
            elif form.reply.data:
                reply_flag = True
                forward = False
                form.compose.subject.data = email.subject
                form.compose.email_to.data = email.sender
                return render_template('viewEmail.html', form=form, isHTML = email.isHTML, body = email.body, sender = email.sender, receiver = current_user.email, subject = email.subject, uid = email.uid, forward=forward, reply_flag=reply_flag)
            elif form.compose.validate_on_submit():
                response =  send_composed_message(form.compose)
                if response is not None:
                    return response

        return render_template('viewEmail.html', form=form, isHTML = email.isHTML, body = email.body, sender = email.sender, receiver = current_user.email, subject = email.subject, uid = email.uid, forward=forward, reply_flag=reply_flag)
    return redirect(url_for('view.login'))


@view.route('/compose', methods=['GET', 'POST'])
@login_required
def compose():
    form = ComposeForm()
    if form.validate_on_submit():
        flag = send_composed_message(form)
        if flag == True:
            flash('Success! Your email has been sent.', category='success')
            return redirect(url_for('view.index'))
        else:
            flash('An unexpected error occured. Please try again', category='error')
            print('Whew!', sys.exc_info()[0], 'occurred.')
    return render_template('compose.html', form=form)

@view.route('/searchResults/<search>', methods=['GET', 'POST'])
@login_required
def searchResults(search):
    search1 = ""
    searchResultsSubjs = []
    searchResultsUids = []
    for email in emails:
        subj = email.subject.lower()
        search = search.lower()
        if search in subj:
            searchResultsSubjs.append(email.subject)
            searchResultsUids.append(email.uid)

    if request.method == 'POST':
        search1 = request.form.get('search')
        if search1:
            return redirect(url_for('searchResults', search=search1))
        else:
            return redirect(url_for('index'))
    
    return render_template('searchResults.html', search=search, user = current_user.first_name, subjects = searchResultsSubjs, uids = searchResultsUids, length1 = len(searchResultsUids))


@view.route('/logout')
@login_required
def logout():
    user_emails.clearAll()
    logout_user()
    return redirect(url_for('view.login'))

