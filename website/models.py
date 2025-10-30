# website/models.py
from datetime import datetime
from flask_login import UserMixin
from website import db
from sqlalchemy import CheckConstraint, Index, func  # ✅ needed for constraints & func.now()

# ---------- User ----------
class User(db.Model, UserMixin):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    # store hashed password (pbkdf2:sha256)
    password = db.Column(db.String(255), nullable=False)

    # optional relationships (safe to keep)
    events = db.relationship('Event', backref='owner', lazy=True)
    bookings = db.relationship('Booking', backref='user', lazy=True)
    comments = db.relationship('Comment', backref='user', lazy=True)

    def __repr__(self):
        return f"<User {self.email}>"

# ---------- Event ----------
class Event(db.Model):
    __tablename__ = "event"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    capacity = db.Column(db.Integer, nullable=False, default=50)
    tickets_sold = db.Column(db.Integer, nullable=False, default=0)

    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    bookings = db.relationship(
        "Booking", backref="event", lazy=True, cascade="all, delete-orphan"
    )
    comments = db.relationship(
        "Comment", backref="event", lazy=True, cascade="all, delete-orphan"
    )

    def tickets_booked(self):
        # total quantity booked for this event
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

# ---------- Booking ----------
class Booking(db.Model):
    __tablename__ = "booking"
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    price_cents = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=func.now()  # ✅ works with the import above
        # alternatively: server_default=db.func.now()
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

# ---------- Comment ----------
class Comment(db.Model):
    __tablename__ = "comment"
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=func.now()  # ✅
        # alternatively: server_default=db.func.now()
    )

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=False, index=True)

    __table_args__ = (
        Index("ix_comment_event_created_at", "event_id", "created_at"),
    )

    def __repr__(self):
        return f"<Comment {self.id} event={self.event_id} user={self.user_id}>"
