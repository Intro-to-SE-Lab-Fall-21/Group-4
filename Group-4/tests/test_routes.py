import os
import tempfile
from flask_sqlalchemy import SQLAlchemy
import pytest
from flask import url_for, redirect
from flask_login import current_user, login_manager, login_user, LoginManager, logout_user
from app import create_app
from app import db as flask_db
from app.models import User, send_composed_message, Emails, authorize
from app.forms import LoginForm
from flask.testing import FlaskClient
from flask_migrate import Migrate, current


'''
========================================FIXTURES========================================
'''
@pytest.fixture(scope='module')
def current_app():
    app = create_app()
    with app.app_context():
        yield app

@pytest.fixture(scope='module')
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture(scope='module')
def authenticated_request(client):
    with client:
        yield login_user(User(email='tcctesteremail@gmail.com', password='123BigTest654', first_name='Tanner', last_name='Hess'))

# To be used with the getEmails and sendEmail functions
@pytest.fixture(scope='session')
def real_test_user():
    user = User.query.filter_by(email='tcctesteremail@gmail.com').first()
    return user

# To be used for all inbox tests.
@pytest.fixture(scope='session')
def inbox(real_test_user):
    inbox = Emails()
    inbox.getEmails(real_test_user)
    yield inbox

# To be used with the getEmails function
@pytest.fixture
def fake_test_user():
    return {'email' : 'notarealuser@gmail.com',
            'password' : 'fakepassword'
            }
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
    res = client.get('/viewEmail/<1>')
    assert res.status_code == 302
    res = client.get('/logout')
    assert res.status_code == 302


def test_send_message(client):
    pass

'''
def test_login_user(client):
    form = LoginForm()
    form.password.data = '123BigTest654'
    form.email.data = 'tcctesteremail@gmail.com'
    response = authorize(form)
    assert response == redirect(url_for('view.index'))
    '''

'''
========================================INBOX TESTS========================================
'''
# This tests the function SelectEmails() function within the Emails class works.
def test_select_emails(inbox):
    selected_email = inbox.selectEmail(5)
    assert 'This is' in selected_email.body
    selected_email = inbox.selectEmail(5000)
    assert selected_email == 'Failed'

# This tests that the clearAll () function within the Emails class works.
# This is particularly important for the apps security.
def test_clear_all(inbox):
    inbox.clearAll()
    assert len(inbox.subjects) == 0
    assert len(inbox.emails) == 0
    assert len(inbox.uids) == 0
