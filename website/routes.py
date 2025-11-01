from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user, login_user, logout_user
from website import db
from website.forms import BookingForm, CommentForm, LoginForm, RegisterForm, EventForm
from website.models import User, Event, Booking, Comment
from werkzeug.security import generate_password_hash, check_password_hash
from pathlib import Path
from werkzeug.utils import secure_filename
import uuid
from flask import current_app

routes = Blueprint('routes', __name__)

# ---- Home (with filters) ----
@routes.route('/', methods=['GET'])
def home():
    q = Event.query

    # Read filters from the URL
    city = (request.args.get('city') or '').strip()
    genre = (request.args.get('genre') or '').strip()
    date_from = (request.args.get('date_from') or '').strip()

    # City -> matches Event.location (case-insensitive contains)
    if city:
        q = q.filter(Event.location.ilike(f"%{city}%"))

    # Genre -> handle both string column and M2M relationship
    if genre:
        try:
            # If you have a Genre model and Event.genres relationship
            from website.models import Genre  # safe to import here
            if hasattr(Event, 'genres'):
                q = q.join(Event.genres).filter(Genre.name == genre)
            else:
                q = q.filter(Event.genre == genre)
        except Exception:
            # Fallback to simple string column
            q = q.filter(Event.genre == genre)

    # Date 
    if date_from:
        try:
            start = datetime.strptime(date_from, "%Y-%m-%d")
            q = q.filter(Event.date >= start)
        except ValueError:
            pass  # ignore bad date



    q = q.order_by(Event.date.asc())

    events = q.all()


    genres = []
    try:
        from website.models import Genre
        genres = Genre.query.order_by(Genre.name.asc()).all()
    except Exception:
        rows = db.session.query(Event.genre).distinct().all()
        genres = [type("G", (), {"name": r[0]}) for r in rows if r[0]]

    return render_template('index.html', events=events, genres=genres)


#Create Event (GET/POST)
@routes.route('/events/new', methods=['GET', 'POST'])
@login_required
def create_event():
    form = EventForm()
    if form.validate_on_submit():
        #image upload v2
        image_rel_path = None
        if form.image.data:
            file = form.image.data
            ext = Path(secure_filename(file.filename)).suffix.lower()
            fname = f"{uuid.uuid4().hex}{ext}"
            save_to = Path(current_app.config["UPLOAD_FOLDER"]) / fname
            file.save(save_to)
            image_rel_path = f"uploads/{fname}"  # relative to /static

        #Create the event
        e = Event(
            title=form.title.data,
            description=form.description.data,
            date=form.date.data,
            capacity=form.capacity.data,
            genre=form.genre.data if hasattr(form, "genre") else None,
            host=form.host.data if hasattr(form, "host") else None,
            location=form.location.data if hasattr(form, "location") else None,
            image_path=image_rel_path,
            owner_id=current_user.id,
        )

        db.session.add(e)
        db.session.commit()
        flash('Event created successfully!', 'success')
        return redirect(url_for('routes.event_detail', event_id=e.id))

    return render_template('create_event.html', form=form)


@routes.route('/events/<int:event_id>', methods=['GET', 'POST'])
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)

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


#Delete Event
@routes.route('/events/<int:event_id>/delete', methods=['POST'])
@login_required
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)

    if event.owner_id != current_user.id:
        flash("You don't have permission to delete this event.", "danger")
        return redirect(url_for('routes.event_detail', event_id=event.id))

    db.session.delete(event)
    db.session.commit()
    flash("Event deleted successfully!", "success")
    return redirect(url_for('routes.home'))



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


#Register 
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


#my tickets
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


#log out
@routes.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('routes.login'))


@routes.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == "POST":
    
        name = (request.form.get("name") or "").strip()
        bio  = (request.form.get("bio") or "").strip()
        role = (request.form.get("role") or "").strip().lower()

        if name:
            current_user.name = name

        current_user.bio = bio  # empty string is fine

        if role in ("user", "artist", "host"):
            current_user.role = role
        else:
            flash("Invalid role selected.", "danger")
            return redirect(url_for("routes.dashboard"))

        
        file = request.files.get("profile_pic")
        if file and file.filename:
            from pathlib import Path
            from werkzeug.utils import secure_filename
            import uuid
            from flask import current_app

            ext = Path(secure_filename(file.filename)).suffix.lower()
            if ext not in {".png", ".jpg", ".jpeg", ".webp"}:
                flash("Please upload a PNG/JPG/WebP image.", "warning")
                return redirect(url_for("routes.dashboard"))

            uploads_rel = "uploads/profilepics"
            dest_dir = Path(current_app.static_folder) / uploads_rel
            dest_dir.mkdir(parents=True, exist_ok=True)

            fname = f"{uuid.uuid4().hex}{ext}"
            file.save(dest_dir / fname)

        
            current_user.profile_pic = f"{uploads_rel}/{fname}"

        db.session.commit()
        flash("Profile updated!", "success")
        return redirect(url_for("routes.dashboard"))

    return render_template("dashboard.html", user=current_user)

