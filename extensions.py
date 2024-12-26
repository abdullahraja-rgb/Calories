import requests

from flask import redirect, render_template, session, Flask, request, render_template
from functools import wraps

def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function

def calorie_calculator(age, height, gender, weight, activity):
    cal = 0
    cal_extreme_loss = 0
    cal_mild_loss = 0
    cal_maintain_weight = 0
    cal_mild_gain = 0
    cal_extreme_gain = 0
    activity_factor = 0
    if gender == "Male":
        cal = (10*weight) + (6.25*height) - (5*age) + 5
    elif gender == "Female":
        cal = (10*weight) + (6.25*height) - (5*age) - 161
    if activity == "low":
        cal = cal * 1.2
    elif activity == "light":
        cal = cal * 1.375
    elif activity == "moderate":
        cal = cal * 1.55
    elif activity == "high":
        cal = cal * 1.725
    elif activity == "extreme":
        cal = cal * 1.9
    cal_extreme_loss = cal - 1000
    cal_mild_loss = cal - 500
    cal_maintain_weight = cal
    cal_mild_gain = cal + 500
    cal_extreme_gain = cal + 1000
    return cal_extreme_loss, cal_mild_loss, cal_maintain_weight, cal_mild_gain, cal_extreme_gain

    
        




        

    
