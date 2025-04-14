# Import relevant libraries/modules
import streamlit as st  # For building the user interface
import folium  # For creating maps
from streamlit_folium import folium_static  # To embed folium maps in Streamlit
from folium.plugins import HeatMap, MarkerCluster  # Additional map features
import requests  # For making HTTP requests to APIs
import ipinfo  # To get geolocation details based on IP address
from googlemaps import Client  # To interact with the Google Maps API
from datetime import datetime  # To work with date and time
from data_ml import (  # Custom module for handling machine learning and database interactions
    init_db,  # Initializes the database
    get_or_create_user,  # Fetches user info or creates a new user
    record_interaction,  # Records user interactions
    save_user_setup,  # Saves user setup data
    save_user_preferences,  # Saves user preferences
    save_search_query,  # Records the user's search queries
    predict_meal_recommendations,  # Predicts meal recommendations
    prepare_feature_vector,  # Prepares data for machine learning model input
    get_user_data,  # Retrieves user-specific data
    get_recent_search,  # Fetches the user's most recent search
    retrain_model # update ML to new DB
)

# Google Maps API Configuration
GOOGLE_MAPS_KEY = "AIzaSyCyi7CZYLTrkq6_YwDOmlG6sAJioF5mh0g"  # Replace with your API key
gmaps = Client(key=GOOGLE_MAPS_KEY)  # Google Maps client for API interactions

# Geolocation Configuration
ip_handler = ipinfo.getHandler("967427397769cc")  # Handler for IPinfo API
ip_address = requests.get("https://api.ipify.org").text  # Fetch the user's public IP address
details = ip_handler.getDetails(ip_address)  # Get location details based on the IP address
city = details.city  # Extract city name
country = details.country  # Extract country name
latitude = round(float(details.latitude), 2)  # Get and round latitude
longitude = round(float(details.longitude), 2)  # Get and round longitude

# Initialize the database at the start to store and retrieve data
init_db()

def show_contribution_matrix():
    """Display the contribution matrix in a collapsible section."""
    with st.expander("Project 7.2 - Contribution Matrix\nFundamentals and Methods of Computer Science for Business Studies - University of St. Gallen"):
        # Create the matrix headers
        st.markdown("""
        | Task | Arthur | Bruno | Christian | Edgar | Valentin |
        |------|--------|--------|-----------|-------|-----------|
        | Project Management | - | - | 🟩 | - | 🟨 |
        | UI Interface | - | - | - | - | 🟧 |
        | Api implementation | - | 🟨 | - | 🟨 | - |
        | Data Visualization | - | - | - | - | 🟩 |
        | Machine Learning | - | - | - | - | 🟩 |
        | 4- Min Video | 🟩 | - | - | - | - |
        | Contribution Matrix | - | - | 🟩 | - | - |
        | Comments | 🟨 | 🟨 | 🟨 | 🟨 | 🟨 |
        | Testing | 🟨 | 🟨 | - | 🟨 | 🟨 |
        | Additional help | 🟨 | 🟨 | 🟨 | 🟨 | 🟨 |
        """)
        
        # Add legend
        st.markdown("""
        *Legend:*
        - 🟩 Main Contributer
        - 🟨 Contributor
        - 🟧 Supporting Role
        - - No Influence
        """)

def temp_geolocated(latitude, longitude):
    """Fetches the current temperature at a specific latitude and longitude using OpenWeatherMap API."""
    owm_api_key = "38174ab1aafd193a46134ac2dd54de7a"  # Replace with your OpenWeatherMap API key
    url = (
        f"https://api.openweathermap.org/data/3.0/onecall?"
        f"lat={latitude}&lon={longitude}&exclude=minutely,hourly,alerts,daily"
        f"&appid={owm_api_key}&units=metric"
    )
    owm_local = requests.get(url)  # Send the request
    owm_local_cache = owm_local.json()  # Parse JSON response
    current_temp = owm_local_cache.get('current', {}).get("temp", "T not found")  # Extract temperature
    return current_temp

