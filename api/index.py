import os
import logging
from flask import Flask, flash, redirect, render_template, request, session, url_for, jsonify
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timezone
import requests
from functools import wraps
import tempfile
import shutil
import urllib.parse
from dotenv import load_dotenv
import re
import psycopg2
import psycopg2.extras

# Load environment variables from .env
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure application
app = Flask(__name__, template_folder='../templates', static_folder='../static')

# Simple session configuration for Vercel (serverless)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-secret-key-in-production')
app.config["SESSION_PERMANENT"] = False
app.config["TEMPLATES_AUTO_RELOAD"] = True

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

def get_db():
    """Get a connection to the persistent PostgreSQL database."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL environment variable is not set.")
        raise ValueError("Database connection URL is missing")
    try:
        # Connect to the external database
        connection = psycopg2.connect(db_url)
        # Return a connection object that provides dictionary-like access to rows
        # This makes it behave like sqlite3.Row
        connection.cursor_factory = psycopg2.extras.DictCursor
        logger.info("Successfully connected to the PostgreSQL database.")
        return connection
    except psycopg2.OperationalError as e:
        logger.error(f"Could not connect to the database: {e}")
        raise

def login_required(f):
    """
    Decorate routes to require login.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def calorie_calculator(age, height, gender, weight, activity):
    """Calculate calorie needs based on user input"""
    if gender == "Male":
        cal = (10 * weight) + (6.25 * height) - (5 * age) + 5
    elif gender == "Female":
        cal = (10 * weight) + (6.25 * height) - (5 * age) - 161
    else:
        # Default to male calculation if gender not specified
        cal = (10 * weight) + (6.25 * height) - (5 * age) + 5
    
    # Apply activity multiplier
    activity_multipliers = {
        "low": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "high": 1.725,
        "extreme": 1.9
    }
    
    cal *= activity_multipliers.get(activity, 1.2)  # Default to low activity if not found
    
    # Calculate different calorie goals
    cal_extreme_loss = cal - 1000
    cal_mild_loss = cal - 500
    cal_maintain_weight = cal
    cal_mild_gain = cal + 500
    cal_extreme_gain = cal + 1000
    
    return cal_extreme_loss, cal_mild_loss, cal_maintain_weight, cal_mild_gain, cal_extreme_gain

@app.route("/")
def index():
    """Home page"""
    return render_template("layout.html")

@app.route("/logout")
def logout():
    """Log user out"""
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("index"))

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirmation = request.form.get('confirmation')

        # Validate input
        if not username or not email or not password or not confirmation:
            flash("All fields are required.", "danger")
            return render_template("register.html")
        
        if password != confirmation:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")
        
        # Validate email format
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash("Please enter a valid email address.", "danger")
            return render_template("register.html")
        
        # Validate password strength
        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "danger")
            return render_template("register.html")

        try:
            password_hash = generate_password_hash(password)
            connection = get_db()
            cursor = connection.cursor()
            
            # Check if username or email already exists
            cursor.execute(
                "SELECT id FROM users WHERE username = %s OR email = %s", 
                (username, email)
            )
            existing_user = cursor.fetchone()
            
            if existing_user:
                flash("Username or email already exists.", "danger")
                cursor.close()
                connection.close()
                return render_template("register.html")
            
            # Insert new user
            cursor.execute(
                "INSERT INTO users (username, password, email) VALUES (%s, %s, %s) RETURNING id", 
                (username, password_hash, email)
            )
            connection.commit()
            cursor.close()
            connection.close()
            
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
        
        except psycopg2.Error as e:
            logger.error(f"Database error during registration: {e}")
            flash("An error occurred during registration. Please try again.", "danger")
            return render_template("register.html")
        except Exception as e:
            logger.error(f"Unexpected error during registration: {e}")
            flash("An unexpected error occurred. Please try again.", "danger")
            return render_template("register.html")
    
    return render_template("register.html")

