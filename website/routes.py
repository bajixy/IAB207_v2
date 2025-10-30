# website/routes.py
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user, login_user, logout_user
from website import db
from website.forms import BookingForm, CommentForm, LoginForm, RegisterForm, EventForm
from website.models import User, Event, Booking, Comment
from werkzeug.security import generate_password_hash, check_password_hash

routes = Blueprint('routes', __name__)

# ---- Home ----
@routes.route('/')
def home():
    events = Event.query.order_by(Event.date.asc()).all()
    return render_template('index.html', events=events)

# ---- Create Event (GET/POST) ----
@routes.route('/events/new', methods=['GET', 'POST'])
@login_required
def create_event():
    form = EventForm()
    if form.validate_on_submit():
        e = Event(
            title=form.title.data,
            description=form.description.data,
            date=form.date.data,
            capacity=form.capacity.data,
            owner_id=current_user.id,
        )
        db.session.add(e)
        db.session.commit()
        flash('Event created!', 'success')
        return redirect(url_for('routes.event_detail', event_id=e.id))
    return render_template('create_event.html', form=form)

# ---- Event detail + comments (GET/POST) ----
@routes.route('/events/<int:event_id>', methods=['GET', 'POST'])
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)

    # comment form (inline on the page)
    comment_form = CommentForm()
    if comment_form.validate_on_submit() and current_user.is_authenticated:
        c = Comment(body=comment_form.body.data, user_id=current_user.id, event_id=event.id)
        db.session.add(c)
        db.session.commit()
        flash('Comment posted!', 'success')
        return redirect(url_for('routes.event_detail', event_id=event.id))

    comments = (
        Comment.query.filter_by(event_id=event.id)
        .order_by(Comment.created_at.desc())
        .all()
    )

    # booking form (posted to /book)
    booking_form = BookingForm()

    return render_template(
        'event_detail.html',
        event=event,
        form=comment_form,
        booking_form=booking_form,
        comments=comments,
    )

# ---- Book tickets (POST) ----
@routes.route('/events/<int:event_id>/book', methods=['POST'])
@login_required
def book_event(event_id):
    event = Event.query.get_or_404(event_id)
    form = BookingForm()

    if form.validate_on_submit():
        qty = form.quantity.data

        # server-side guards
        if event.date < datetime.utcnow():
            flash('Event is in the past.', 'warning')
            return redirect(url_for('routes.event_detail', event_id=event.id))

        remaining = max(event.capacity - event.tickets_booked(), 0)
        if qty > remaining:
            flash(f'Only {remaining} ticket(s) remaining.', 'danger')
            return redirect(url_for('routes.event_detail', event_id=event.id))

        db.session.add(Booking(user_id=current_user.id, event_id=event.id, quantity=qty))
        db.session.commit()
        flash('Booking confirmed!', 'success')
        return redirect(url_for('routes.booking_history'))

    flash('Invalid booking request.', 'danger')
    return redirect(url_for('routes.event_detail', event_id=event.id))

# ---- Register ----
@routes.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Email already registered.', 'danger')
            return redirect(url_for('routes.register'))

        hashed_pw = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        new_user = User(email=form.email.data, name=form.name.data, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('routes.login'))
    return render_template('register.html', form=form)

# ---- Login ----
@routes.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('routes.home'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html', form=form)

# ---- My Bookings ----
@routes.route('/me/bookings')
@login_required
def booking_history():
    bookings = (
        db.session.query(Booking, Event)
        .join(Event, Booking.event_id == Event.id)
        .filter(Booking.user_id == current_user.id)
        .order_by(Booking.created_at.desc())
        .all()
    )
    return render_template('booking_history.html', bookings=bookings)

# ---- Logout ----
@routes.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('routes.login'))

# ---- Simple dashboard ----
@routes.route('/dashboard')
@login_required
def dashboard():
    return f"Welcome {current_user.name}! This page is protected."
