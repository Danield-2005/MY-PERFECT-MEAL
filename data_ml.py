# Import required libraries for database, ML, and data processing
import sqlite3  # Database management
import json     # JSON data handling 
import numpy as np  # Numerical operations
import os  # File and path operations
import pickle  # Model serialization
from sklearn.ensemble import RandomForestClassifier  # ML model
import pandas as pd  # Data manipulation

# Global configuration
DB_PATH = 'recommendation.db'  # SQLite database path
MODEL_PATH = 'random_forest_model.pkl'  # Trained model storage path

# Load the trained Random Forest model if it exists
rf_model = None
if os.path.exists(MODEL_PATH):
    with open(MODEL_PATH, "rb") as f:
        rf_model = pickle.load(f)
    print("Random Forest model loaded successfully.")
else:
    print(f"Model file not found at {MODEL_PATH}. Please train the model first.")

def init_db(db_path='recommendation.db'):
    
    """
    Initialize the SQLite database with required tables.
    
    Creates four main tables:
    - Users: Stores user profiles and preferences
    - Meals: Stores meal/cuisine information
    - Interactions: Records user-meal interactions (likes/dislikes)
    - Searches: Stores user search history
    
    Args:
        db_path (str): Path to the SQLite database file
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Users table: Store user information and preferences
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            temperature_bias FLOAT,  
            tourist_bias FLOAT,      
            emotion TEXT,            
            other_preferences TEXT
            )
    ''')

    # Meals table: Store cuisine information
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Meals (
            meal_id INTEGER PRIMARY KEY AUTOINCREMENT,
            cuisine TEXT,                
            temperature_category TEXT,    
            popularity_score FLOAT,       
            location_type TEXT,          
            other_features TEXT          
        )
    ''')

    # Interactions table: Store user feedback on meals
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Interactions (
            interaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            meal_id TEXT,
            feedback INTEGER,            
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES Users(user_id)
        )
    ''')

    # Searches table: Store search history
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Searches (
            search_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            cuisines TEXT,              
            tastes TEXT,                
            diet TEXT,                
            price_range TEXT,           
            location TEXT,             
            emotion TEXT,               
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES Users(user_id)
        )
    ''')

    conn.commit()
    conn.close()

def get_user_data(user_id, db_path=DB_PATH):
    """
    Retrieve user preferences and biases from database.
    
    Args:
        user_id (int): User's unique identifier
        db_path (str): Database path
    
    Returns:
        dict: User's preference data including temperature_bias, tourist_bias, and emotion
    
    Raises:
        ValueError: If user_id not found
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT temperature_bias, tourist_bias, emotion FROM Users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "temperature_bias": row[0],
            "tourist_bias": row[1],
            "emotion": row[2]
        }
    else:
        raise ValueError(f"No user data found for user_id {user_id}")

def prepare_training_data(DB_PATH):
    """
    Extract and preprocess data from database for model training.
    
    Combines data from Users, Searches, and Interactions tables to create
    feature vectors and labels for training the recommendation model.
    
    Args:
        DB_PATH (str): Path to the database
    
    Returns:
        tuple: (X, y) where X is feature matrix and y is binary labels
    """
    conn = sqlite3.connect(DB_PATH)
    
    # Load all relevant tables
    users_df = pd.read_sql_query("SELECT * FROM Users", conn)
    searches_df = pd.read_sql_query("SELECT * FROM Searches", conn)
    interactions_df = pd.read_sql_query("SELECT * FROM Interactions", conn)
    conn.close()

    data = []
    labels = []
    
    # Process each interaction record
    for _, interaction in interactions_df.iterrows():
        user_id = interaction['user_id']
        feedback = interaction['feedback']  # 1 = Like, 0 = Dislike
        
        # Get user preferences
        user_row = users_df[users_df['user_id'] == user_id].iloc[0]
        temperature_bias = user_row['temperature_bias']
        tourist_bias = user_row['tourist_bias']
        emotion = {"happy": 2, "neutral": 1, "sad": 0}.get(user_row['emotion'], 1)
        
        # Get search history
        search_row = searches_df[searches_df['user_id'] == user_id]
        if search_row.empty:
            continue
        search_row = search_row.iloc[-1]  # Use most recent search
        
        # Extract and process search preferences
        cuisines = json.loads(search_row['cuisines'])
        tastes = json.loads(search_row['tastes'])
        diet = search_row['diet']
        price_range = json.loads(search_row['price_range'])
        
        # Create feature vectors
        all_cuisines = ["Italian", "American", "Mexican", "Japanese", "Asian", "European", "Mediterranean", "Thai"]
        cuisine_vector = [1 if cuisine in cuisines else 0 for cuisine in all_cuisines]

        all_tastes = ["Sweet", "Salty", "Sour", "Bitter", "Umami", "Spicy"]
        taste_vector = [1 if taste in tastes else 0 for taste in all_tastes]

        diet_vector = [
            1 if diet == "Vegan" else 0,
            1 if diet == "Vegetarian" else 0,
            1 if diet == "None" else 0
        ]
        
        price_min = price_range[0]
        price_max = price_range[1]
        
        # Combine all features
        feature_vector = (
            [temperature_bias, tourist_bias, emotion] +
            cuisine_vector +
            taste_vector +
            diet_vector +
            [price_min, price_max]
        )
        
        data.append(feature_vector)
        labels.append(feedback)
    
    return np.array(data), np.array(labels)

