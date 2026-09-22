# -*- coding: utf-8 -*-

from app import app
from flask import render_template, flash, redirect, url_for, request, jsonify
from app.forms import LoginForm, RegistrationForm, MessageForm
from flask_login import (
  current_user, login_user, logout_user, login_required
)
import sqlalchemy as sa
from sqlalchemy import func
from app import db
from app.models import User, Message
from urllib.parse import urlsplit


@app.route('/')
@app.route('/index')
@login_required
def index():
  messages = [
    {
      'author': {'username': 'Вася'},
      'body': 'Парампампам'
    },
    {
      'author': {'username': 'Петя'},
      'body': "Трололо"
    }
  ]
  return render_template(
    'index.html', title='Home', messages=messages
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
    next_page = request.args.get("next")
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


@app.route('/user/<username>', methods=['GET'])
@login_required
def user(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))

    contacts = db.session.scalars(
        sa.select(User).where(User.username != current_user.username)
    ).all()

    form = MessageForm()

    # Проверяем, открыт ли какой-то чат прямо сейчас
    chat_with_id = request.args.get('chat_with', type=int)

    return render_template(
        'user.html',
        user=user,
        contacts=contacts,
        form=form,
        chat_with_id=chat_with_id  # Передаем этот ID в HTML
    )

@app.route('/get-content/<int:item_id>')
def get_content(item_id):

    query = sa.select(Message).where(
        sa.or_(
            sa.and_(
                Message.sender_id == current_user.id,
                Message.receiver_id == item_id
            ),
            sa.and_(
                Message.sender_id == item_id,
                Message.receiver_id == current_user.id
            )
        )
    ).order_by(Message.timestamp.desc())
    messages = db.session.scalars(query).all()

    html_fragment = render_template(
        'messages.html', messages=messages
    )
    return jsonify({"html": html_fragment})


@app.route('/send-message/<int:recipient_id>', methods=['POST'])
@login_required
def send_message(recipient_id):
    form = MessageForm()

    if form.validate_on_submit():
        recipient = db.session.get(User, recipient_id)
        if not recipient:
            return jsonify({"error": "Пользователь не найден"}), 404

        message = Message(
            author=current_user,
            recipient=recipient,
            body=form.content.data
        )
        db.session.add(message)
        db.session.commit()

        return jsonify({"success": True})

    return jsonify({"error": "Ошибка валидации формы", "errors": form.content.errors}), 400

@app.route('/get-unread-counts', methods=['GET'])
@login_required
def get_unread_counts():
    results = db.session.query(
        Message.sender_id, func.count(Message.id)
    ).filter_by(
        receiver_id=current_user.id, is_read=False
    ).group_by(Message.sender_id).all()
    unread_dict = {str(sender_id) : count for sender_id, count in results}
    return jsonify(unread_dict)

@app.route('/mark-messages-read', methods=['POST'])
@login_required
def mark_messages_read():
    data = request.get_json()
    sender_id = data.get('sender_id')
    if not sender_id:
        return jsonify({"error" : "id не предоставлен"}), 400
    unread_messages = Message.query.filter_by(
        receiver_id=current_user.id, is_read=False, sender_id=sender_id
    ).all()
    for msg in unread_messages:
        msg.is_read = True

    db.session.commit()

    return jsonify({'success' : True})