@app.route("/tracker", methods=["GET", "POST"])
@login_required
def tracker():
    """Food tracker with Nutritionix API integration"""
    search_results = []
    selected_food = None
    selected_food_calories = None

    if request.method == "POST":
        query = request.form.get("search")
        if not query or not query.strip():
            flash("Please enter a valid search term.", "warning")
            return render_template("tracker.html", search_results=search_results)

        try:
            # Nutritionix API request with proper encoding
            encoded_query = urllib.parse.quote_plus(query.strip())
            url = f'https://trackapi.nutritionix.com/v2/search/instant?query={encoded_query}'
            headers = {
                'x-app-id': os.environ.get('NUTRITIONIX_APP_ID'),
                'x-app-key': os.environ.get('NUTRITIONIX_APP_KEY'),
                'x-remote-user-id': '0'
            }
            
            if not headers['x-app-id'] or not headers['x-app-key']:
                flash("Nutritionix API is not configured properly.", "danger")
                return render_template("tracker.html", search_results=search_results)
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
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
                        food_detail_url, headers=headers, json=food_detail_payload, timeout=10
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
            logger.error(f"API request error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                # Check for 401 Unauthorized error specifically
                if e.response.status_code == 401:
                    flash("Daily API search limit may have been reached. Please try again later.", "warning")
                else:
                    # Handle other potential HTTP errors
                    flash(f"Error fetching food data. Status code: {e.response.status_code}", "danger")
            else:
                # Handle network errors where there is no response
                flash("Error fetching food data. Please check your connection and try again.", "danger")
        except Exception as e:
            logger.error(f"Unexpected error in tracker: {e}")
            flash("An unexpected error occurred. Please try again.", "danger")

    return render_template(
        "tracker.html",
        search_results=search_results,
        selected_food=selected_food,
        selected_food_calories=selected_food_calories
    )

@app.route("/manual_tracker", methods=["GET", "POST"])
@login_required
def manual_tracker():
    """Manual food entry tracker"""
    if request.method == "POST":
        food_name = request.form.get("food_name")
        calories_option = request.form.get("caloriesOption")

        if not food_name or not calories_option:
            flash("Please fill in all fields.", "warning")
            return render_template("manual_tracker.html")

        user_id = session["user_id"]
        connection = get_db()
        cursor = connection.cursor()

        try:
            # Fetch the daily goal from the tracker table
            cursor.execute(
                "SELECT goal FROM tracker WHERE user_id = %s ORDER BY created_at DESC LIMIT 1",
                (user_id,)
            )
            tracker_record = cursor.fetchone()

            if not tracker_record:
                flash("Daily goal not set. Please set your goal first.", "warning")
                cursor.close()
                connection.close()
                return render_template("manual_tracker.html")

            daily_goal = tracker_record["goal"]

            # Fetch or create a calorie tracking record for the current date
            cursor.execute(
                """
                SELECT id, consumed_calories, remaining_calories 
                FROM calorie_tracking
                WHERE user_id = %s AND date = CURRENT_DATE
                """,
                (user_id,)
            )
            calorie_tracking_record = cursor.fetchone()

            if calorie_tracking_record:
                calorie_tracking_id = calorie_tracking_record["id"]
                consumed_calories = calorie_tracking_record["consumed_calories"]
                remaining_calories = calorie_tracking_record["remaining_calories"]
            else:
                # Create a new calorie tracking record for today
                cursor.execute(
                    """
                    INSERT INTO calorie_tracking (user_id, date, daily_goal, consumed_calories, remaining_calories)
                    VALUES (%s, CURRENT_DATE, %s, 0, %s) RETURNING id
                    """,
                    (user_id, daily_goal, daily_goal)
                )
                calorie_tracking_id = cursor.fetchone()["id"]
                consumed_calories = 0
                remaining_calories = daily_goal

            # Handle the different input methods
            total_calories = 0
            weight = 0
            
            if calories_option == "perItem":
                calories_per_item = request.form.get("caloriesPerItem")
                total_items = request.form.get("totalItems")
                
                if not calories_per_item or not total_items:
                    flash("Please fill in all fields.", "warning")
                    cursor.close()
                    connection.close()
                    return render_template("manual_tracker.html")
                
                try:
                    calories_per_item = float(calories_per_item)
                    total_items = int(total_items)
                    total_calories = calories_per_item * total_items
                    weight = total_items
                except ValueError:
                    flash("Please enter valid numbers.", "danger")
                    cursor.close()
                    connection.close()
                    return render_template("manual_tracker.html")

            elif calories_option == "per100g":
                calories_per_100g = request.form.get("calories")
                weight_input = request.form.get("weight")
                
                if not calories_per_100g or not weight_input:
                    flash("Please fill in all fields.", "warning")
                    cursor.close()
                    connection.close()
                    return render_template("manual_tracker.html")
                
                try:
                    calories_per_100g = float(calories_per_100g)
                    weight = float(weight_input)
                    total_calories = (calories_per_100g * weight) / 100
                except ValueError:
                    flash("Please enter valid numbers.", "danger")
                    cursor.close()
                    connection.close()
                    return render_template("manual_tracker.html")

            elif calories_option == "totalCalories":
                total_calories_input = request.form.get("totalCalories")
                
                if not total_calories_input:
                    flash("Please fill in all fields.", "warning")
                    cursor.close()
                    connection.close()
                    return render_template("manual_tracker.html")
                
                try:
                    total_calories = float(total_calories_input)
                except ValueError:
                    flash("Please enter a valid number.", "danger")
                    cursor.close()
                    connection.close()
                    return render_template("manual_tracker.html")

            else:
                flash("Invalid calories option selected.", "warning")
                cursor.close()
                connection.close()
                return render_template("manual_tracker.html")

            # Insert the food entry
            cursor.execute(
                """
                INSERT INTO food_entries (user_id, calorie_tracking_id, food_item, calories, weight, consumption_time)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """,
                (user_id, calorie_tracking_id, food_name, total_calories, weight)
            )

            # Update the calorie tracking totals
            new_consumed_calories = consumed_calories + total_calories
            new_remaining_calories = max(0, daily_goal - new_consumed_calories)

            cursor.execute(
                """
                UPDATE calorie_tracking
                SET consumed_calories = %s, remaining_calories = %s
                WHERE id = %s
                """,
                (new_consumed_calories, new_remaining_calories, calorie_tracking_id)
            )

            connection.commit()
            flash(f"Added {food_name} ({total_calories:.2f} kcal) successfully.", "success")
            return redirect(url_for("manual_tracker"))

        except Exception as e:
            connection.rollback()
            logger.error(f"Error in manual_tracker: {e}")
            flash("An error occurred while adding the food entry. Please try again.", "danger")
        finally:
            cursor.close()
            connection.close()

    return render_template("manual_tracker.html")

@app.route("/select-food", methods=["POST"])
@login_required
def select_food():
    """Handle food selection from search results"""
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
    """Calculate calories based on food and weight"""
    connection = None
    cursor = None
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
        cursor = connection.cursor()
        
        # Get or create today's tracking record
        cursor.execute("""
            SELECT id, consumed_calories, daily_goal 
            FROM calorie_tracking 
            WHERE user_id = %s AND date = CURRENT_DATE
        """, (user_id,))
        tracking_record = cursor.fetchone()

        if not tracking_record:
            # Get user's goal
            cursor.execute("""
                SELECT goal FROM tracker WHERE user_id = %s ORDER BY created_at DESC LIMIT 1
            """, (user_id,))
            user_goal = cursor.fetchone()
            
            daily_goal = user_goal["goal"] if user_goal else 2000
            
            cursor.execute("""
                INSERT INTO calorie_tracking (user_id, date, daily_goal, consumed_calories, remaining_calories)
                VALUES (%s, CURRENT_DATE, %s, 0, %s) RETURNING id
            """, (user_id, daily_goal, daily_goal))
            tracking_id = cursor.fetchone()["id"]
            consumed_calories = 0
        else:
            tracking_id = tracking_record["id"]
            consumed_calories = tracking_record["consumed_calories"]
            daily_goal = tracking_record["daily_goal"]

        # Calculate and update calories
        total_calories = (calories_per_100g * weight) / 100
        new_consumed_calories = consumed_calories + total_calories
        new_remaining_calories = max(0, daily_goal - new_consumed_calories)

        # Insert food entry
        cursor.execute("""
            INSERT INTO food_entries (
                user_id, calorie_tracking_id, food_item, calories, weight, consumption_time
            ) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        """, (user_id, tracking_id, food_name, total_calories, weight))

        # Update tracking record
        cursor.execute("""
            UPDATE calorie_tracking 
            SET consumed_calories = %s, remaining_calories = %s
            WHERE id = %s
        """, (new_consumed_calories, new_remaining_calories, tracking_id))

        connection.commit()
        flash(f"Added {food_name} ({weight}g, {total_calories:.1f} kcal)", "success")

    except Exception as e:
        if connection:
            connection.rollback()
        logger.error(f"Error in calculate_calories: {e}")
        flash(f"Error adding food entry: {str(e)}", "danger")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

    return redirect(url_for("tracker"))

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any user_id
    session.clear()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Validate input
        if not username:
            flash("Please provide a username.", "danger")
            return render_template("login.html")
        
        if not password:
            flash("Please provide a password.", "danger")
            return render_template("login.html")

        try:
            # Query database for username
            connection = get_db()
            cursor = connection.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE username = %s", 
                (username,)
            )
            user = cursor.fetchone()
            cursor.close()
            connection.close()

            # Check if user exists and password is correct
            if user is None or not check_password_hash(user["password"], password):
                flash("Invalid username or password.", "danger")
                return render_template("login.html")

            # Remember which user has logged in
            session["user_id"] = user["id"]
            session["username"] = user["username"]

            # Redirect to requested page or home
            next_page = request.args.get('next')
            flash(f"Welcome back, {user['username']}!", "success")
            return redirect(next_page or url_for("index"))

        except Exception as e:
            logger.error(f"Login error: {e}")
            flash("An error occurred during login. Please try again.", "danger")
            return render_template("login.html")

    return render_template("login.html")

