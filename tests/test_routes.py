import os
import re
import tempfile
from flask_sqlalchemy import SQLAlchemy
import pytest
from flask import url_for, redirect, request
from flask_login import current_user, login_manager, login_user, LoginManager, logout_user
from app import create_app
from app import db as flask_db
from app.models import User, send_composed_message, Emails, authorize
from app.forms import LoginForm
from flask.testing import FlaskClient
from flask_migrate import Migrate, current



'''
========================================FUNCTIONS========================================
'''

def login(client, username, password):
    return client.post('/login', data=dict(
        email=username,
        password=password,
        submit=True
    ), follow_redirects=True)


def logout(client):
    return client.get('/logout', follow_redirects=True)

def refresh(auth_client):
    return auth_client.get('/index/True', follow_redirects=True)


'''
========================================FIXTURES========================================
'''


@pytest.fixture(scope='module')
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        yield client


@pytest.fixture(scope='module')
def auth_client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED']=False
    with app.test_client() as client:
        login(client, "tcctesteremail2@gmail.com", "123BigTest654")
        yield client



# To be used with the getEmails and sendEmail functions
@pytest.fixture(scope='session')
def real_test_user():
    user = User.query.filter_by(email='tcctesteremail2@gmail.com').first()
    return user

# To be used for all inbox tests.
@pytest.fixture(scope='function')
def inbox(real_test_user):
    inbox = Emails()
    inbox.getEmails(real_test_user, "INBOX")
    yield inbox

@pytest.fixture(scope='session')
def trash(real_test_user):
    inbox = Emails()
    inbox.getEmails(real_test_user, "[Gmail]/Trash")
    yield inbox

# To be used with the getEmails function
@pytest.fixture
def fake_test_user():
    return {'email' : 'notarealuser@gmail.com',
            'password' : 'fakepassword'
            }



'''
========================================NOTES TESTS========================================
'''
def test_notes(auth_client):
    res = auth_client.get('/notes')
    assert b"Grocery List" in res.data


'''
========================================HTML TESTS========================================
'''
# This is a generic test for each of our routes. We assume that there is no current user instance and therefore
# the routes status code are 200, 200, and then all 302 (redirects).

def test_html_logged_out(client):
    res = client.get('/sign-up')
    assert res.status_code == 200
    res = client.get('/login')
    assert res.status_code == 200
    res = client.get('/index/<refresh>')
    assert res.status_code == 302
    res = client.get('/compose')
    assert res.status_code == 302
    res = client.get('/viewEmail/<1>/False/False/False')
    assert res.status_code == 302
    res = client.get('/logout')
    assert res.status_code == 302


def test_send_message(client):
    pass



def test_login(client):
    rv = login(client, 'tcctesteremail2@gmail.com', '123BigTest654')
    assert rv.status_code==200
    assert b'Hello' in rv.data


def test_html_logged_in(auth_client):
    #login(client, 'tcctesteremail@gmail.com', '123BigTest654')
    res = auth_client.get('/sign-up')
    assert res.status_code == 302
    res = auth_client.get('/login')
    assert res.status_code == 302
    res = auth_client.get('/index/<refresh>')
    assert res.status_code == 200
    res = auth_client.get('/compose')
    assert res.status_code == 200
    res = auth_client.get('/viewEmail/1/False/False/False')
    assert res.status_code == 200
    res = auth_client.get('/logout')
    assert res.status_code == 302


'''
========================================INBOX TESTS========================================
'''
# This tests the function SelectEmails() function within the Emails class works.

def test_move_to_trash(real_test_user):
    inbox = Emails()
    inbox.getEmails(real_test_user, "INBOX")
    uids = inbox.uids
    uidMax = max(uids)

    inbox.moveToTrash(real_test_user, uidMax)

    inbox.clearAll()
    inbox.getEmails(real_test_user, "INBOX")
    newMax = max(inbox.uids)  
    assert newMax != uidMax


def test_remove_to_trash(real_test_user):
    inbox = Emails()
    inbox.getEmails(real_test_user, "[Gmail]/Trash")
    uids = inbox.uids
    uidMax = max(uids)

    inbox.removeFromTrash(real_test_user, uidMax)
    
    inbox.clearAll()
    inbox.getEmails(real_test_user, "[Gmail]/Trash")
    newMax = max(inbox.uids) 
    assert newMax != uidMax



@pytest.mark.parametrize('value', (1, 50000))
def test_select_emails(inbox, value):
    if value == 1:
        selected_email = inbox.selectEmail(value)
        assert 'Hi Test2' in selected_email.body
    elif value == 50000:
        selected_email = inbox.selectEmail(value)
        assert selected_email == 'Failed'

    
# This tests that the clearAll () function within the Emails class works.
# This is particularly important for the apps security.
def test_clear_all(inbox):
    inbox.clearAll()
    assert len(inbox.subjects) == 0
    assert len(inbox.emails) == 0
    assert len(inbox.uids) == 0



'''
========================================COMPOSE/DELETE TEST========================================
'''


def test_compose(auth_client):
    data = dict(email_to='tcctesteremail2@gmail.com', subject="This is a test", body='This is an autiomatic message sent for testing', importNote=False, submit=True, note=None, attachment=None)
    res = auth_client.post('/compose', data=data, follow_redirects=True)
    assert res.status_code == 200





def test_delete(real_test_user):
    inbox = Emails()
    inbox.getEmails(real_test_user, "INBOX")
    uids = inbox.uids
    uidMax = max(uids)

    inbox.moveToTrash(real_test_user, uidMax)
    inbox.clearAll()
    inbox.getEmails(real_test_user, "[Gmail]/Trash")

    uids = inbox.uids
    uidMax = max(uids)

    inbox.deleteEmail(real_test_user, uidMax)
    inbox.clearAll()
    inbox.getEmails(real_test_user, "[Gmail]/Trash")
    newUid = max(inbox.uids)
    assert uidMax != newUid




