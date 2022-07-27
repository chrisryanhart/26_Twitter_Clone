"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


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

        db.session.commit()

        self.client = app.test_client()

        self.secondUser = User.signup(username= "user",
                                    email="email@gmail.com",
                                    password="bogus",
                                    image_url=None)

        db.session.commit()

        m1 = Message(text='test message', user_id=2)

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

    def test_logged_out_add_message(self):
        """Can logged out user add message?"""
        with self.client as c:
        # CURR_USER_KEY cannot be in the session key

            resp = c.post("/messages/new", data={"text": "Hello"})

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)

            with self.assertRaises(orm.exc.NoResultFound):
                msg = Message.query.one()


    def test_valid_delete_message(self):
        """delete message while logged in"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

        new_msg = Message(text='test message', user_id=self.testuser.id)
        
        db.session.add(new_msg)
        db.session.commit()

        # msg_to_delete = Message.query.get(1)

        resp = c.post(f'/messages/{new_msg.id}/delete')

        test_deleted_msg = Message.query.get(new_msg.id)

        self.assertIsNone(test_deleted_msg)


    def test_logged_out_message_delete_redirect(self):
        """Test if logged out user is redirected when deleting a message"""
        with self.client as c:
        # CURR_USER_KEY cannot be in the session key
            new_msg = Message(text='test message', user_id=self.testuser.id)
        
            db.session.add(new_msg)
            db.session.commit()

            resp = c.post(f"/messages/{new_msg.id}/delete")

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)

    def test_logged_out_message_delete_response(self):
        """Test if logged out user can delete message"""
        with self.client as c:
        # CURR_USER_KEY cannot be in the session key
            new_msg = Message(text='test message', user_id=self.testuser.id)
        
            db.session.add(new_msg)
            db.session.commit()

            resp = c.post(f"/messages/{new_msg.id}/delete", follow_redirects=True)

            html = resp.get_data(as_text=True)

            # Make sure it redirects
            self.assertEqual(resp.status_code, 200)
            self.assertIn('<div class="alert alert-danger">Access unauthorized.</div>', html)

    
    def test_add_message_to_different_user(self):
        """While logged in, test you cannot add a message to a different user"""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY]=self.testuser.id

            test=4

            # test add message to a separate userid
            resp = c.post('/messages/new',data={"text":"new message text", "user_id":f"{self.secondUser.id}"})

            # message gets posted to my profile even though I specified a different user?
            # I would expect an error saying that is not possible
            # There's not an accurate way to test this that I see.  The user id does not appear as a field on the form.  Once
            # the form is submitted, the message is appended to the current user
            # I could add a conditional where request.form['user_id'] and confirm a match with g.user.id
            # I could test the html response if it doesn't go to the expected page

            self.assertEqual(resp.status_code, 302)
            # where does it redirect to
    
    def test_delete_message_from_different_user(self):
        """While logged in, test deleting message of a different user"""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY]=self.testuser.id
            # with self.assertRaises(orm.exc.NoResultFound):
            #     msg = Message.query.one()

            resp = c.post('/messages/1/delete')

            msg = Message.query.all()

            self.assertNotEqual(len(msg),0)
            self.assertEqual(resp.status_code,302)

    def test_delete_message_from_different_user_response(self):
        """While logged in, test deleting message of a different user"""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY]=self.testuser.id
            # with self.assertRaises(orm.exc.NoResultFound):
            #     msg = Message.query.one()

            resp = c.post('/messages/1/delete', follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertIn('<div class="alert alert-danger">Access unauthorized.</div>', html)
            self.assertEqual(resp.status_code, 200)


            # resp = c.post(f"/messages/{new_msg.id}/delete", follow_redirects=True)
            # html = resp.get_data(as_text=True)
            # self.assertIn('html', thml)






