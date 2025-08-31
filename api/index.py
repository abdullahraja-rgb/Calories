import os
from flask import Flask, flash, redirect, render_template, request, session, url_for, jsonify
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
'''from extensions import login_required, calorie_calculator'''
import sqlite3
from datetime import datetime, timezone
import requests
from functools import wraps
from typing import List, Dict, Optional
from dataclasses import dataclass
import re 
from difflib import SequenceMatcher
import os
from dotenv import load_dotenv

'''import requests'''

'''from flask import redirect, render_template, session, Flask, request, render_template'''
from functools import wraps

# Load environment variables from .env
load_dotenv()

# Configure application
app = Flask(__name__, template_folder='../templates', static_folder='../static')

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Establish a connection with the db
def get_db():
    connection = sqlite3.connect("cal.db")
    connection.row_factory = sqlite3.Row
    return connection

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


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

    
        




        


@app.route("/")
def layout():
    return render_template("layout.html")

@app.route("/logout")
def logout():
    """Log user out"""
    # Forget any user_id
    session.clear()
    # Redirect user to login form
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    try:
        if request.method == "POST":
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            confirmation = request.form.get('confirmation')

            if not username:
                return ("Username is required!")
            elif not email:
                return ("Email is required!")
            elif not password:
                return ("Password is required!")
            elif not confirmation:
                return ("Password confirmation is required!")
            if password != confirmation:
                return ("Passwords do not match!")

            password_c = generate_password_hash(password)
            connection = get_db()
            connection.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)", (username, password_c, email))
            connection.commit()
            connection.close()
            return redirect('/')
        
        else:
            return render_template("register.html")
    
    except Exception as e:
        return (f"An error occurred: {str(e)}")
    


@app.route("/tracker", methods=["GET", "POST"])
@login_required
def tracker():
    import urllib.parse
    import requests

    search_results = []
    selected_food = None
    selected_food_calories = None
    calorie_status = None

    # Existing logic to get calorie status (unchanged)
    # ...

    if request.method == "POST":
        query = request.form.get("search")
        if not query or not query.strip():
            flash("Please enter a valid search term.", "warning")
            return render_template("tracker.html", 
                                   search_results=search_results, 
                                   calorie_status=calorie_status)

        try:
            # Nutritionix API request with proper encoding
            encoded_query = urllib.parse.quote_plus(query.strip())
            url = f'https://trackapi.nutritionix.com/v2/search/instant?query={encoded_query}'
            headers = {
                'x-app-id': os.environ.get('NUTRITIONIX_APP_ID'),
                'x-app-key': os.environ.get('NUTRITIONIX_APP_KEY'),
                'x-remote-user-id': '0'
            }
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()  # Raise exception for HTTP errors
            data = response.json()

            # Parse the API response
            if 'common' in data and isinstance(data['common'], list):
                for item in data['common']:
                    name = item.get('food_name', 'Unknown').title()
                    photo = item.get('photo', {}).get('thumb', '')

                    # Get detailed nutrition info for each food item
                    food_detail_url = 'https://trackapi.nutritionix.com/v2/natural/nutrients'
                    food_detail_payload = {"query": name}
                    food_detail_response = requests.post(
                        food_detail_url, headers=headers, json=food_detail_payload, timeout=5
                    )
                    food_detail_response.raise_for_status()
                    food_detail_data = food_detail_response.json()

                    if 'foods' in food_detail_data and len(food_detail_data['foods']) > 0:
                        food_detail = food_detail_data['foods'][0]
                        calories = food_detail.get('nf_calories')
                        serving_size_g = food_detail.get('serving_weight_grams', 'Unknown')

                        if name and calories is not None:
                            try:
                                calories = round(float(calories), 2)
                                search_results.append({
                                    'name': name,
                                    'calories': calories,
                                    'serving_size_g': serving_size_g,
                                    'photo': photo
                                })
                            except (ValueError, TypeError):
                                continue

            # Determine selected food if user selects one
            selected_food = request.form.get("food")
            if selected_food:
                selected_food_calories = next(
                    (result["calories"] for result in search_results 
                     if result["name"] == selected_food), 
                    None
                )

        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                error_message = f"Error fetching food data: {e.response.status_code} - {e.response.text}"
            else:
                error_message = f"Error fetching food data: {str(e)}"
            flash(error_message, "danger")
        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", "danger")

    return render_template(
        "tracker.html",
        search_results=search_results,
        selected_food=selected_food,
        selected_food_calories=selected_food_calories,
        calorie_status=calorie_status
    )


