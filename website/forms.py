# website/forms.py
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed

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

#Auth forms
class RegisterForm(FlaskForm):
    first_name = StringField("First Name", validators=[DataRequired(), Length(max=100)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(max=100)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    street_address = StringField("Street Address", validators=[DataRequired(), Length(max=255)])
    phone_number = StringField("Phone Number", validators=[DataRequired(), Length(max=20)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Sign Up")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


class BookingForm(FlaskForm):
    name = StringField(
        "Your Name",
        validators=[DataRequired(), Length(min=2, max=100)],
        filters=[lambda x: x.strip() if x else x]  # trims spaces
    )
    email = StringField(
        "Email",
        validators=[DataRequired(), Email(), Length(max=255)],
        filters=[lambda x: x.strip().lower() if x else x]  # normalize email
    )
    quantity = IntegerField(
        "Quantity",
        validators=[DataRequired(), NumberRange(min=1)],
    )
    submit = SubmitField("Book Now")


class CommentForm(FlaskForm):
    body = TextAreaField(
        "Comment",
        validators=[DataRequired(), Length(max=500)],
        filters=[lambda x: x.strip() if x else x]  # trims whitespace
    )
    submit = SubmitField("Post comment")

class EventForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Description", validators=[DataRequired()])
    date = DateTimeLocalField(
        "Date & time",
        format="%Y-%m-%dT%H:%M",
        validators=[DataRequired()],
    )
    capacity = IntegerField(
        "Capacity",
        validators=[DataRequired(), NumberRange(min=1, max=100000)]
    )

    # updated fields now adds genre host location
    genre = StringField("Genre", validators=[DataRequired(), Length(max=50)])
    host = StringField("Host", validators=[DataRequired(), Length(max=120)])
    location = StringField("Location", validators=[DataRequired(), Length(max=255)])

    image = FileField(
        "Event image",
        validators=[FileAllowed(["jpg", "jpeg", "png", "gif"], "Images only!")],
    )

    submit = SubmitField("Create event")

