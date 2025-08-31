# 🔥 Calories


A modern, full-stack web application built with Flask and Python to help users track their daily calorie intake, set goals, and view their nutritional history.

[![Live Demo](https://img.shields.io/badge/Live-Demo-brightgreen.svg)](https://calories-rose.vercel.app/)
[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Key Features

- **👤 Full User Authentication:** Secure user registration, login, and session management with password hashing.
- **🔍 API-Powered Food Search:** Instantly search for thousands of food items using the **Nutritionix API** to get accurate calorie and nutritional data.
- **✍️ Flexible Manual Entry:** Log food with multiple convenient methods: total calories, calories per item, or calories per 100g.
- **📊 Progress Tracking:** Set daily calorie goals and visualize your consumption and remaining calories for the day.
- **📖 Detailed History:** View a complete, time-stamped log of all your past food entries.
- **🗑️ Edit Your Entries:** Easily delete incorrect food entries, with calorie totals updated automatically.

## Tech Stack

- **Backend:** **Python** with the **Flask** micro-framework.
- **Database:** **SQLite3** for lightweight and portable data storage.
- **Frontend:** **HTML5** with **Jinja2** for server-side templating.
- **Styling:** **Bootstrap 5** for a modern, responsive user interface.
- **External API:** **Nutritionix API** for real-time nutritional data.
- **Deployment:** Configured for serverless deployment on **Vercel**.

## Getting Started

Follow these steps to get the application running locally on your machine.

### 1. Prerequisites
- Python 3.9+
- `pip` and `venv`

### 2. Installation & Setup

**1. Clone the repository:**
```bash
git clone [https://github.com/abdullahraja-rgb/Calories.git](https://github.com/abdullahraja-rgb/Calories.git)
cd your-repo-name
````

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

**4. Set up your Environment Variables:**

  - Create a file named `.env` in the root of the project.
  - Add your secret keys to this file:
    ```
    SECRET_KEY='your_super_secret_flask_key'
    NUTRITIONIX_APP_ID='your_nutritionix_app_id'
    NUTRITIONIX_APP_KEY='your_nutritionix_app_key'
    ```

**5. Initialize the Database:**

  - You'll need a way to create your database tables. It's recommended to have a small Python script (`init_db.py`) to set up the initial `cal.db` file with the necessary tables (`users`, `tracker`, etc.).

**6. Run the Application:**

```bash
flask run
```

The application will be available at `http://127.0.0.1:5000`.

## Deployment

This application is configured for easy deployment on **Vercel**. The `vercel.json` file handles the build and routing configuration for a serverless Python environment. To deploy, connect your GitHub repository to Vercel and add your environment variables to the project settings.

```
```
