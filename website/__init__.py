# website/__init__.py
import os
from pathlib import Path
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
import click
from flask.cli import with_appcontext  # for CLI commands

# Optional: load variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Globals used across the app
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def _normalize_sqlite_uri(app: Flask, uri: str) -> str:
    """
    If someone sets a relative SQLite URI like sqlite:///instance/app.db,
    convert it to an absolute path using the real instance_path so it works
    on Windows/Mac/Linux.
    """
    if not uri.startswith("sqlite:///"):
        return uri

    raw_path = uri.replace("sqlite:///", "", 1)
    raw_norm = raw_path.replace("\\", "/")
    p = Path(raw_path)

    if raw_norm.startswith("instance/"):
        # point inside the actual instance folder
        rel = raw_norm.split("/", 1)[1] if "/" in raw_norm else ""
        abs_path = Path(app.instance_path) / rel
    elif p.is_absolute():
        abs_path = p
    else:
        # make it absolute relative to the app root
        abs_path = Path(app.root_path) / p

    abs_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{abs_path.as_posix()}"


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # ----- Config (env first, then sensible defaults) -----
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-change-me")

    # Ensure instance folder exists up-front
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    # Prefer DATABASE_URL env; else if a packaged DB exists, use it; else use instance/
    packaged_db = Path(app.root_path) / "_data" / "app.db"
    default_sqlite = (
        f"sqlite:///{packaged_db.as_posix()}"
        if packaged_db.exists()
        else "sqlite:///instance/app.db"
    )
    uri = os.getenv("DATABASE_URL", default_sqlite)
    app.config["SQLALCHEMY_DATABASE_URI"] = _normalize_sqlite_uri(app, uri)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # ----- Init extensions -----
    db.init_app(app)
    csrf.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "routes.login"
    login_manager.login_message_category = "info"

    # Import models so SQLAlchemy registers tables
    from .models import User  # noqa: F401

    @login_manager.user_loader
    def load_user(user_id: str):
        return User.query.get(int(user_id))

    # ----- Blueprints -----
    from .routes import routes
    app.register_blueprint(routes)

    # ----- Error handlers -----
    @app.errorhandler(404)
    def not_found(_e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(_e):
        # In debug you’ll still see Werkzeug debugger
        return render_template("500.html"), 500

    # ----- CLI: create tables manually -----
    @app.cli.command("init-db")
    @with_appcontext
    def init_db():
        """Create database tables."""
        db.create_all()
        click.echo(f"Database initialized ✅ -> {app.config['SQLALCHEMY_DATABASE_URI']}")

    # ----- CLI: seed some dummy data (safe to run multiple times) -----
    @app.cli.command("seed-db")
    @with_appcontext
    def seed_db():
        """Insert dummy users/events/bookings/comments if not present."""
        from .models import User, Event, Booking, Comment
        from werkzeug.security import generate_password_hash
        from datetime import datetime, timedelta

        # Ensure tables exist
        db.create_all()

        # Users
        user = User.query.filter_by(email="demo@example.com").first()
        if not user:
            user = User(
                email="demo@example.com",
                name="Demo User",
                password=generate_password_hash("password123", method="pbkdf2:sha256"),
            )
            db.session.add(user)

        # Events
        upcoming = Event.query.filter_by(title="Campus Music Night").first()
        past = Event.query.filter_by(title="Orientation Fair").first()
        if not upcoming:
            upcoming = Event(
                title="Campus Music Night",
                description="Live bands and open mic.",
                date=datetime.utcnow() + timedelta(days=5),
                capacity=100,
                owner_id=user.id if user.id else None,
            )
            db.session.add(upcoming)
        if not past:
            past = Event(
                title="Orientation Fair",
                description="Clubs, stalls and freebies.",
                date=datetime.utcnow() - timedelta(days=3),
                capacity=80,
                owner_id=user.id if user.id else None,
            )
            db.session.add(past)

        db.session.commit()

        # One sample booking on the upcoming event
        if upcoming and not Booking.query.filter_by(user_id=user.id, event_id=upcoming.id).first():
            db.session.add(Booking(user_id=user.id, event_id=upcoming.id, quantity=2))

        # One sample comment
        if upcoming and not Comment.query.filter_by(event_id=upcoming.id).first():
            db.session.add(Comment(user_id=user.id, event_id=upcoming.id, body="Can’t wait!"))

        db.session.commit()
        click.echo("Seed data inserted 🌱")

    return app
