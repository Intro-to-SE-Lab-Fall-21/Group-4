from os import error
from flask import render_template, request, flash, redirect, url_for, Blueprint, current_app
from app.forms import ForwardReplyTrashForm, LoginForm, SignupForm, ComposeForm
from smtplib import SMTP_SSL, SMTPAuthenticationError
from app import  db
from .models import Note, User, Emails, download_attachment, send_composed_message, authorize, userEmail
from flask_login import current_user, login_user, logout_user, login_required
from imap_tools import MailBox, AND
from flask_mail import Message, Mail
from mimetypes import guess_type
import sys
from bs4 import BeautifulSoup

view = Blueprint('view', __name__)
user_emails = Emails()
user_deleted_emails = Emails()

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
            return redirect(url_for('view.searchResults', search=searchQuery, deleted=False))

        else:
            return redirect(url_for('view.index'))

    # adds refresh functionality to reload all the emails
    if not user_emails.emails or refresh == "True":
        user_emails.clearAll()

        user_deleted_emails.clearAll()
        user_emails.getEmails(current_user, 'INBOX')
        user_deleted_emails.getEmails(current_user, '[Gmail]/Trash')
    return render_template('index.html', search = 0, deleted = False, user=current_user.first_name, subjects = user_emails.subjects, uids = user_emails.uids, length1 = len(user_emails.subjects))


@view.route('/trash/<refresh>', methods=['GET', 'POST'])
@login_required
def trash(refresh="False"):
    searchQuery = ""

    # checks to see if the user searches through the emails
    if request.method == 'POST':
        searchQuery = request.form.get('search')
        if searchQuery:
            return redirect(url_for('view.searchResults', search=searchQuery, deleted=True))

        else:
            return redirect(url_for('view.trash', refresh='False'))

    if not user_emails.emails or refresh == "True":
        user_emails.clearAll()
        user_deleted_emails.clearAll()
        user_emails.getEmails(current_user, 'INBOX')
        user_deleted_emails.getEmails(current_user, '[Gmail]/Trash')
    return render_template('trash.html', search = 0, deleted = True, subjects = user_deleted_emails.subjects, uids = user_deleted_emails.uids, length1 = len(user_deleted_emails.subjects))


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
    if current_user.is_authenticated:
        return redirect(url_for('view.index'))

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
                flash('Success! You created an account!', category='success')
            # fails if user's info does not match up with their email's info
            except SMTPAuthenticationError:
                flash('Error, these credentials are not valid.', category ='error')
    return render_template("signup.html", form=form)


# views specific emails
@view.route('/viewEmail/<uid>/<forward>/<reply_flag>/<deleted>', methods=['GET', 'POST'])
@login_required
def viewEmail(uid, forward, reply_flag, deleted="False"):
    form = ComposeForm()
    trashForm = ForwardReplyTrashForm()
    if deleted == 'False':
        email = user_emails.selectEmail(uid)
    else:
        email = user_deleted_emails.selectEmail(uid)

    num_of_att = len(email.attachments)
    
    # Logic to pre-load the compose form based on whether reply or forward == "True"
    if forward == "True" and (form.body.data == None):
        form.body.data = email.body
        form.subject.data = 'FW: (' + email.sender + ') ' + email.subject
    elif reply_flag == "True":
            form.subject.data = email.subject
            form.email_to.data = email.sender

    # Logic for importing note into message
    if request.method=='POST' and (reply_flag=="True" or forward=="True"):
        if not trashForm.trash.data and not trashForm.untrash.data:
            if request.form['note'] != "None":
                noteid = request.form['note']
                note = Note.query.get(noteid)
                title = "<html><body><b>" + "Title: " + note.title + "<b></body></html>"
                print("is working")
                form.body.data = form.body.data + title + note.data
                return render_template('viewEmail.html', deleted=deleted, trashForm = trashForm, form=form, isHTML = email.isHTML, body = email.body, sender = email.sender, receiver = current_user.email, subject = email.subject, uid = email.uid, forward=forward, reply_flag=reply_flag, attachments=email.attachments, attachments_length=num_of_att, user=current_user)

    if uid:
        # sends the message ("and form.submit" protects from accidentally sending message when importing notes)
        if form.validate_on_submit() and form.submit:
            response = send_composed_message(form)
            if response is not None:
                if response == True:
                    flash('Success! Youre message has been sent!', category='success')
                    return redirect(url_for('view.viewEmail', uid=uid, forward=False, reply_flag=False, deleted = deleted))
                else:
                    flash('Uh oh! Something went wrong.', category='error')
                    return render_template('viewEmail.html', deleted = deleted, trashForm = trashForm, form=form, isHTML = email.isHTML, body = email.body, sender = email.sender, receiver = current_user.email, subject = email.subject, uid = email.uid, forward=forward, reply_flag=reply_flag, attachments=email.attachments, attachments_length=num_of_att, user=current_user)

        
        if trashForm.is_submitted():
            if trashForm.trash.data:
                user_emails.moveToTrash(current_user, uid)
                return redirect(url_for('view.index', refresh=True))
            if trashForm.untrash.data:
                user_deleted_emails.removeFromTrash(current_user, uid)
                return redirect(url_for('view.trash', refresh=True))
            if trashForm.delete.data:
                user_deleted_emails.deleteEmail(current_user, uid)
                return redirect(url_for('view.trash', refresh=True))


        return render_template('viewEmail.html', deleted=deleted, trashForm=trashForm, form=form, isHTML = email.isHTML, body = email.body, sender = email.sender, receiver = current_user.email, subject = email.subject, uid = email.uid, forward=forward, reply_flag=reply_flag, attachments=email.attachments, attachments_length=num_of_att, user=current_user)

    return redirect(url_for('view.login'))


