# website/forms.py
from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    SubmitField,
    IntegerField,
    TextAreaField,
    DateTimeLocalField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    NumberRange,
)

# --- Auth forms ---
class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    name = StringField("Name", validators=[DataRequired(), Length(min=2, max=80)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Register")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


# --- Event-related forms ---
class BookingForm(FlaskForm):
    quantity = IntegerField(
        "Quantity",
        validators=[DataRequired(), NumberRange(min=1, max=100)]
    )
    submit = SubmitField("Book tickets")


class CommentForm(FlaskForm):
    body = TextAreaField(
        "Comment",
        validators=[DataRequired(), Length(max=500)]
    )
    submit = SubmitField("Post comment")


class EventForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Description", validators=[DataRequired()])
    # HTML datetime-local uses "YYYY-MM-DDTHH:MM"
    date = DateTimeLocalField(
        "Date & time",
        format="%Y-%m-%dT%H:%M",
        validators=[DataRequired()],
    )
    capacity = IntegerField(
        "Capacity",
        validators=[DataRequired(), NumberRange(min=1, max=100000)]
    )
    submit = SubmitField("Create event")
