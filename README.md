# Calories

# Calorie Tracker Web Application

## Overview
This is a Flask-based web application designed to help users track their daily calorie intake with features for manual and API-based food tracking.

## Key Features

### User Authentication
- **Registration**: Users can create an account with username, email, and password
- **Login**: Secure login with password hashing
- **Logout**: Session management with secure logout functionality

### Calorie Tracking Modes

#### 1. API-Based Food Tracker
- Search for food items using Nutritionix API
- Retrieve detailed nutritional information
- View food search results with calories and serving sizes
- Select and log food items

#### 2. Manual Food Entry
- Multiple calorie input methods:
  - Calories per item
  - Calories per 100g
  - Total calories
- Tracks daily calorie consumption
- Updates remaining calories in real-time

## Technologies Used
- **Backend**: Flask
- **Database**: SQLite
- **Authentication**: Werkzeug security
- **API Integration**: Nutritionix API
- **Session Management**: Flask-Session

## Setup Requirements
- Python
- Flask
- SQLite
- Nutritionix API credentials
- Required Python packages (listed in requirements.txt)

## Security Features
- Password hashing
- Session management
- Cache control headers
- Error handling
- Input validation

## Database Schema
- Users table
- Calorie tracking table
- Food entries table

## Installation
1. Clone the repository
2. Install dependencies
3. Set up Nutritionix API credentials
4. Initialize SQLite database
5. Run the Flask application

## Contributions
Open to contributions. Please follow coding standards and submit pull requests.

