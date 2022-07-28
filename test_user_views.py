"""User View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py

from cgitb import html
import os
from unittest import TestCase
from sqlalchemy import exc, orm

from models import Follows, db, connect_db, Message, User, Likes

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


class UserViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        # User.query.delete()
        # Message.query.delete()

        db.drop_all()
        db.create_all()

        self.client = app.test_client()

        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)
        self.testuser_id = 1
        self.testuser.id = self.testuser_id



        self.secondUser = User.signup(username= "rocky",
                                    email="email@gmail.com",
                                    password="bogus",
                                    image_url=None)

        self.secondUser_id = 2
        self.secondUser.id = self.secondUser_id

        db.session.commit()

        m1 = Message(id=10,text='test message', user_id=self.secondUser_id)
        m2 = Message(id=11,text='2nd test message', user_id=self.secondUser_id)
        m3 = Message(id=12,text='3rd test message', user_id=self.testuser_id)

        db.session.add(m1)
        db.session.add(m2)
        db.session.add(m3)
        db.session.commit()

        follow = Follows(user_being_followed_id=self.testuser.id, user_following_id=self.secondUser.id)
        db.session.add(follow)
        db.session.commit()

        # setup likes

        like1 = Likes(user_id=self.testuser_id,message_id=11)

        db.session.add(like1)
        db.session.commit()

    def test_show_all_users(self):
        """Ensure all users are shown"""
        with self.client as c:
        
            resp = c.get('/users')
            html = resp.get_data(as_text=True)

            self.assertIn('@testuser',html)
            self.assertIn('@rocky',html)
            self.assertEqual(resp.status_code, 200)

    def test_query_users(self):
        """Search for users"""
        with self.client as c:
            resp = c.get('/users?q=rock')
            html = resp.get_data(as_text=True)

            self.assertIn('@rocky', html)

    def test_show_user_profile(self):
        with self.client as c:
            resp = c.get(f'/users/{self.testuser_id}')
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('@testuser',html)

    
    def test_show_user_profile(self):
        """Show user likes and follows"""
        with self.client as c:
            
            resp = c.get('/users/1')
            html = resp.get_data(as_text=True)

            self.assertIn('<h4><a href="/users/1/likes">1</a></h4>',html)
            self.assertIn('<a href="/users/1/followers">1</a>',html)

    def test_add_user_like(self):
        with self.client as c: 
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.secondUser_id

            msg = Message.query.get(12)

            like = Likes(user_id=self.secondUser_id,message_id=msg.id)

            db.session.add(like)
            db.session.commit()

            u2 = User.query.get(2)

            self.assertTrue(len(u2.likes)==1)

    def test_remove_user_like(self):
        with self.client as c: 
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id
            
            u1 = User.query.get(1)
            msg_id = u1.likes[0].id

            self.assertTrue(len(u1.likes)==1)

            # how can you prevent the wrong user from liking their own post 

            resp = c.post(f'/users/handle_like/{msg_id}')

            updated_u1 = User.query.get(1)
            updated_likes = updated_u1.likes

            self.assertTrue(len(updated_likes)==0)
            
    def test_like_without_login(self):
        """Test if you can like without a login"""
        with self.client as c: 
            
            u1 = User.query.get(1)

            self.assertTrue(len(u1.likes)==1)
           

            # how can you prevent the wrong user from liking their own post 

            resp = c.post('/users/handle_like/12')

            updated_u1 = User.query.get(1)
            updated_likes = updated_u1.likes

            self.assertTrue(len(updated_likes)==1)


        
    def test_show_different_user_following_while_loggedOn(self):
        """Can you view who another user follows while logged in?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

            # Now, that session setting is saved, so we can have
            # the rest of ours test

            resp = c.get(f'/users/{self.secondUser_id}/following')
            html = resp.get_data(as_text=True)

            # No redirect b/c user is logged in
            self.assertEqual(resp.status_code, 200)
            self.assertIn('<p>@testuser</p>',html)

    def test_show_different_user_followers_while_loggedOn(self):
        """Show another users followers whilel logged in"""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.secondUser_id

            # Now, that session setting is saved, so we can have
            # the rest of ours test

            resp = c.get(f'/users/{self.testuser_id}/followers')
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('<p>@rocky</p>',html)

    def test_show_another_users_follows_while_loggedOut(self):
        """Unauthorized access when attempting to view another users follows while logged out"""
        with self.client as c:
            
            resp = c.get(f'/users/{self.secondUser_id}/following', follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('<div class="alert alert-danger">Access unauthorized.</div>', html)

    def test_show_another_users_followers_while_loggedOut(self):
        """Unauthorized access when attempting to view another users followers while logged out"""
        with self.client as c:
            
            resp = c.get(f'/users/{self.testuser_id}/followers', follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('<div class="alert alert-danger">Access unauthorized.</div>', html)
    