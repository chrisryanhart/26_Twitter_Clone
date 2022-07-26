"""Test Message Model"""
#
#    python -m unittest test_user_model.py


import os
from re import U
from unittest import TestCase

from sqlalchemy import exc

from psycopg2 import IntegrityError

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

    def test_