def get_or_create_user(username, db_path=DB_PATH):
    """
    Retrieve existing user or create new user profile.
    
    Args:
        username (str): User's username
        db_path (str): Database path
    
    Returns:
        tuple: (user_info dict, is_new_user boolean)
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, temperature_bias, tourist_bias, emotion, other_preferences FROM Users WHERE username=?", (username,))
    row = cursor.fetchone()
    
    if row:
        # Existing user
        user_info = {
            'user_id': row[0],
            'temperature_bias': row[1],
            'tourist_bias': row[2],
            'emotion': row[3],
            'other_preferences': row[4]
        }
        is_new_user = False
    else:
        # Create new user with default values
        cursor.execute(
            "INSERT INTO Users(username, temperature_bias, tourist_bias, emotion, other_preferences) VALUES(?,?,?,?,?)",
            (username, 0.5, 0.5, 'neutral', '{}')
        )
        conn.commit()
        user_id = cursor.lastrowid
        user_info = {
            'user_id': user_id,
            'temperature_bias': 0.5,
            'tourist_bias': 0.5,
            'emotion': 'neutral',
            'other_preferences': '{}'
        }
        is_new_user = True
        
    conn.close()
    return user_info, is_new_user

def record_interaction(user_id, meal_id_index, feedback, db_path=DB_PATH):
    """
    Record user's feedback on a meal/cuisine.
    
    Args:
        user_id (int): User's ID
        meal_id_index (int): Index of the meal in the cuisine list
        feedback (int): 1 for like, 0 for dislike
        db_path (str): Database path
    """
    # Map indices to cuisine names
    meal_id_map = {
        0: "Italian",
        1: "American",
        2: "Mexican",
        3: "Japanese",
        4: "Asian",
        5: "European",
        6: "Mediterranean",
        7: "Thai"
    }
    meal_id = meal_id_map.get(meal_id_index, "Unknown")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO Interactions(user_id, meal_id, feedback) VALUES(?,?,?)",
            (user_id, meal_id, feedback)
        )
        conn.commit()
    finally:
        conn.close()

def save_user_setup(user_id, emotion, db_path=DB_PATH):
    """
    Update user's emotional state in database.
    
    Args:
        user_id (int): User's ID
        emotion (str): Current emotion ('happy', 'neutral', or 'sad')
        db_path (str): Database path
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE Users SET emotion=? WHERE user_id=?", (emotion, user_id))
    conn.commit()
    conn.close()

def save_user_preferences(user_id, q1, q2, q3, db_path=DB_PATH):
    """
    Save user's preference responses and calculate bias values.
    
    Args:
        user_id (int): User's ID
        q1 (str): Response to cold food preference
        q2 (str): Response to warm food preference
        q3 (str): Response to local food preference
        db_path (str): Database path
    """
    preferences = {
        'q1': q1,  # Cold food preference
        'q2': q2,  # Warm food preference
        'q3': q3   # Local food preference
    }
    preferences_json = json.dumps(preferences)

    # Calculate bias values
    temperature_bias = calculate_temperature_bias(q1, q2)
    tourist_bias = calculate_tourist_bias(q3)

    # Update database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE Users
        SET other_preferences=?, temperature_bias=?, tourist_bias=?
        WHERE user_id=?
    """, (preferences_json, temperature_bias, tourist_bias, user_id))
    conn.commit()
    conn.close()

def save_search_query(user_id, cuisines, tastes, diet, price_range, location, emotion, db_path=DB_PATH):
    """
    Save user's search criteria to database.
    
    Args:
        user_id (int): User's ID
        cuisines (list): Selected cuisines
        tastes (list): Selected taste preferences
        diet (str): Dietary preference
        price_range (list): Min and max price levels
        location (str): Search location
        emotion (str): Current emotion
        db_path (str): Database path
    """
    cuisines_str = json.dumps(cuisines)
    tastes_str = json.dumps(tastes)
    price_range_str = json.dumps(price_range)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Searches(user_id, cuisines, tastes, diet, price_range, location, emotion)
        VALUES(?,?,?,?,?,?,?)
    """, (user_id, cuisines_str, tastes_str, diet, price_range_str, location, emotion))
    conn.commit()
    conn.close()

def calculate_temperature_bias(q1, q2):
    """
    Calculate user's temperature preference bias.
    
    Args:
        q1 (str): Response to cold food preference
        q2 (str): Response to warm food preference
    
    Returns:
        float: Temperature bias value between 0 and 1
    """
    mapping = {
        "Strongly Agree": 5,
        "Agree": 4,
        "Indifferent": 3,
        "Disagree": 2,
        "Strongly Disagree": 1
    }
    cold_bias = mapping.get(q1, 3)
    warm_bias = mapping.get(q2, 3)
    return (cold_bias + warm_bias) / 10

