from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DecimalField, DateField, HiddenField, SubmitField
from wtforms.validators import InputRequired, Length, NumberRange

# Event Details
class EventDetailsForm(FlaskForm):
    event_name = StringField("Event Name", validators=[InputRequired(), Length(max=255)])
    overall_budget = DecimalField("Total Budget", validators=[InputRequired(), NumberRange(min=0)], places=2)
    event_date = DateField("Date", validators=[InputRequired()], format="%Y-%m-%d")
    capacity = IntegerField("Capacity", validators=[InputRequired(), NumberRange(min=1, max=5000)])
    location_id = HiddenField(validators=[InputRequired()])
    submit = SubmitField("Next")