@app.route("/manual_tracker", methods=["GET", "POST"])
@login_required
def manual_tracker():
    if request.method == "POST":
        # Get form data
        food_name = request.form.get("food_name")
        calories_option = request.form.get("caloriesOption")  # The option selected by the user
        
        if not food_name or not calories_option:
            flash("Please fill in all fields.", "warning")
            return render_template("manual_tracker.html")

        user_id = session["user_id"]  # Get the current user ID
        connection = get_db()

        # Fetch the daily goal from the `tracker` table
        tracker_record = connection.execute(
            """
            SELECT goal FROM tracker WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

        if not tracker_record:
            flash("Daily goal not set. Please set your goal first.", "warning")
            return render_template("manual_tracker.html")

        daily_goal = tracker_record["goal"]  # Fetch the `goal` value from the `tracker` table

        # Fetch or create a calorie tracking record for the current date
        calorie_tracking_record = connection.execute(
            """
            SELECT id, consumed_calories, remaining_calories 
            FROM calorie_tracking
            WHERE user_id = ? AND date = DATE('now')
            """,
            (user_id,)
        ).fetchone()

        if calorie_tracking_record:
            calorie_tracking_id = calorie_tracking_record["id"]
            consumed_calories = calorie_tracking_record["consumed_calories"]
            remaining_calories = calorie_tracking_record["remaining_calories"]
        else:
            # Create a new calorie tracking record for today
            calorie_tracking_id = connection.execute(
                """
                INSERT INTO calorie_tracking (user_id, date, daily_goal, consumed_calories, remaining_calories)
                VALUES (?, DATE('now'), ?, 0, ?)
                """,
                (user_id, daily_goal, daily_goal)
            ).lastrowid
            consumed_calories = 0
            remaining_calories = daily_goal

        # Handle the different input methods based on the selected option
        try:
            if calories_option == "perItem":
                # Get the calories per item and total items from the form
                calories_per_item = request.form.get("caloriesPerItem")
                total_items = request.form.get("totalItems")

                if not calories_per_item or not total_items:
                    flash("Please fill in all fields.", "warning")
                    return render_template("manual_tracker.html")
                
                calories_per_item = float(calories_per_item)
                total_items = int(total_items)

                total_calories = calories_per_item * total_items  # Calculate total calories

                # Insert the manual food entry into `food_entries`
                connection.execute(
                    """
                    INSERT INTO food_entries (user_id, calorie_tracking_id, food_item, calories, weight, consumption_time)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (user_id, calorie_tracking_id, food_name, total_calories, total_items)
                )

            elif calories_option == "per100g":
                # Get calories per 100g and weight from the form
                calories_per_100g = request.form.get("calories")
                weight = request.form.get("weight")

                if not calories_per_100g or not weight:
                    flash("Please fill in all fields.", "warning")
                    return render_template("manual_tracker.html")
                
                calories_per_100g = float(calories_per_100g)
                weight = int(weight)

                total_calories = (calories_per_100g * weight) / 100  # Calculate total calories based on weight

                # Insert the manual food entry into `food_entries`
                connection.execute(
                    """
                    INSERT INTO food_entries (user_id, calorie_tracking_id, food_item, calories, weight, consumption_time)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (user_id, calorie_tracking_id, food_name, total_calories, weight)
                )

            elif calories_option == "totalCalories":
                # Get the total calories from the form
                total_calories = request.form.get("totalCalories")

                if not total_calories:
                    flash("Please fill in all fields.", "warning")
                    return render_template("manual_tracker.html")
                
                total_calories = float(total_calories)

                # Insert the manual food entry into `food_entries`
                connection.execute(
                    """
                    INSERT INTO food_entries (user_id, calorie_tracking_id, food_item, calories, weight, consumption_time)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (user_id, calorie_tracking_id, food_name, total_calories, 0)  # No weight for this option
                )

            else:
                flash("Invalid calories option selected.", "warning")
                return render_template("manual_tracker.html")

            # Update the calorie tracking totals
            new_consumed_calories = consumed_calories + total_calories
            new_remaining_calories = max(0, remaining_calories - total_calories)

            connection.execute(
                """
                UPDATE calorie_tracking
                SET consumed_calories = ?, remaining_calories = ?
                WHERE id = ?
                """,
                (new_consumed_calories, new_remaining_calories, calorie_tracking_id)
            )

            connection.commit()

            # Provide feedback to the user
            flash(f"Added {food_name} ({total_calories:.2f} kcal) successfully.", "success")
            return redirect(url_for("manual_tracker"))

        except Exception as e:
            flash("An error occurred while adding the food entry. Please try again.", "error")
            print(f"Error: {e}")
        finally:
            connection.close()

    # Render the manual tracker form
    return render_template("manual_tracker.html")


