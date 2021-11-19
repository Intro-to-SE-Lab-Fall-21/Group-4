import os
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

'''
========================================FIXTURES========================================
'''


@pytest.fixture(scope='session')
def app(request):
    """Session-wide test `Flask` application."""
    app = create_app()
    app.config['TESTING']=True
    app.config['WTF_CSRF_ENABLED']=False
    app.config['PRESERVE_CONTEXT_ON_EXCEPTION']=False

    # Establish an application context before running the tests.
    ctx = app.app_context()
    ctx.push()

    def teardown():
        ctx.pop()

    request.addfinalizer(teardown)
    return app


@pytest.fixture(scope='module')
def current_app():
    app = create_app()
    with app.app_context():
        yield app

@pytest.fixture(scope='module')
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        yield client


@pytest.fixture(scope='module')
def authenticated_client(client):
    login(client, "tcctesteremail@gmail.com", '123BigTest654')
    yield client

# To be used with the getEmails and sendEmail functions
@pytest.fixture(scope='session')
def real_test_user():
    user = User.query.filter_by(email='tcctesteremail@gmail.com').first()
    return user

# To be used for all inbox tests.
@pytest.fixture(scope='session')
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


def test_add_category_post(app):
    """Does add category post a new category?"""
    TESTEMAIL = "tcctesteremail@gmail.com"
    TESTPASS = '123BigTest654'
    user = User.query.filter(User.email==TESTEMAIL).first()
    form = LoginForm(email=TESTEMAIL, password=TESTPASS)
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess['MAIL_USERNAME'] = TESTEMAIL
            sess['MAIL_PASSWORD'] = TESTPASS
            response = c.post(
                '/login', data=form.data, follow_redirects=True)
        assert response.status_code == 200
        assert b"Hello" in response.data



def test_authentication(real_test_user):
    client = create_app()
    client.config['TESTING']=True
    with client.test_request_context('/login'):
        test_user = real_test_user
        @client.login_manager.request_loader
        def load_user_from_request(request):
            return test_user
        
        assert request.status_code == 302



def test_login_user(client):
    form = LoginForm()
    form.password.data = '123BigTest654'
    form.email.data = 'tcctesteremail@gmail.com'
    response = authorize(form)
    assert response.status_code==302
    

def test_login(client):
    rv = login(client, 'tcctesteremail@gmail.com', '123BigTest654')
    assert rv.status_code==200
    assert b'Hello' in rv.data

'''
def test_html_logged_in(authenticated_client):
    res = authenticated_client.get('/sign-up')
    assert res.status_code == 302
    res = authenticated_client.get('/login')
    assert res.status_code == 302
    res = authenticated_client.get('/index/<refresh>')
    assert res.status_code == 200
    res = authenticated_client.get('/compose')
    assert res.status_code == 200
    res = authenticated_client.get('/viewEmail/<1>/False/False/False')
    assert res.status_code == 200
    res = authenticated_client.get('/logout')
    assert res.status_code == 200
'''

'''
========================================INBOX TESTS========================================
'''
# This tests the function SelectEmails() function within the Emails class works.
@pytest.mark.parametrize('value', (9, 50000))
def test_select_emails(inbox, value):
    if value == 9:
        selected_email = inbox.selectEmail(value)
        assert 'I was wondering' in selected_email.body
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