@app.route('/calculator', methods=['GET', 'POST'])
def calorie_calculator_route():
    """Calorie calculator route"""
    if request.method == "POST":
        age = request.form.get('age')
        height = request.form.get('height')
        weight = request.form.get('weight')
        gender = request.form.get('gender')
        activity = request.form.get('activity_level')

        # Validate form data
        if not all([age, height, weight, gender, activity]):
            flash("Please fill in all fields.", "danger")
            return render_template("calculator.html")

        try:
            age = int(age)
            height = float(height)
            weight = float(weight)
            
            if age <= 0 or height <= 0 or weight <= 0:
                raise ValueError("Values must be positive")
                
        except ValueError:
            flash("Please enter valid numerical values for age, height, and weight.", "danger")
            return render_template("calculator.html")

        # Calculate calories
        try:
            cal_extreme_loss, cal_mild_loss, cal_maintain_weight, cal_mild_gain, cal_extreme_gain = calorie_calculator(
                age, height, gender, weight, activity
            )
            
            return render_template("calculated.html", 
                                cal_extreme_loss=round(cal_extreme_loss), 
                                cal_mild_loss=round(cal_mild_loss), 
                                cal_maintain_weight=round(cal_maintain_weight), 
                                cal_mild_gain=round(cal_mild_gain), 
                                cal_extreme_gain=round(cal_extreme_gain))
        except Exception as e:
            logger.error(f"Error in calorie calculator: {e}")
            flash("An error occurred during calculation. Please try again.", "danger")
            return render_template("calculator.html")
    else:
        return render_template("calculator.html")