def temp_target(location):
    """Fetches temperature for a specific location name using Google Maps Geocoding and OpenWeatherMap."""
    geocode_result = gmaps.geocode(location)  # Get geocoding data for the location
    if geocode_result:
        lat = geocode_result[0]['geometry']['location']['lat']  # Extract latitude
        lng = geocode_result[0]['geometry']['location']['lng']  # Extract longitude
        owm_api_key = "38174ab1aafd193a46134ac2dd54de7a"  # OpenWeatherMap API key
        url = (
            f"https://api.openweathermap.org/data/3.0/onecall?"
            f"lat={lat}&lon={lng}&exclude=minutely,hourly,alerts,daily"
            f"&appid={owm_api_key}&units=metric"
        )
        owm_local = requests.get(url)  # Fetch weather data
        owm_local_cache = owm_local.json()  # Parse JSON response
        current_temp = owm_local_cache.get('current', {}).get("temp", "T not found")  # Extract temperature
        return current_temp
    return "Location not found"  # Return fallback message if location is invalid

def setup():
    """Initial setup for the application, including user data and UI customization."""
    # Initialize session state variables
    if "index" not in st.session_state:  # Tracks the image carousel index for new user setup
        st.session_state.index = 0
    if "username" not in st.session_state:  # Stores the current user's username
        st.session_state.username = ""
    if "feeling" not in st.session_state:  # Captures the user's emotional state
        st.session_state.feeling = None
    if "user_id" not in st.session_state:  # Unique ID for the user
        st.session_state.user_id = None
    if "user_exists" not in st.session_state:  # Tracks if the user is new or existing
        st.session_state.user_exists = False
    if "setup_complete" not in st.session_state:  # Indicates if the setup process is finished
        st.session_state.setup_complete = False

    # Apply a custom background image to the app
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] {
            background: url("https://i.imgur.com/JEKYsJc.png") no-repeat center center fixed;
            background-size: cover;
        }
        h1 {
            white-space: nowrap;
        }
        </style>
        """,
        unsafe_allow_html=True  # Allow custom HTML for styling
    )

    st.title("My Perfect Meal")  # Set the title of the app
    st.write("")  # Adds spacing

    # Username input for first-time setup
    if st.session_state.username == "":
        username_input = st.text_input("Please enter your username:")  # Input box for username
        if username_input:  # If a username is provided
            st.session_state.username = username_input  # Store username in session state
            user_info, is_new_user = get_or_create_user(st.session_state.username)  # Fetch or create user data
            st.session_state.user_id = user_info['user_id']  # Save user ID
            st.session_state.user_exists = not is_new_user  # Determine if the user is new

    # Ask the user how they are feeling
    elif st.session_state.feeling is None:
        st.write(f"Hi {st.session_state.username}, how are you feeling today?")  # Prompt for mood
        col1, col2, col3 = st.columns(3)  # Create columns for mood buttons
        with col1:
            if st.button("😊", key="happy"):  # Happy button
                st.session_state.feeling = "happy"
                save_user_setup(st.session_state.user_id, emotion="happy")  # Save the mood
                if st.session_state.user_exists:
                    st.session_state.setup_complete = True  # Mark setup as complete
        
        with col2:
            if st.button("😐", key="neutral"):  # Neutral button
                st.session_state.feeling = "neutral"
                save_user_setup(st.session_state.user_id, emotion="neutral")  # Save the mood
                if st.session_state.user_exists:
                    st.session_state.setup_complete = True  # Mark setup as complete
        with col3:
            if st.button("😞", key="sad"):  # Sad button
                st.session_state.feeling = "sad"
                save_user_setup(st.session_state.user_id, emotion="sad")  # Save the mood
                if st.session_state.user_exists:
                    st.session_state.setup_complete = True  # Mark setup as complete

    # New user setup: if the user is new, display cuisine preference setup
    elif not st.session_state.user_exists:
        images = [  # List of images representing different cuisines
            "https://i.imgur.com/K8Q2pUV.png",  # Italian
            "https://i.imgur.com/8NrQSxl.png",  # American
            "https://i.imgur.com/hMK6cS4.png",  # Mexican
            "https://i.imgur.com/kotTII8.png",  # Japanese
            "https://i.imgur.com/GHFWxTW.png",  # Asian
            "https://i.imgur.com/bbgSU2U.png",  # European
            "https://i.imgur.com/qUfcoOT.png",  # Mediterranean
            "https://i.imgur.com/wuEUqTv.png"   # Thai
        ]

        current_index = st.session_state.index  # Get the current index for image display
        if current_index < len(images):  # Display images until the last one
            st.image(images[current_index], width=300)  # Show the current image
            b_left, b_right = st.columns([1, 1])  # Create buttons for feedback
            with b_left:
                left_clicked = st.button("💙", key=f"blue-heart-{current_index}")  # Like button
            with b_right:
                right_clicked = st.button("❌", key=f"red-cross-{current_index}")  # Dislike button

            if left_clicked or right_clicked:  # Handle button click feedback
                feedback = 1 if left_clicked else 0  # Assign feedback value
                record_interaction(st.session_state.user_id, current_index, feedback)  # Save interaction
                st.session_state.index += 1  # Increment index to show the next image
        else:
            # Once all images are displayed, ask for detailed preferences
            st.subheader("Done! Please proceed.")  # Notify user setup is complete
            responses = ["Strongly Agree", "Agree", "Indifferent", "Disagree", "Strongly Disagree"]  # Scale options
            q1 = st.select_slider("I prefer cold food in the summer", options=responses, key="q1")  # Preference 1
            q2 = st.select_slider("I prefer warm food in the winter", options=responses, key="q2")  # Preference 2
            q3 = st.select_slider("I love to try local food when travelling abroad", options=responses, key="q3")  # Preference 3

            if st.button("Save and proceed to finder"):  # Save preferences and move to finder
                save_user_preferences(st.session_state.user_id, q1, q2, q3)  # Save to database
                st.session_state.setup_complete = True  # Mark setup as complete

def get_restaurant_results(cuisines, price_range, location):
    """Fetches restaurant recommendations based on cuisines, price range, and location."""
    try:
        coords = get_location_coordinates(location)  # Get location coordinates from the name
        if not coords:  # If location is invalid
            return []

        lat, lon = coords  # Unpack coordinates
        # Use Google Maps API to find nearby restaurants
        places_result = gmaps.places_nearby(
            location=(lat, lon),
            radius=2000,  # Search radius in meters
            type='restaurant',  # Look for restaurants
            keyword=' '.join(cuisines) if cuisines else 'restaurant'  # Include cuisine keywords
        )

        results = []  # Initialize the results list
        for place in places_result.get('results', []):  # Iterate through API results
            place_details = gmaps.place(  # Fetch detailed info for each place
                place['place_id'],
                fields=['name', 'rating', 'formatted_address', 'formatted_phone_number', 'price_level', 'reviews']
            )['result']

            price_level = place_details.get('price_level', 0)  # Get price level
            price = '$' * (price_level + 1) if price_level is not None else 'N/A'  # Format price
            reviews = place_details.get('reviews', [])  # Get reviews
            latest_reviews = reviews[:3] if reviews else []  # Limit to 3 most recent reviews

            # Create a dictionary for the restaurant details
            restaurant = {
                'name': place['name'],
                'cuisine': ', '.join(cuisines) if cuisines else 'Various',
                'rating': place_details.get('rating', 'N/A'),
                'price': price,
                'address': place_details.get('formatted_address', 'N/A'),
                'phone': place_details.get('formatted_phone_number', 'N/A'),
                'coordinates': {
                    'latitude': place['geometry']['location']['lat'],
                    'longitude': place['geometry']['location']['lng']
                },
                'reviews': [{
                    'author': review.get('author_name', 'Anonymous'),
                    'rating': review.get('rating', 'N/A'),
                    'text': review.get('text', 'No comment')
                } for review in latest_reviews]  # Store reviews as a list of dictionaries
            }
            results.append(restaurant)  # Add restaurant to results

        return results  # Return the list of restaurants
    except Exception as e:
        st.error(f"Error occurred while fetching results: {str(e)}")  # Handle API errors
        return []

def get_location_coordinates(location):
    """Returns the latitude and longitude for a given location."""
    try:
        geocode_result = gmaps.geocode(location)  # Geocode the location name
        if geocode_result:
            lat = geocode_result[0]['geometry']['location']['lat']  # Extract latitude
            lng = geocode_result[0]['geometry']['location']['lng']  # Extract longitude
            return float(lat), float(lng)  # Return coordinates as floats
        return None  # Return None if geocoding fails
    except Exception as e:
        st.error(f"Error getting location: {str(e)}")  # Handle geocoding errors
        return None

def display_results_on_map(results):
    """Displays the restaurant results on an interactive map."""
    if not results:
        st.warning("No results found. Please try a different search.")  # Show warning if no results
        return

    try:
        # Initialize the map centered on the first result
        lat = results[0]["coordinates"]["latitude"]
        lon = results[0]["coordinates"]["longitude"]

        m = folium.Map(
            location=[lat, lon],
            zoom_start=13,  # Set zoom level
            tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',  # Use Google Maps tiles
            attr='Google Maps'  # Set attribution
        )

        # Create heatmap data from restaurant coordinates
        heat_data = [[business["coordinates"]["latitude"], 
                     business["coordinates"]["longitude"]]
                    for business in results if "coordinates" in business]
        HeatMap(heat_data).add_to(m)  # Add heatmap to map

        # Add markers for each restaurant
        marker_cluster = MarkerCluster().add_to(m)
        for business in results:
            reviews_html = ""  # Initialize reviews HTML content
            if business.get('reviews'):
                reviews_html = "<br><b>Recent Reviews:</b><br>"  # Add a reviews header
                for review in business['reviews']:  # Format each review
                    reviews_html += f"""
                    <br>⭐ {review['rating']}/5 - {review['author']}<br>
                    "{review['text'][:100]}..."<br>
                    """

            # Create a popup with restaurant details
            popup_content = f"""
            <b>{business['name']}</b><br>
            <b>Cuisine:</b> {business.get('cuisine', 'N/A')}<br>
            <b>Rating:</b> {'⭐' * round(float(business['rating'])) if isinstance(business['rating'], (int, float)) else 'N/A'}<br>
            <b>Price:</b> {business.get('price', 'N/A')}<br>
            <b>Address:</b> {business.get('address', 'N/A')}<br>
            <b>Phone:</b> {business.get('phone', 'N/A')}<br>
            {reviews_html}
            """

            # Add marker to the map
            folium.Marker(
                [business["coordinates"]["latitude"], 
                 business["coordinates"]["longitude"]],
                popup=folium.Popup(popup_content, max_width=300),
                tooltip=f"{business['name']} - {'⭐' * round(float(business['rating'])) if isinstance(business['rating'], (int, float)) else 'N/A'}"
            ).add_to(marker_cluster)

        folium_static(m)  # Render the map in Streamlit
    except KeyError as e:
        st.error("Missing coordinates in results.")  # Handle missing data
    except Exception as e:
        st.error(f"Error displaying map: {str(e)}")  # Handle other map-related errors

def surprise_me_recommendation(user_id, location):
    """
    Generate recommendations using the trained Random Forest model and user-specific data.
    Args:
        user_id (int): User ID for which the recommendation is to be generated.
        location (str): Location entered by the user.
    Returns:
        list: A list of recommended restaurants or an empty list if no results.
    """
    try:
        # Fetch user and recent search data
        user_info = get_user_data(user_id)
        recent_search = get_recent_search(user_id)

        # Ensure user_info and recent_search are retrieved correctly
        if not user_info or not recent_search:
            raise ValueError("Missing user data or recent search data.")

        # Prepare the feature vector
        feature_vector = prepare_feature_vector(user_info, recent_search)
        print(f"Feature vector for prediction: {feature_vector}")

        # Predict user preference
        prediction = rf_model.predict([feature_vector])[0]

        # Determine query keywords based on prediction
        keywords = recent_search['cuisines'] if prediction == 1 else ["restaurant"]

        # Get location coordinates
        coords = get_location_coordinates(location)
        if not coords:
            raise ValueError("Unable to determine coordinates for the specified location.")

        # Query Google Places API for restaurants
        lat, lon = coords
        places_result = gmaps.places_nearby(
            location=(lat, lon),
            radius=2000,  # 2km radius
            type='restaurant',
            keyword=' '.join(keywords)
        )

        # Parse results
        results = []
        for place in places_result.get('results', []):
            place_details = gmaps.place(
                place['place_id'], 
                fields=['name', 'rating', 'formatted_address', 'formatted_phone_number', 'price_level', 'reviews']
            )['result']
            price_level = place_details.get('price_level', 0)
            price = '$' * (price_level + 1) if price_level is not None else 'N/A'
            reviews = place_details.get('reviews', [])
            latest_reviews = reviews[:3] if reviews else []

            results.append({
                'name': place_details.get('name', 'N/A'),
                'rating': place_details.get('rating', 'N/A'),
                'price': price,
                'address': place_details.get('formatted_address', 'N/A'),
                'phone': place_details.get('formatted_phone_number', 'N/A'),
                'coordinates': {
                    'latitude': place_details['geometry']['location']['lat'],
                    'longitude': place_details['geometry']['location']['lng']
                },
                'reviews': [
                    {
                        'author': review.get('author_name', 'Anonymous'),
                        'rating': review.get('rating', 'N/A'),
                        'text': review.get('text', 'No comment')
                    } for review in latest_reviews
                ]
            })

        return results
    except Exception as e:
        raise RuntimeError(f"An error occurred during recommendation: {str(e)}")


def main():
    """Main function to handle the app logic."""
    st.title("Find Your Perfect Meal")  # Title of the application
    show_contribution_matrix()

    # Define a helper function to get user preferences
    def get_user_preferences():
        cuisines = st.multiselect(  # Allow users to select multiple cuisines
            "Select cuisines:", 
            ["Italian", "Chinese", "Mexican", "Japanese", "Indian", "American", "Thai", "French", "Greek", "Spanish"]
        )
        tastes = st.multiselect(  # Allow users to select multiple taste preferences
            "Select taste preferences:", 
            ["Sweet", "Salty", "Sour", "Bitter", "Umami", "Spicy"]
        )
        diet = st.selectbox(  # Allow users to select dietary preferences
            "Select dietary preference:", 
            ["None", "Vegetarian", "Vegan"]
        )
        price_range = st.slider(  # Allow users to select a price range
            "Select price range:", 
            1, 4, (1, 4)
        )
        return cuisines, tastes, diet, price_range  # Return all the selected preferences

    # Capture user inputs
    cuisines, tastes, diet, price_range = get_user_preferences()
    location = st.text_input("Enter your location:")  # Input for user location

    if st.button("Surprise Me, now with mealLearning™"):  # "Surprise Me" button
        user_id = st.session_state.get("user_id")  # Get the user ID from the session state
        if user_id and location:  # Ensure user ID and location are provided
            try:
                # Generate surprise recommendations
                results = surprise_me_recommendation(user_id, location)
                if results:
                    display_results_on_map(results)  # Display recommendations on the map
                    st.subheader("Surprise Recommendations:")  # Add a header for results
                    for business in results:  # Display each recommended business
                        st.write(f"**{business['name']}**")
                        st.write(f"Rating: {'⭐' * round(float(business['rating'])) if isinstance(business['rating'], (int, float)) else 'N/A'}")
                        st.write(f"Price: {business.get('price', 'N/A')}")
                        st.write(f"Address: {business.get('address', 'N/A')}")
                        st.write(f"Phone: {business.get('phone', 'N/A')}")
                        if business.get('reviews'):  # Show reviews if available
                            st.write("Recent Reviews:")
                            for review in business['reviews']:
                                st.write(f"- ⭐{review['rating']}/5 - {review['author']}: {review['text'][:100]}...")
                        st.write("---")  # Separator between results
                else:
                    st.warning("No recommendations found. Try a different location.")  # No results message
            except Exception as e:
                st.error(str(e))  # Display error message
        else:
            st.warning("Please ensure you are logged in and have entered a location.")  # Missing input message


    if st.button("Find Restaurants"):  # "Find Restaurants" button
        if location:  # Ensure location is provided
            user_id = st.session_state.get("user_id")  # Get user ID from session state
            emotion = st.session_state.get("feeling", "neutral")  # Get user's mood from session state

            if user_id:
                # Save the search query to the database
                save_search_query(user_id, cuisines, tastes, diet, price_range, location, emotion)
                retrain_model() 
            # Get restaurant recommendations
            results = get_restaurant_results(cuisines, price_range, location)
            if results:
                display_results_on_map(results)  # Display results on the map
                st.subheader("Restaurant Recommendations:")  # Add a header for results
                for business in results:  # Display each recommended restaurant
                    st.write(f"{business['name']}")
                    st.write(f"Rating: {'⭐' * round(float(business['rating'])) if isinstance(business['rating'], (int, float)) else 'N/A'}")
                    st.write(f"Price: {business.get('price', 'N/A')}")
                    st.write(f"Address: {business.get('address', 'N/A')}")
                    st.write(f"Phone: {business.get('phone', 'N/A')}")
                    if business.get('reviews'):  # Show reviews if available
                        st.write("Recent Reviews:")
                        for review in business['reviews']:
                            st.write(f"- ⭐{review['rating']}/5 - {review['author']}: {review['text'][:100]}...")
                    st.write("---")  # Separator between results
            else:
                st.warning("No restaurants found for your search criteria.")  # No results message
        else:
            st.warning("Please enter a location before searching for restaurants.")  # Missing location message

# Entry point of the script
if __name__ == "__main__":
    if "setup_complete" not in st.session_state:  # Initialize session state if not already set
        st.session_state["setup_complete"] = False

    if not st.session_state["setup_complete"]:  # If setup is not complete, run the setup
        setup()
    else:
        main()  # Otherwise, run the main function


