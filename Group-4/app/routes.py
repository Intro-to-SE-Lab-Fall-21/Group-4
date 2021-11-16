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

# loads in the user's emails and displays links to read them
@view.route('/', methods=['GET', 'POST'])
@view.route('/index/<refresh>', methods=['GET','POST'])
@login_required
def index(refresh="False"):
    searchQuery = ""

    # checks to see if the user searches through the emails
    if request.method == 'POST':
        searchQuery = request.form.get('search')
        if searchQuery:
            return redirect(url_for('view.searchResults', search=searchQuery))

        else:
            return redirect(url_for('view.index'))

    # adds refresh functionality to reload all the emails
    if not user_emails.emails or refresh == "True":
        user_emails.clearAll
        user_emails.getEmails(current_user)

    return render_template('index.html', search = 0, user=current_user.first_name, subjects = user_emails.subjects, uids = user_emails.uids, length1 = len(user_emails.subjects))


# handles login for the user
@view.route('/login', methods=['GET', 'POST'])
def login():
    # checks if user is already authenticated and if they are redirects them to index
    if current_user.is_authenticated:
        return redirect(url_for('view.index'))

    # makes login form and detects if its valid
    form = LoginForm()
    if form.validate_on_submit():
        return authorize(form)

    return render_template('login.html', form=form)

# make sign up form so users can be added to the database
@view.route('/sign-up', methods=['GET', 'POST'])
def sign_up():

    # signs up users and makes sure form is valid
    form = SignupForm()
    if form.validate_on_submit():
        email = form.email.data
        first_name = form.first_name.data
        last_name = form.last_name.data
        password1 = form.password1.data
        password2 = form.password2.data
        server = SMTP_SSL('smtp.gmail.com', 465)

        # checks for user already in database
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Error! This email already has an account', category='error')
        # checks if passwords match
        elif password1 != password2:
            flash('Error! Passwords do not match', category='error')
        else:
            # adds user to database
            try:
                server.login(email, password1)
                new_user = User(email=email, password=password1, first_name=first_name, last_name=last_name)
                db.session.add(new_user)
                db.session.commit()
                flash('Success! You logged into your email!', category='success')
            # fails if user's info does not match up with their email's info
            except SMTPAuthenticationError:
                flash('Error, these credentials are not valid.', category ='error')
    return render_template("signup.html", form=form)


# views specific emails
@view.route('/viewEmail/<uid>', methods=['GET', 'POST'])
@login_required
def viewEmail(uid):
    forward = False
    reply_flag = False
    form = ForwardReplyForm()
    email = user_emails.selectEmail(uid)

    if uid:
        if form.is_submitted():
            # allows the user to forward their email
            if form.forward.data:
                forward = True
                reply_flag = False
                form.compose.body.data = email.body
                form.compose.subject.data = 'FW: (' + email.sender + ') ' + email.subject
                return render_template('viewEmail.html', form=form, isHTML = email.isHTML, body = email.body, sender = email.sender, receiver = current_user.email, subject = email.subject, uid = email.uid, forward=forward, reply_flag=reply_flag)

            # allows the user to reply to emails
            elif form.reply.data:
                reply_flag = True
                forward = False
                form.compose.subject.data = email.subject
                form.compose.email_to.data = email.sender
                return render_template('viewEmail.html', form=form, isHTML = email.isHTML, body = email.body, sender = email.sender, receiver = current_user.email, subject = email.subject, uid = email.uid, forward=forward, reply_flag=reply_flag)

            # sends the message
            elif form.compose.validate_on_submit():
                response =  send_composed_message(form.compose)
                if response is not None:
                    return response

        return render_template('viewEmail.html', form=form, isHTML = email.isHTML, body = email.body, sender = email.sender, receiver = current_user.email, subject = email.subject, uid = email.uid, forward=forward, reply_flag=reply_flag)

    return redirect(url_for('view.login'))


# allows user to compose and edit emails
@view.route('/compose', methods=['GET', 'POST'])
@login_required
def compose():
    # presents form for email and allows user to send
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


# shows search results
@view.route('/searchResults/<search>', methods=['GET', 'POST'])
@login_required
def searchResults(search):
    searchQuery = ""
    searchResultsSubjs = []
    searchResultsUids = []
    # loops through emails and finds ones with matching subjects
    for email in user_emails.emails:
        subj = email.subject.lower()
        search = search.lower()
        if search in subj:
            searchResultsSubjs.append(email.subject)
            searchResultsUids.append(email.uid)

    # allows the user to search from this page too
    if request.method == 'POST':
        searchQuery = request.form.get('search')
        if searchQuery:
            return redirect(url_for('view.searchResults', search=searchQuery))
        else:
            return redirect(url_for('view.index'))
    
    return render_template('searchResults.html', search=search, user = current_user.first_name, subjects = searchResultsSubjs, uids = searchResultsUids, length1 = len(searchResultsUids))


# logs the user out
@view.route('/logout')
@login_required
def logout():
    user_emails.clearAll()
    logout_user()
    return redirect(url_for('view.login'))
