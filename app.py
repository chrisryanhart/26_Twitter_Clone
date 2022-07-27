from crypt import methods
import os
from turtle import update

from flask import Flask, render_template, request, flash, redirect, session, g, request
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import UpdateUserForm, UserAddForm, LoginForm, MessageForm
from models import db, connect_db, User, Message, Likes
from flask_bcrypt import Bcrypt

CURR_USER_KEY = "curr_user"

# https://upload.wikimedia.org/wikipedia/commons/thumb/7/7d/NaPali_overlook_Kalalau_Valley.jpg/1024px-NaPali_overlook_Kalalau_Valley.jpg

app = Flask(__name__)
bcrypt = Bcrypt(app)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL', 'postgresql:///warbler'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")
toolbar = DebugToolbarExtension(app)

connect_db(app)


##############################################################################
# User signup/login/logout


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]
        return True
    return False


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """

    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data,
                                 form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.route('/logout')
def logout():
    """Handle logout of user."""

    logout_result = do_logout()

    if logout_result:
        flash('User logout successful')

    return redirect('/login')

    


##############################################################################
# General user routes:

@app.route('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template('users/index.html', users=users)


@app.route('/users/<int:user_id>')
def users_show(user_id):
    """Show user profile."""

    # if not g.user:
    #     flash("Access unauthorized.", "danger")
    #     return redirect("/")

    user = User.query.get_or_404(user_id)

    # snagging messages in order from the database;
    # user.messages won't be in order by default
    messages = (Message
                .query
                .filter(Message.user_id == user_id)
                .order_by(Message.timestamp.desc())
                .limit(100)
                .all())
    likes = Likes.query.filter_by(user_id=user.id)
    liked_messages = [like.messages for like in likes]

    like_count = len([like.id for like in likes])

    return render_template('users/show.html', user=user, messages=messages, like_count=like_count)

@app.route('/users/<int:user_id>/likes')
def show_user_likes(user_id):

    user = User.query.get_or_404(user_id)

    likes = Likes.query.filter_by(user_id=user.id)
    # can do a message query but filter based on user likes 
    # then messages will be connected to the user

    liked_messages = [like.messages for like in likes]
    like_count = len(liked_messages)

    # map the user info with the message

    return render_template('users/likes.html', user=user, like_count=like_count, liked_messages=liked_messages)

@app.route('/users/<int:user_id>/following')
def show_following(user_id):
    """Show list of people this user is following."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)

    likes = Likes.query.filter_by(user_id=user.id)
    liked_messages = [like.messages for like in likes]
    like_count = len(liked_messages)

    return render_template('users/following.html', user=user, like_count=like_count)


@app.route('/users/<int:user_id>/followers')
def users_followers(user_id):
    """Show list of followers of this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)

    likes = Likes.query.filter_by(user_id=user.id)
    liked_messages = [like.messages for like in likes]
    like_count = len(liked_messages)
    return render_template('users/followers.html', user=user, like_count=like_count)


@app.route('/users/follow/<int:follow_id>', methods=['POST'])
def add_follow(follow_id):
    """Add a follow for the currently-logged-in user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get_or_404(follow_id)
    g.user.following.append(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/stop-following/<int:follow_id>', methods=['POST'])
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get(follow_id)
    g.user.following.remove(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/profile', methods=["GET", "POST"])
def profile():
    """Update profile for current user."""



    add_user_to_g()
    user = g.user

    # user = User.query.filter_by(username=)
    # can't retrieve the user until the form is submitted as is

    form = UpdateUserForm()

    if form.validate_on_submit():

        # Have to form fields already be complete with the 

        username = form.username.data
        user = User.query.filter_by(username=username)

        hashed_password = user[0].password
        submitted_password = form.password.data

        password_check = bcrypt.check_password_hash(hashed_password,submitted_password)

        if not password_check:
            flash('Username/password combination incorrect')
            return redirect('/')

        user[0].email = form.email.data
        user[0].image_url = form.image_url.data
        user[0].header_image_url = form.header_image_url.data
        user[0].bio = form.bio.data

        # updated_profile = User(username=username,email=email, image_url=image_url, header_image_url=header_image_url,bio=bio,password=hashed_password)

        db.session.add(user[0])
        db.session.commit()

        return redirect(f'/users/{user[0].id}')
    # confirm PW matches original hashed PW

    # auto populate the fields if data exists

    form.username.data = user.username
    form.email.data = user.email
    form.image_url.data = user.image_url
    form.header_image_url.data = user.header_image_url
    form.bio.data = user.bio

    return render_template('/users/edit.html', form=form, user=g.user)


@app.route('/users/delete', methods=["POST"])
def delete_user():
    """Delete user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    do_logout()

    db.session.delete(g.user)
    db.session.commit()

    return redirect("/signup")


##############################################################################
# Messages routes:

@app.route('/messages/new', methods=["GET", "POST"])
def messages_add():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()

        return redirect(f"/users/{g.user.id}")

    return render_template('messages/new.html', form=form)


@app.route('/messages/<int:message_id>', methods=["GET"])
def messages_show(message_id):
    """Show a message."""

    msg = Message.query.get(message_id)
    return render_template('messages/show.html', message=msg)


@app.route('/messages/<int:message_id>/delete', methods=["GET","POST"])
def messages_destroy(message_id):
    """Delete a message."""
    msg = Message.query.get(message_id)

    if not g.user or msg.user_id != g.user.id:
        flash("Access unauthorized.", "danger")
        return redirect("/")


    db.session.delete(msg)
    db.session.commit()

    return redirect(f"/users/{g.user.id}")


##############################################################################
# Homepage and error pages


@app.route('/')
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of followed_users
    """

    if g.user:
        # get list of users being following
        user = g.user
        followed_users = [followed_user.id for followed_user in user.following]
        followed_users.append(user.id)

        messages = (Message
                    .query
                    .filter(Message.user_id.in_(followed_users))
                    .order_by(Message.timestamp.desc())
                    .limit(100)
                    .all())

        # loop through messages
        # loop through user ids 
        # add to new list if there's a match
        # stop at 100 values 

        # find out if message is liked

        likes = Likes.query.all()
        like_message_ids = [like.message_id for like in likes]
        # can unpack like ids here

        # test = []

        # for msg in messages:
        #     if msg.id in like_message_ids:
        #         test.append(msg.id)
        #     # [msg.id for like in likes if like.message_id == msg.id]
            
        return render_template('home.html', messages=messages, likes=likes, like_message_ids=like_message_ids, user=user)

    else:
        return render_template('home-anon.html')

@app.route('/users/handle_like/<int:msg_id>', methods=["POST"])
def handle_like(msg_id):

    curr_user_id = g.user.id

    likes = Likes.query.filter_by(user_id=curr_user_id)

    like_status = [like.id for like in likes if msg_id == like.message_id]

    if (len(like_status)!=0):
        # Delete message from likes

        like_to_delete = Likes.query.get(like_status[0])
        
        db.session.delete(like_to_delete)
        db.session.commit()
    else:
        # Add message to likes 
        new_like = Likes(user_id = curr_user_id, message_id = msg_id)

        db.session.add(new_like)
        db.session.commit()

    return redirect('/')

##############################################################################
# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask

@app.after_request
def add_header(req):
    """Add non-caching headers on every request."""

    req.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    req.headers["Pragma"] = "no-cache"
    req.headers["Expires"] = "0"
    req.headers['Cache-Control'] = 'public, max-age=0'
    return req