@app.route('/select_calorie', methods=['GET', 'POST'])
@login_required
def select_calorie():
    """Select calorie goal"""
    if request.method == "POST":
        calorie = request.form.get('calorie')
        user_id = session["user_id"]
        
        if not calorie:
            flash("Please select a calorie goal.", "danger")
            return render_template("select_calorie.html")
        
        try:
            calorie = float(calorie)
            if calorie <= 0:
                raise ValueError("Calorie goal must be positive")
        except ValueError:
            flash("Please enter a valid calorie goal.", "danger")
            return render_template("select_calorie.html")

        # Insert the goal into the tracker table
        connection = get_db()
        cursor = connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO tracker (goal, user_id) VALUES (%s, %s)",
                (calorie, user_id)
            )
            connection.commit()
            flash(f"Calorie goal set to {calorie} kcal per day.", "success")
        except Exception as e:
            logger.error(f"Error setting calorie goal: {e}")
            flash("An error occurred while setting your goal. Please try again.", "danger")
        finally:
            cursor.close()
            connection.close()
        
        return redirect(url_for("progress"))
    
    # GET request - show the form
    return render_template('select_calorie.html')

@app.route("/progress")
@login_required
def progress():
    """Progress tracking page"""
    connection = get_db()
    cursor = connection.cursor()
    try:
        # Fetch the latest calorie goal from the database
        cursor.execute(
            "SELECT goal FROM tracker WHERE user_id = %s ORDER BY id DESC LIMIT 1", 
            (session["user_id"],)
        )
        goal_row = cursor.fetchone()

        # Fetch the consumed calories for today
        cursor.execute(
            "SELECT consumed_calories FROM calorie_tracking WHERE user_id = %s AND date = CURRENT_DATE", 
            (session["user_id"],)
        )
        calorie_tracking_row = cursor.fetchone()

        # Extract the goal and consumed calories from the rows
        goal = round(goal_row["goal"]) if goal_row else None
        consumed_calories = round(calorie_tracking_row["consumed_calories"]) if calorie_tracking_row else 0

        # Calculate progress percentage
        if goal is not None and goal > 0:
            progress_percentage = min(100, (consumed_calories / goal) * 100)
        else:
            progress_percentage = 0

        # Get weekly progress data for chart
        cursor.execute("""
            SELECT date, consumed_calories, daily_goal 
            FROM calorie_tracking 
            WHERE user_id = %s AND date >= CURRENT_DATE - INTERVAL '6 days'
            ORDER BY date
        """, (session["user_id"],))
        weekly_data = cursor.fetchall()

        # Format weekly data for chart
        chart_labels = []
        chart_consumed = []
        chart_goal = []
        
        for row in weekly_data:
            chart_labels.append(str(row["date"])[5:10])  # Extract MM-DD from YYYY-MM-DD
            chart_consumed.append(row["consumed_calories"])
            chart_goal.append(row["daily_goal"])

        return render_template(
            'progress.html', 
            goal=goal, 
            consumed_calories=consumed_calories, 
            progress_percentage=round(progress_percentage),
            chart_labels=chart_labels,
            chart_consumed=chart_consumed,
            chart_goal=chart_goal
        )
    except Exception as e:
        logger.error(f"Error in progress: {e}")
        flash("An error occurred while loading your progress.", "danger")
        return render_template('progress.html', goal=None, consumed_calories=0, progress_percentage=0)
    finally:
        cursor.close()
        connection.close()

