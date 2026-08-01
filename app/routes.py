import flask
import datetime
from app import app
from flask import flash, redirect, url_for, request, render_template, jsonify
from app.forms import LoginForm, RegistrationForm
from flask_login import (
  current_user, login_user, logout_user, login_required
)
import sqlalchemy as sa
from app import db
from app.models import User, Message
from urllib.parse import urlsplit

@login_required
@app.route('/')
@app.route('/index')
def index():
  messages = [
    {
      "author" : {"username" : "COL" },
      "body" : "8 800 535 3535",
    },
    {
      "author": {"username": "SOP"},
      "body": "48520",
    },
    {
      "author": {"username": "rut"},
      "body": "316497852013",
    }
  ]
  products = ["milk", "bread", "apple"]
  user = {'username' : 'Dmitriy'}
  time_now = str(datetime.datetime.now())
  time_now_redacted = int(time_now[11:13])
  color_time = "red"
  time_day = "Добрый вечер"
  if time_now_redacted < 6:
    time_day = ("Доброй ночи")
    color_time = "black"
  elif time_now_redacted >= 6 and time_now_redacted < 12:
    time_day = "Доброе утро"
    color_time = "blue"
  elif time_now_redacted >= 12 and time_now_redacted < 18:
    time_day = "Добрый день"
    color_time = "green"

  return render_template(
    'index.html', title='Home', messages=messages, products=products, user=user,
    time_day=time_day, color_time=color_time
  )

@app.route('/login', methods=['GET', 'POST'])
def login():
  if current_user.is_authenticated:
    return redirect(url_for('index'))
  form = LoginForm()
  if form.validate_on_submit():
    user = db.session.scalar(
      sa.select(User).where(User.username == form.username.data)
    )
    if user is None or not user.check_password(form.password.data):
      flash('Invalid username or password')
      return redirect(url_for('login'))
    login_user(user, remember=form.remember_me.data)
    next_page = request.args.get('next')
    if not next_page or urlsplit(next_page).netloc != '':
      next_page = url_for('index')

    return redirect(next_page)
  return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
  logout_user()
  return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
  if current_user.is_authenticated:
    return redirect(url_for('index'))
  form = RegistrationForm()
  if form.validate_on_submit():
    user = User(username=form.username.data, email=form.email.data)
    user.set_password(form.password.data)
    db.session.add(user)
    db.session.commit()
    flash('Congratulations, you are now a registered user!')
    return redirect(url_for('login'))
  return render_template('register.html', title='Register', form=form)

@app.route('/user/<username>')
@login_required
def user(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    messages = db.session.scalars(sa.select(Message))
    contacts = db.session.scalars(sa.select(User).where(User.username != username))
    return render_template('user.html', user=user, messages=messages, contacts=contacts)

@app.route('/get-content/<int:item_id>')
def get_content(item_id):
    query = sa.select(Message).where(
      sa.or_(
        sa.and_(
          Message.sender_id == item_id,
          Message.receiver_id == current_user.id
        ),
        sa.and_(
          Message.sender_id == current_user.id,
          Message.receiver_id == item_id
        )
      )
    ).order_by(Message.timestamp.desc())
    messages = db.session.scalars(query).all()
    html_fragment = render_template('messages.html', messages=messages)
    return jsonify({"html" : html_fragment})