# Route to download aa particulat attachment of a particular email (specified by the attachments index in the email)
@view.route('download/<index>/<uid>/<deleted>')
def download(index, uid, deleted="False"):
    if deleted == "False":
        email = user_emails.selectEmail(uid)
    else:
        email = user_deleted_emails.selectEmail(uid)
    index = int(index)
    attachment = email.attachments[index]
    download_attachment(attachment)
    flash('Success! Check your downloads folder', category='success')
    return redirect(url_for('view.viewEmail', uid=uid, forward=False, reply_flag=False, deleted=deleted))


# allows user to compose and edit emails
@view.route('/compose', methods=['GET', 'POST'])
@login_required
def compose():
    # Presents form for email and allows user to send
    form = ComposeForm()
    if request.method=='POST':
        if request.form['note'] != "None":
            noteid = request.form['note']
            note = Note.query.get(noteid)
            title = "<html><body><b>" + "Title: " + note.title + "<b></body></html>"
            form.body.data = form.body.data + title + note.data
            return render_template('compose.html', form=form, user=current_user)
        if form.validate_on_submit():
            flag = send_composed_message(form)
            if flag == True:
                flash('Success! Your email has been sent.', category='success')
                return redirect(url_for('view.index'))

            else:
                flash('An unexpected error occured. Please try again', category='error')
                print('Whew!', sys.exc_info()[0], 'occurred.')

    return render_template('compose.html', form=form, user=current_user)


# shows search results
@view.route('/searchResults/<search>/<deleted>', methods=['GET', 'POST'])
@login_required
def searchResults(search, deleted="False"):
    searchQuery = ""
    searchResultsSubjs = []
    searchResultsUids = []
    # loops through emails and finds ones with matching subjects
    if deleted == 'False':
        for email in user_emails.emails:
            subj = email.subject.lower()
            search = search.lower()
            if search in subj:
                searchResultsSubjs.append(email.subject)
                searchResultsUids.append(email.uid)
    else:
        for email in user_deleted_emails.emails:
            subj = email.subject.lower()
            search = search.lower()
            if search in subj:
                searchResultsSubjs.append(email.subject)
                searchResultsUids.append(email.uid)

    # allows the user to search from this page too
    if request.method == 'POST':
        searchQuery = request.form.get('search')
        if searchQuery:
            return redirect(url_for('view.searchResults', search=searchQuery, deleted = deleted))
        else:
            if deleted == 'True':
                return redirect(url_for('view.trash', refresh="False"))
            else:
                return redirect(url_for('view.index'))
    
    return render_template('searchResults.html', deleted=deleted, search=search, user = current_user.first_name, subjects = searchResultsSubjs, uids = searchResultsUids, length1 = len(searchResultsUids))


# Note route: Displays the user's notes, allows the user to add/edit/delete notes.
@view.route('/notes', methods=['GET', 'POST'])
@login_required
def notes():
    return render_template("notes.html", user=current_user)


# Deleted-notes Route: Displays the nots the user has deleted
@view.route('/deleted-notes', methods=['GET', 'POST'])
@login_required
def deletedNotes():
    return render_template("deleted-notes.html", user=current_user)


# View-Note Route: Displays a particular note for editing
@view.route('/edit-note/<id>', methods=['GET', 'POST'])
@login_required
def editNote(id):
    note = Note.query.get(id)
    if request.method == 'POST':
        new_data = request.form.get('note')
        new_title = request.form.get('title')
        
        if len(new_data) < 1:
            flash('Note body is too short!', category='error')
        elif len(new_title) < 1:
            flash('Note title is too short!', category='error')
        else:
            note.title = new_title
            note.data = new_data
            db.session.commit()
            flash('Note updated!', category='success')
            return redirect(url_for('view.notes', user=current_user))
    return render_template("edit-note.html", user=current_user, id=id, note=note)


@view.route('/add-note', methods=['GET', 'POST'])
def addNote():
    if request.method == 'POST':
        data = request.form.get('note')
        title = request.form.get('title')

        if len(data) < 1:
            flash('Note is too short!', category='error')
        else:
            new_note = Note(data=data, title=title, deleted=False, user_id=current_user.id)
            db.session.add(new_note)
            db.session.commit()
            flash('Note added!', category='success')
            return redirect(url_for('view.notes', user=current_user))
    return render_template("add-note.html", user=current_user)


@view.route('/delete-note/<id>')
def deleteNote(id):
    note = Note.query.get(id)
    if note:
        if note.user_id == current_user.id:
            if note.deleted == True:
                flash('Note permanently deleted!', category='success')
                db.session.delete(note)
                db.session.commit()
                return redirect(url_for('view.deletedNotes', user=current_user))
            else:
                note.deleted = True
                flash('Note deleted!', category='success')
                db.session.commit()
    return redirect(url_for('view.notes', user=current_user))


# Route to recover deleted notes 
@view.route('/recover-note/<id>')
def recoverNote(id):
    note = Note.query.get(id)
    if note:
        if note.user_id == current_user.id:
            note.deleted = False
            flash('Note recovered!', category='success')
            db.session.commit()
    return redirect(url_for('view.deletedNotes', user=current_user))

# logs the user out
@view.route('/logout')
@login_required
def logout():
    user_emails.clearAll()
    user_deleted_emails.clearAll()
    logout_user()
    return redirect(url_for('view.login'))

