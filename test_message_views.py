"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


from cgitb import html
import os
from unittest import TestCase
from sqlalchemy import exc, orm

from models import db, connect_db, Message, User

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database


os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app, CURR_USER_KEY

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()

        self.client = app.test_client()

        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)

        self.testuser_id = 1
        self.testuser.id = self.testuser_id

        db.session.commit()

        self.client = app.test_client()

        self.secondUser = User.signup(username= "user",
                                    email="email@gmail.com",
                                    password="bogus",
                                    image_url=None)
        
        self.secondUser_id = 2
        self.secondUser.id = self.secondUser_id
        
        db.session.commit()

        m1 = Message(id=1,text='test message', user_id=2)

        db.session.add(m1)
        db.session.commit()
    
    def test_add_message(self):
        """Can use add a message?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # Now, that session setting is saved, so we can have
            # the rest of ours test

            resp = c.post("/messages/new", data={"text": "Hello"})

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)

            msg = Message.query.one()
            self.assertEqual(msg.text, "Hello")

    def test_show_message(self):
        """View previously created message"""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.secondUser_id

            resp = c.get('/messages/1')
            html = resp.get_data(as_text=True)

            self.assertIn('test message',html)
            self.assertEqual(resp.status_code,200)

    def test_invalid_message(self):
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.secondUser_id
            
        resp = c.get('/messages/1234')

        self.assertEqual(resp.status_code, 404)


    def test_logged_out_add_message(self):
        """Can logged out user add message?"""
        with self.client as c:
        # CURR_USER_KEY cannot be in the session key

            resp = c.post("/messages/new", data={"text": "Hello"}, follow_redirects=True)
            html = resp.get_data(as_text=True)

            # Make sure it redirects
            self.assertEqual(resp.status_code, 200)
            self.assertIn('Access unauthorized', html)



    def test_valid_delete_message(self):
        """delete message while logged in"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

        new_msg = Message(id=2,text='additional message', user_id=self.testuser_id)
        
        db.session.add(new_msg)
        db.session.commit()

        # msg_to_delete = Message.query.get(1)

        resp = c.post('/messages/2/delete')

        test_deleted_msg = Message.query.get(2)

        self.assertIsNone(test_deleted_msg)


    def test_logged_out_message_delete_redirect(self):
        """Test if logged out user is redirected when deleting a message"""
        with self.client as c:
        # CURR_USER_KEY cannot be in the session key
            new_msg = Message(id=10, text='test message', user_id=self.testuser.id)
        
            db.session.add(new_msg)
            db.session.commit()

            resp = c.post(f"/messages/{new_msg.id}/delete", follow_redirects=True)
            html = resp.get_data(as_text=True)

            msg_state = Message.query.get(10)

            self.assertIsNotNone(msg_state)

            # Make sure it redirects
            self.assertEqual(resp.status_code, 200)
            self.assertIn('Access unauthorized', html)



    def test_logged_out_message_delete_response(self):
        """Test if logged out user can delete message"""
        with self.client as c:
        # CURR_USER_KEY cannot be in the session key to test logged out condition
            new_msg = Message(text='test message', user_id=self.testuser.id)
        
            db.session.add(new_msg)
            db.session.commit()

            resp = c.post(f"/messages/{new_msg.id}/delete", follow_redirects=True)

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('<div class="alert alert-danger">Access unauthorized.</div>', html)

    
    def test_add_message_to_different_user(self):
        """While logged in, test you cannot add a message to a different user"""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY]=self.testuser_id

            # Test post to a different user
            resp = c.post('/messages/new',data={"text":"new message text", "user_id":f"{self.secondUser_id}"}, follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertIn('Access unauthorized',html)
            self.assertEqual(resp.status_code, 200)
    
    def test_delete_message_from_different_user(self):
        """While logged in, test deleting message of a different user"""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY]=self.testuser_id

            # message '1' is from a different user than testuser
            resp = c.post('/messages/1/delete', follow_redirects=True)
            html = resp.get_data(as_text=True)

            user1 = User.query.get(2)
            messages = user1.messages

            self.assertNotEqual(len(messages),0)
            self.assertEqual(resp.status_code,200)

    def test_delete_message_from_different_user_response(self):
        """While logged in, test deleting message of a different user"""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY]=self.testuser.id

            resp = c.post('/messages/1/delete', follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertIn('<div class="alert alert-danger">Access unauthorized.</div>', html)
            self.assertEqual(resp.status_code, 200)








