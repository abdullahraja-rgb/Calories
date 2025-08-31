# 🔥 Calories

A modern, full-stack web application built with Flask and Python to help users track their daily calorie intake, set goals, and view their nutritional history.

[](https://calories-rose.vercel.app/)
[](https://www.python.org/downloads/)
[](https://opensource.org/licenses/MIT)

## Key Features

  - **👤 Full User Authentication:** Secure user registration, login, and session management with password hashing.
  - **🔍 API-Powered Food Search:** Instantly search for thousands of food items using the **Nutritionix API** to get accurate calorie and nutritional data.
  - **✍️ Flexible Manual Entry:** Log food with multiple convenient methods: total calories, calories per item, or calories per 100g.
  - **📊 Progress Tracking:** Set daily calorie goals and visualize your consumption and remaining calories for the day.
  - **📈 Weekly Progress Chart:** View a chart of your calorie consumption vs. your goal over the last 7 days.
  - **📖 Detailed History:** View a complete, time-stamped log of all your past food entries.
  - **🗑️ Edit Your Entries:** Easily delete incorrect food entries, with calorie totals updated automatically.

-----

## Tech Stack

  - **Backend:** **Python** with the **Flask** micro-framework.
  - **Database:** **PostgreSQL** for a robust, persistent, and scalable database.
  - **Database Hosting:** **Supabase** for managed PostgreSQL hosting.
  - **Frontend:** **HTML5** with **Jinja2** for server-side templating.
  - **Styling:** **Bootstrap 5** for a modern, responsive user interface.
  - **External API:** **Nutritionix API** for real-time nutritional data.
  - **Deployment:** Configured for serverless deployment on **Vercel**.

-----

## Getting Started

Follow these steps to get the application running locally on your machine.

### 1\. Prerequisites

  - Python 3.9+
  - `pip` and `venv`
  - A free [Supabase](https://supabase.com/) account.

### 2\. Installation & Setup

**1. Clone the repository:**

```bash
git clone https://github.com/abdullahraja-rgb/Calories.git
cd Calories
```

**2. Create and activate a virtual environment:**

```bash
# Create the environment
python -m venv venv

# Activate it
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

**3. Install dependencies:**

```bash
pip install -r requirements.txt
```

**4. Set up your Database on Supabase:**

  - Go to [supabase.com](https://supabase.com), create a **New Project**, and save your **Database Password** securely.
  - In your project dashboard, go to the **SQL Editor**.
  - Click **"+ New query"** and run the script below to create your tables:
    ```sql
    -- Create the users table
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    -- Create the tracker table for goals
    CREATE TABLE IF NOT EXISTS tracker (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        goal REAL NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    -- Create the daily tracking summary table
    CREATE TABLE IF NOT EXISTS calorie_tracking (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        date DATE NOT NULL,
        daily_goal REAL NOT NULL,
        consumed_calories REAL DEFAULT 0,
        remaining_calories REAL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        UNIQUE(user_id, date) -- Ensures only one entry per user per day
    );

    -- Create the individual food entries table
    CREATE TABLE IF NOT EXISTS food_entries (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        calorie_tracking_id INTEGER NOT NULL REFERENCES calorie_tracking(id) ON DELETE CASCADE,
        food_item TEXT NOT NULL,
        calories REAL NOT NULL,
        weight REAL,
        consumption_time TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    ```

**5. Set up your Environment Variables:**

  - Create a file named `.env` in the root of the project.
  - In your Supabase project, go to **Settings** \> **Database** and find the **Transaction Pooler** connection string.
  - Add your secret keys and the database URL to the `.env` file:
    ```
    SECRET_KEY='your_super_secret_flask_key'
    NUTRITIONIX_APP_ID='your_nutritionix_app_id'
    NUTRITIONIX_APP_KEY='your_nutritionix_app_key'
    DATABASE_URL='your_supabase_transaction_pooler_connection_url'
    ```

**6. Run the Application:**

```bash
flask run
```

The application will be available at `http://127.0.0.1:5000`.

-----

## Deployment

This application is configured for easy deployment on **Vercel**. The `vercel.json` file handles the build and routing configuration for a serverless Python environment.

To deploy, connect your GitHub repository to Vercel and add your environment variables (`SECRET_KEY`, `NUTRITIONIX_APP_ID`, `NUTRITIONIX_APP_KEY`, and `DATABASE_URL`) to the Vercel project settings.