def calculate_tourist_bias(q3):
    """
    Calculate user's tourist/local food preference bias.
    
    Args:
        q3 (str): Response to local food preference
    
    Returns:
        float: Tourist bias value between 0 and 1
    """
    mapping = {
        "Strongly Agree": 1.0,
        "Agree": 0.8,
        "Indifferent": 0.5,
        "Disagree": 0.2,
        "Strongly Disagree": 0.0
    }
    return mapping.get(q3, 0.5)

def get_recent_search(user_id, db_path=DB_PATH):
    """
    Retrieve user's most recent search preferences.
    
    Args:
        user_id (int): User's ID
        db_path (str): Database path
    
    Returns:
        dict: Recent search preferences
    
    Raises:
        ValueError: If no recent searches found
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT cuisines, tastes, diet, price_range FROM Searches 
        WHERE user_id=? ORDER BY timestamp DESC LIMIT 1
    """, (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "cuisines": json.loads(row[0]),
            "tastes": json.loads(row[1]),
            "diet": row[2],
            "price_range": json.loads(row[3])
        }
    else:
        raise ValueError(f"No recent searches found for user_id {user_id}")

def predict_meal_recommendations(feature_vector):
    """Predict user preferences using the trained Random Forest model."""
    try:
        if rf_model is None:
            raise ValueError("Model not loaded. Please ensure the model file exists and is loaded correctly.")
        prediction = rf_model.predict([feature_vector])[0]
        return prediction
    except Exception as e:
        raise RuntimeError(f"Error during prediction: {str(e)}")

def prepare_feature_vector(user_info, recent_search):
    """
    Prepares a feature vector for predictions.
    Ensures that the structure matches the training model input.

    Args:
        user_info (dict): User data from the database
        recent_search (dict): The user's most recent search

    Returns:
        list: A feature vector for the ML model
    """
    # Extract basic user features from user_info
    temperature_bias = user_info.get("temperature_bias", 0.5)
    tourist_bias = user_info.get("tourist_bias", 0.5)
    
    # Convert emotion to numerical value
    emotion_map = {"happy": 2, "neutral": 1, "sad": 0}
    emotion = emotion_map.get(user_info.get("emotion", "neutral"), 1)
    
    # Cuisine vector – must match training structure
    all_cuisines = ["Italian", "American", "Mexican", "Japanese", "Asian", "European", "Mediterranean", "Thai"]
    cuisines = recent_search.get("cuisines", [])
    # Standardize capitalization
    cuisines = [c.title() for c in cuisines]
    cuisine_vector = [1 if cuisine in cuisines else 0 for cuisine in all_cuisines]
    
    # Taste vector
    all_tastes = ["Sweet", "Salty", "Sour", "Bitter", "Umami", "Spicy"]
    tastes = recent_search.get("tastes", [])
    # Diet vector
    tastes = [t.title() for t in tastes]
    taste_vector = [1 if taste in tastes else 0 for taste in all_tastes]
    
    # Diet vector
    diet = recent_search.get("diet", "None")
    diet_vector = [
        1 if diet == "Vegan" else 0,
        1 if diet == "Vegetarian" else 0,
        1 if diet == "None" else 0
    ]
    
    # Price range
    price_range = recent_search.get("price_range", [1, 4])
    if isinstance(price_range, list) and len(price_range) == 2:
        price_min, price_max = price_range
    else:
        price_min, price_max = 1, 4
    
    # Final setup of feature-vector
    feature_vector = (
        [temperature_bias, tourist_bias, emotion] +
        cuisine_vector +
        taste_vector +
        diet_vector +
        [price_min, price_max]
    )
    
    print(f"Feature vector for prediction: {feature_vector}")
    return feature_vector



def save_model(model, path=MODEL_PATH):
    """
    Save trained model to disk.
    
    Args:
        model: Trained RandomForestClassifier model
        path (str): Path to save the model
    """
    with open(path, "wb") as f:
        pickle.dump(model, f)
    print(f"Model saved at {path}.")

def retrain_model():
    """
    Retrain the Random Forest model using accumulated user data.
    
    This function:
    1. Extracts training data from database
    2. Trains a new RandomForestClassifier
    3. Saves the updated model
    """
    print("Retraining the Random Forest model with real user data...")
    X, y = prepare_training_data(DB_PATH)
    
    if len(X) == 0 or len(y) == 0:
        print("Insufficient data for model training. Retraining aborted.")
        return
    
    # Create and train new model
    global rf_model
    rf_model = RandomForestClassifier(random_state=42)
    rf_model.fit(X, y)
    
    # Save the updated model
    save_model(rf_model)
    print("Model retrained and saved successfully.")

# Optional: Automatic model retraining
if __name__ == "__main__":
    retrain_model()