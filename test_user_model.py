"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from re import U
from unittest import TestCase

from models import db, User, Message, Follows

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.drop_all()
db.create_all()


class UserModelTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()
        Follows.query.delete()

        self.client = app.test_client()

        u1 = User(
            email="party@gmail.com",
            username="3rduser",
            password="3rd_password"
        )

        u2 = User(
            email="2ndEmail@gmail.com",
            username="2nd_user",
            password="2nd_password"
        )

        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()

    # def tearDown(self):

        # return super().tearDown()

    def test_user_model(self):
        """Does basic model work?"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )

        db.session.add(u)
        db.session.commit()

        # User should have no messages & no followers
        self.assertEqual(len(u.messages), 0)
        self.assertEqual(len(u.followers), 0)

        # user should have the below repr representation
        self.assertEqual(repr(u), f'<User #{u.id}: testuser, test@test.com>')

        # confirm is_following detects when user1 is following user 2

    def test_user_following(self):
        u3 = User(
            email="vacation@gmail.com",
            username="3rd_user",
            password="Third_PW"
        )

        db.session.add(u3)
        db.session.commit()

        # make user1 follow user 2

        follow = Follows(user_being_followed_id=u3.id, user_following_id=1)

        db.session.add(follow)
        db.session.commit()

        # confirm u1 is following u2

        u1 = User.query.get(1)

        self.assertTrue(u1.is_following(u3))


    def test_user_unfollowing(self):

        u1 = User.query.get(1)
        u2 = User.query.get(2)

        self.assertFalse(u1.is_following(u2))

    def test_followed_by(self):
        u1 = User.query.get(1)
        u2 = User.query.get(2)

        follow = Follows(user_being_followed_id=u2.id, user_following_id=u1.id)

        db.session.add(follow)
        db.session.commit()

        self.assertTrue(u2.is_followed_by(u1))

    def test_not_followed_by(self):
        u1 = User.query.get(1)
        u2 = User.query.get(2)

        self.assertFalse(u2.is_followed_by(u1))

    def test_user_signup(self):
        # Add new user 
        try:
            u = User.signup(
                username='3rduser',
                password='PW',
                email='test@gmail.com',
                image_url='https://upload.wikimedia.org/wikipedia/commons/thumb/1/1c/Grizzly_Giant_Mariposa_Grove.jpg/440px-Grizzly_Giant_Mariposa_Grove.jpg'
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", 'danger')
            return False
        # try:
        #     user = User.signup(
        #         username=form.username.data,
        #         password=form.password.data,
        #         email=form.email.data,
        #         image_url=form.image_url.data or User.image_url.default.arg,
        #     )
            # db.session.commit()

        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        db.session.commit()

        # PW still commits to DB even though it doesn't comply with form validators

        self.assertEqual(u.id, 3)
    
    # def test_invalid_user_signup(self):
        # test cases:
        # completely empty fields
        # username already taken


# def signup(cls, username, email, password, image_url):


