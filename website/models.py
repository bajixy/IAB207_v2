from datetime import datetime
from flask_login import UserMixin
from website import db
from sqlalchemy import CheckConstraint, Index, func  

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    street_address = db.Column(db.String(255))
    phone_number = db.Column(db.String(20))
    role = db.Column(db.String(20), default="user")  # "user", "artist", "host"
    bio = db.Column(db.Text, default="")             # short description or artist bio
    profile_pic = db.Column(db.String(255), nullable=True)

    # Relationships
    bookings = db.relationship('Booking', backref='user', lazy=True)
    comments = db.relationship('Comment', backref='user', lazy=True)
    events = db.relationship('Event', backref='owner', lazy=True)

    # Computed property for backward compatibility
    @property
    def name(self):
        """Return the user's full name or email if missing."""
        full_name = f"{self.first_name or ''} {self.last_name or ''}".strip()
        return full_name if full_name else self.email

    def __repr__(self):
        return f"<User {self.name} ({self.role})>"

class Event(db.Model):
    __tablename__ = "event"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    capacity = db.Column(db.Integer, nullable=False, default=0)
    tickets_sold = db.Column(db.Integer, nullable=False, default=0)
    genre = db.Column(db.String(50), nullable=False, default="other")
    host = db.Column(db.String(120), nullable=False, default="Unknown")
    location = db.Column(db.String(255), nullable=False, default="TBA")
    image_path = db.Column(db.String(255), nullable=True)

    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"))


    bookings = db.relationship(
        "Booking", backref="event", lazy=True, cascade="all, delete-orphan"
    )
    comments = db.relationship(
        "Comment", backref="event", lazy=True, cascade="all, delete-orphan"
    )

    def tickets_booked(self):
        
        return (
            db.session.scalar(
                db.select(db.func.coalesce(db.func.sum(Booking.quantity), 0))
                .where(Booking.event_id == self.id)
            )
            or 0
        )

    @property
    def status(self):
        if self.tickets_sold >= self.capacity:
            return "Sold Out"
        if self.date < datetime.utcnow():
            return "Inactive"
        if self.tickets_booked() >= self.capacity:
            return "Sold Out"
        return "Open"

    def __repr__(self):
        return f"<Event {self.title}>"


class Booking(db.Model):
    __tablename__ = "booking"
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    price_cents = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=func.now() 
    
    )

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=False, index=True)

    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_booking_qty_pos"),
        CheckConstraint("price_cents >= 0", name="ck_booking_price_nonneg"),
        Index("ix_booking_user_created_at", "user_id", "created_at"),
    )

    def __repr__(self):
        return f"<Booking {self.id} user={self.user_id} event={self.event_id}>"

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
   