@app.route("/select-food", methods=["POST"])
@login_required
def select_food():
    food_name = request.form.get("food")
    calories_per_100g = request.form.get("calories_per_100g")

    if not food_name or not calories_per_100g:
        flash("Please select a food item.", "warning")
        return redirect(url_for("tracker"))

    try:
        calories_per_100g = float(calories_per_100g)
    except (ValueError, TypeError):
        flash("Invalid calorie value.", "danger")
        return redirect(url_for("tracker"))

    return render_template(
        "tracker.html", 
        selected_food=food_name,
        selected_food_calories=calories_per_100g,
        show_weight_form=True
    )

@app.route("/calculate-calories", methods=["POST"])
@login_required
def calculate_calories():
    connection = None
    try:
        food_name = request.form.get("food")
        calories_per_100g = request.form.get("calories_per_100g")
        weight = request.form.get("weight")
        user_id = session["user_id"]

        # Validate inputs
        if not all([food_name, calories_per_100g, weight]):
            flash("Please provide all required information.", "warning")
            return redirect(url_for("tracker"))

        try:
            weight = float(weight)
            calories_per_100g = float(calories_per_100g)
            if weight <= 0 or calories_per_100g < 0:
                raise ValueError("Weight and calories must be positive numbers")
        except ValueError as e:
            flash(f"Invalid input: {str(e)}", "danger")
            return redirect(url_for("tracker"))

        connection = get_db()
        
        # Get or create today's tracking record
        tracking_record = connection.execute("""
            SELECT id, consumed_calories, remaining_calories 
            FROM calorie_tracking 
            WHERE user_id = ? AND date = DATE('now')
        """, (user_id,)).fetchone()

        if not tracking_record:
            # Get user's goal
            user_goal = connection.execute("""
                SELECT goal FROM tracker WHERE user_id = ?
            """, (user_id,)).fetchone()
            
            daily_goal = user_goal["goal"] if user_goal else 2000
            
            tracking_id = connection.execute("""
                INSERT INTO calorie_tracking (user_id, date, daily_goal, consumed_calories, remaining_calories)
                VALUES (?, DATE('now'), ?, 0, ?)
                RETURNING id
            """, (user_id, daily_goal, daily_goal)).fetchone()["id"]
            
            consumed_calories = 0
            remaining_calories = daily_goal
        else:
            tracking_id = tracking_record["id"]
            consumed_calories = tracking_record["consumed_calories"]
            remaining_calories = tracking_record["remaining_calories"]

        # Calculate and update calories
        total_calories = (calories_per_100g * weight) / 100
        new_consumed_calories = consumed_calories + total_calories
        
        # Get daily goal for remaining calories calculation
        daily_goal = connection.execute("""
            SELECT daily_goal FROM calorie_tracking WHERE id = ?
        """, (tracking_id,)).fetchone()["daily_goal"]
        
        new_remaining_calories = daily_goal - new_consumed_calories

        # Insert food entry
        connection.execute("""
            INSERT INTO food_entries (
                user_id, calorie_tracking_id, food_item, calories, weight, consumption_time
            ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (user_id, tracking_id, food_name, total_calories, weight))

        # Update tracking record
        connection.execute("""
            UPDATE calorie_tracking 
            SET consumed_calories = ?, remaining_calories = ?
            WHERE id = ?
        """, (new_consumed_calories, new_remaining_calories, tracking_id))

        connection.commit()
        flash(f"Added {food_name} ({weight}g, {total_calories:.1f} kcal)", "success")

    except Exception as e:
        if connection:
            connection.rollback()
        flash(f"Error adding food entry: {str(e)}", "danger")
        print(f"Error in calculate_calories: {str(e)}")
    finally:
        if connection:
            connection.close()

    return redirect(url_for("tracker"))

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return ("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return ("must provide password", 403)

        try:
            # Query database for username
            connection = get_db()
            rows = connection.execute("SELECT * FROM users WHERE username = ?", (request.form.get("username"),)).fetchall()
            connection.close()

            # Ensure username exists and password is correct
            if len(rows) != 1 or not check_password_hash(rows[0]["password"], request.form.get("password")):
                return ("invalid username and/or password", 403)

            # Remember which user has logged in
            session["user_id"] = rows[0]["id"]

            # Redirect user to home page
            return redirect("/")

        except Exception as e:
            return (f"An error occurred: {str(e)}", 500)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")
    
# Load the secret key from environment variables
app.secret_key = os.environ.get('SECRET_KEY')

@app.route('/calculator', methods=['GET', 'POST'])
def calorie_calculator_route():
    if request.method == "POST":
        age = request.form.get('age')
        height = request.form.get('height')
        weight = request.form.get('weight')
        gender = request.form.get('gender')
        activity = request.form.get('activity_level')

        # Validate form data
        try:
            age = int(age)
            height = float(height)
            weight = float(weight)
        except ValueError:
            flash("Please enter valid numerical values for age, height, and weight.", "error")
            return redirect("/calculator")

        if not gender or not activity:
            flash("Please select gender and activity level.", "error")
            return redirect("/calculator")

        # Calculate calories
        cal_extreme_loss, cal_mild_loss, cal_maintain_weight, cal_mild_gain, cal_extreme_gain = calorie_calculator(age, height, gender, weight, activity)
        
        return render_template("calculated.html", 
                               cal_extreme_loss=cal_extreme_loss, 
                               cal_mild_loss=cal_mild_loss, 
                               cal_maintain_weight=cal_maintain_weight, 
                               cal_mild_gain=cal_mild_gain, 
                               cal_extreme_gain=cal_extreme_gain)
    else:
        return render_template("calculator.html")

@app.route('/select_calorie', methods=['GET', 'POST'])
@login_required
def select_calorie():
    # Get the selected calorie value from the form
    calorie = request.form.get('calorie')
    id = session["user_id"]
    
    # Get the current user's ID (requires Flask-Login or similar)
 # Flask-Login's current_user provides the logged-in user's details

    # Insert the goal into the tracker table, including the user_id
    connection = get_db()
    connection.execute(
        "INSERT INTO tracker (goal, user_id) VALUES (?, ?)",
        (calorie, id)
    )
    connection.commit()
    connection.close()

    # Show the selected calorie value
    return render_template('select_calorie.html', calorie=calorie)

@app.route("/progress", methods=["GET", "POST"])
@login_required
def progress():
    # Fetch the latest calorie goal from the database
    connection = get_db()

    # Fetch the goal
    goal_row = connection.execute(
        "SELECT goal FROM tracker WHERE user_id = ? ORDER BY id DESC LIMIT 1", 
        (session["user_id"],)
    ).fetchone()

    # Fetch the consumed calories for today
    calorie_tracking_row = connection.execute(
        "SELECT consumed_calories FROM calorie_tracking WHERE user_id = ? AND date = DATE('now')", 
        (session["user_id"],)
    ).fetchone()

    connection.close()

    # Extract the goal and consumed calories from the rows
    goal = round(goal_row[0]) if goal_row else None
    consumed_calories = round(calorie_tracking_row[0]) if calorie_tracking_row else 0

    # Calculate progress percentage
    if goal is not None:
        progress_percentage = (consumed_calories / goal) * 100
        progress_percentage = round(min(100, progress_percentage))  # Cap it at 100% and round it
    else:
        progress_percentage = 0  # If no goal is set, progress is 0%

    # Render the progress page with the goal, consumed calories, and progress
    return render_template(
        'progress.html', 
        goal=goal, 
        consumed_calories=consumed_calories, 
        progress_percentage=progress_percentage
    )



@app.route("/history", methods=["GET"])
@login_required
def history():
    # Connect to the database
    connection = get_db()

    # Get the food entries for the current user
    food_entries = connection.execute(
        """
        SELECT id, food_item, calories, consumption_time
        FROM food_entries
        WHERE user_id = ?
        ORDER BY consumption_time DESC
        """,
        (session["user_id"],)
    ).fetchall()

    connection.close()

    # Render the history page with the food entries
    return render_template("history.html", food_entries=food_entries)

@app.route('/delete-food/<int:food_id>', methods=['DELETE'])
@login_required
def delete_food(food_id):
    try:
        # Connect to the database
        connection = get_db()

        # Retrieve the food item and its calories
        food_entry = connection.execute(
            """
            SELECT calories, consumption_time 
            FROM food_entries 
            WHERE id = ? AND user_id = ?
            """,
            (food_id, session["user_id"])
        ).fetchone()

        if not food_entry:
            return jsonify({'error': 'Food item not found'}), 404

        calories_to_deduct = food_entry['calories']
        consumption_date = food_entry['consumption_time'][:10]  # Extract only the date part

        # Delete the food item from the food_entries table
        connection.execute(
            "DELETE FROM food_entries WHERE id = ? AND user_id = ?",
            (food_id, session["user_id"])
        )

        # Update the calorie_tracking table
        connection.execute(
            """
            UPDATE calorie_tracking
            SET consumed_calories = consumed_calories - ?
            WHERE user_id = ? AND date = ?
            """,
            (calories_to_deduct, session["user_id"], consumption_date)
        )

        # Commit the changes and close the connection
        connection.commit()
        connection.close()

        return jsonify({'message': 'Food item deleted successfully'}), 200

    except Exception as e:
        # Handle errors and close the connection if open
        connection.rollback()
        connection.close()
        return jsonify({'error': str(e)}), 500



@app.errorhandler(HTTPException)
def handle_error(error):
    """Handle HTTP errors gracefully."""
    return render_template("error.html", error=error), error.code



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
