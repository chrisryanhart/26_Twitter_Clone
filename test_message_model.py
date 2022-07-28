"""Test Message Model"""
#
#    python -m unittest test_user_model.py


from datetime import datetime
import os
from re import U
from unittest import TestCase

from sqlalchemy import exc

from psycopg2 import IntegrityError, Timestamp

from models import db, User, Message, Follows, Likes

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


class MessageModelTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()
        Follows.query.delete()

        self.client = app.test_client()

        User.signup(
            email="party@gmail.com",
            username="3rduser",
            password="3rd_password",
            image_url=None
        )

        db.session.commit()

        User.signup(
            email="2ndEmail@gmail.com",
            username="2nd_user",
            password="2nd_password",
            image_url=None
        )

        # db.session.add(u1)
        # db.session.add(u2)
        db.session.commit()

        # message 1
        m1 = Message(text='here is my message',user_id=1)

        db.session.add(m1)
        db.session.commit()

        # message 2
        m2 = Message(text='2nd message', user_id=1)

        # message 3
        m3 = Message(text='3rd message',user_id=2)

        # db.session.add(m1)
        db.session.add(m2)
        db.session.add(m3)

        db.session.commit()

    def test_message_likes(self):
        messages = Message.query.all()

        m1 = messages[0]

        u1 = User.query.first()

        like = Likes(user_id=u1.id, message_id=m1.id)

        db.session.add(like)
        db.session.commit()

        likes = Likes.query.filter_by(user_id=u1.id).all()

        self.assertEqual(len(likes), 1)



    def test_valid_message(self):
        m4 = Message(text='test message',user_id=2)

        db.session.add(m4)
        db.session.commit()
        
        # gets id assign once commited to the DB
        self.assertTrue(type(m4.id)==int)

    def test_invalid_text(self):

        more_than_140_char = 'lj;alsjdkfl;j;lasdjkf;lkjsadf;ljasdfl;jkasd;lfjas;ldjf;lasdjkf;ljsadkf;ljdsakf;ljdsaf;lsadjkfl;sadjkf;ldjskf;lasdjkf;ladjskf;lsadjf;lasdjkf;lasdjkf;ldjsakfl;asdjkas;ldfjka;sldjfk;asldjfas;ldjfa;sldjfka;lsjf'

        m4 = Message(text=more_than_140_char,user_id=2)

        db.session.add(m4)

        with self.assertRaises(exc.DataError):
            db.session.commit()

        # self.assertTrue(type(m4.id)==int)

    def test_no_text(self):
        u1 = User.query.get(1)

        m4 = Message(text=None,user_id=1)

        db.session.add(m4)

        with self.assertRaises(exc.IntegrityError):
            db.session.commit()

    def test_message_relationship(self):

        m1 = Message.query.get(1)

        self.assertEqual(m1.user.id,1)

    def test_user_relationship(self):

        u1 = User.query.get(1)

        self.assertEqual(repr(u1.messages[0]),'<Message 1>')

    
    def test_invalid_timestamp(self):

        u1 = User.query.get(1)

        invalid_m = Message(text='3rd message', timestamp='',user_id=2)

        db.session.add(invalid_m)

        with self.assertRaises(exc.DataError):
            db.session.commit()

    def test_no_user_id(self):

        invalid_user_id = Message(text='3rd message',user_id=None)
        db.session.add(invalid_user_id)

        with self.assertRaises(exc.IntegrityError):
            db.session.commit()

        


    




    # text not nullable

    # message has relationship with user

    # timestamp not null

    # user_id is FK in another table

