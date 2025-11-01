import os
from pathlib import Path
from flask import Flask, render_template, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from werkzeug.routing import BuildError
import click
from flask.cli import with_appcontext
from sqlalchemy import inspect, text

# Optional: load variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def _normalize_sqlite_uri(app: Flask, uri: str) -> str:
    if not uri.startswith("sqlite:///"):
        return uri
    raw_path = uri.replace("sqlite:///", "", 1)
    raw_norm = raw_path.replace("\\", "/")
    p = Path(raw_path)
    if raw_norm.startswith("instance/"):
        rel = raw_norm.split("/", 1)[1] if "/" in raw_norm else ""
        abs_path = Path(app.instance_path) / rel
    elif p.is_absolute():
        abs_path = p
    else:
        abs_path = Path(app.root_path) / p
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{abs_path.as_posix()}"


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # ----- Config -----
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-change-me")
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db_path = Path(app.instance_path) / "app.db"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path.as_posix()}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    uploads_dir = Path(app.root_path) / "static" / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = uploads_dir.as_posix()
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB max upload size

    # ----- Init extensions -----
    db.init_app(app)
    csrf.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "routes.login"
    login_manager.login_message_category = "info"

    # ----- Models -----
    from .models import User  # noqa: F401

    @login_manager.user_loader
    def load_user(user_id: str):
        return User.query.get(int(user_id))

    # --- Ensure new User columns exist (dev convenience) ---
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            if "user" in inspector.get_table_names():
                cols = {c["name"] for c in inspector.get_columns("user")}
                stmts = []
                if "role" not in cols:
                    stmts.append(text("ALTER TABLE user ADD COLUMN role VARCHAR(20) DEFAULT 'user'"))
                if "bio" not in cols:
                    stmts.append(text("ALTER TABLE user ADD COLUMN bio TEXT DEFAULT ''"))
                if "profile_pic" not in cols:
                    stmts.append(text("ALTER TABLE user ADD COLUMN profile_pic VARCHAR(255)"))
                for s in stmts:
                    db.session.execute(s)
                if stmts:
                    db.session.commit()
                    print(f"✅ Added missing columns: {[s.text for s in stmts]}")
        except Exception as e:
            print("⚠️ Skipped column check:", e)

    # ----- Blueprints -----
    from .routes import routes
    app.register_blueprint(routes)

    # ----- Error handlers -----
    @app.errorhandler(404)
    def not_found(_e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(_e):
        return render_template("500.html"), 500

    # ----- Context processors / template helpers -----
    @app.context_processor
    def inject_helpers():
        def safe_url_for(endpoint, **values):
            try:
                return url_for(endpoint, **values)
            except BuildError:
                return None

        import datetime as _dt
        return {
            "safe_url_for": safe_url_for,
            "current_year": _dt.datetime.utcnow().year,
        }

    # ----- CLI: create tables -----
    @app.cli.command("init-db")
    @with_appcontext
    def init_db():
        from . import models
        db.create_all()
        click.echo(f"Database initialized ✅ -> {app.config['SQLALCHEMY_DATABASE_URI']}")

    # ----- CLI: seed data -----
    @app.cli.command("seed-db")
    @with_appcontext
    def seed_db():
        from .models import User, Event, Booking, Comment
        from werkzeug.security import generate_password_hash
        from datetime import datetime, timedelta

        db.create_all()

        user = User.query.filter_by(email="demo@example.com").first()
        if not user:
            user = User(
                email="demo@example.com",
                name="Demo User",
                password=generate_password_hash("password123", method="pbkdf2:sha256"),
            )
            db.session.add(user)

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

        if upcoming and not Booking.query.filter_by(user_id=user.id, event_id=upcoming.id).first():
            db.session.add(Booking(user_id=user.id, event_id=upcoming.id, quantity=2))

        if upcoming and not Comment.query.filter_by(event_id=upcoming.id).first():
            db.session.add(Comment(user_id=user.id, event_id=upcoming.id, body="Can’t wait!"))

        db.session.commit()
        click.echo("Seed data inserted 🌱")

    # ✅ Return app
    return app