@app.route("/history")
@login_required
def history():
    """Food history page"""
    connection = get_db()
    cursor = connection.cursor()
    try:
        # Get the food entries for the current user
        cursor.execute(
            """
            SELECT id, food_item, calories, consumption_time
            FROM food_entries
            WHERE user_id = %s
            ORDER BY consumption_time DESC
            """,
            (session["user_id"],)
        )
        food_entries = cursor.fetchall()

        return render_template("history.html", food_entries=food_entries)
    except Exception as e:
        logger.error(f"Error in history: {e}")
        flash("An error occurred while loading your history.", "danger")
        return render_template("history.html", food_entries=[])
    finally:
        cursor.close()
        connection.close()

@app.route('/delete-food/<int:food_id>', methods=['DELETE'])
@login_required
def delete_food(food_id):
    """Delete food entry (AJAX)"""
    connection = None
    cursor = None
    try:
        connection = get_db()
        cursor = connection.cursor()

        # Retrieve the food item and its calories
        cursor.execute(
            """
            SELECT calories, consumption_time 
            FROM food_entries 
            WHERE id = %s AND user_id = %s
            """,
            (food_id, session["user_id"])
        )
        food_entry = cursor.fetchone()

        if not food_entry:
            return jsonify({'error': 'Food item not found'}), 404

        calories_to_deduct = food_entry['calories']
        consumption_date = food_entry['consumption_time'].date()  # Extract only the date part

        # Delete the food item from the food_entries table
        cursor.execute(
            "DELETE FROM food_entries WHERE id = %s AND user_id = %s",
            (food_id, session["user_id"])
        )

        # Update the calorie_tracking table
        cursor.execute(
            """
            UPDATE calorie_tracking
            SET consumed_calories = consumed_calories - %s
            WHERE user_id = %s AND date = %s
            """,
            (calories_to_deduct, session["user_id"], consumption_date)
        )

        # Commit the changes
        connection.commit()

        return jsonify({'message': 'Food item deleted successfully'}), 200

    except Exception as e:
        if connection:
            connection.rollback()
        logger.error(f"Error deleting food: {e}")
        return jsonify({'error': 'An error occurred while deleting the food item'}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return render_template('error.html', error=error, message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    connection = get_db()
    connection.rollback()
    return render_template('error.html', error=error, message="Internal server error"), 500

@app.errorhandler(Exception)
def handle_exception(error):
    """Handle all other exceptions"""
    logger.error(f"Unhandled exception: {error}")
    return render_template('error.html', error=error, message="An unexpected error occurred"), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))