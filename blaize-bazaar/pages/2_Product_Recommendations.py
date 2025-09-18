import streamlit as st
import psycopg
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv
import boto3
import json
import base64
from botocore.exceptions import ClientError
from botocore.config import Config
from datetime import datetime
import time
import hashlib

# Load environment variables and set up configurations
load_dotenv()

# Initialize Bedrock client
config = Config(
    region_name='us-west-2',
    retries={
        'max_attempts': 3,
        'mode': 'standard'
    }
)
   
bedrock = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-west-2',
    config=config
)

# Constants and configurations
LOGO_URL = "static/Blaize.png"
CLAUDE_MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"

# Database functions
def get_db_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT", "5432")
    )


def init_user_tables():
    """Initialize user-related database tables if they don't exist"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Create users table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bedrock_integration.users (
                    user_id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Create user preferences table with unique constraint on user_id
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bedrock_integration.user_preferences (
                    preference_id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES bedrock_integration.users(user_id),
                    category_preferences TEXT[],
                    price_range_min NUMERIC,
                    price_range_max NUMERIC,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id)
                );
            """)
            
            # Create user search history table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bedrock_integration.user_search_history (
                    history_id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES bedrock_integration.users(user_id),
                    search_query TEXT,
                    search_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()

def hash_password(password):
    """Create a secure hash of the password"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password):
    """Create a new user account"""
    password_hash = hash_password(password)
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    INSERT INTO bedrock_integration.users (username, password_hash)
                    VALUES (%s, %s)
                    RETURNING user_id
                """, (username, password_hash))
                user_id = cur.fetchone()[0]
                conn.commit()
                return user_id
            except psycopg.Error as e:
                st.error(f"Error creating user: {e}")
                return None

def authenticate_user(username, password):
    """Authenticate user credentials"""
    password_hash = hash_password(password)
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT user_id, username
                FROM bedrock_integration.users
                WHERE username = %s AND password_hash = %s
            """, (username, password_hash))
            result = cur.fetchone()
            return result if result else None

def save_user_preferences(user_id, categories, min_price, max_price):
    """Save or update user preferences"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            try:
                # First, check if preferences exist for this user
                cur.execute("""
                    SELECT 1 FROM bedrock_integration.user_preferences WHERE user_id = %s
                """, (user_id,))
                
                if cur.fetchone() is None:
                    # Insert new preferences
                    cur.execute("""
                        INSERT INTO bedrock_integration.user_preferences 
                        (user_id, category_preferences, price_range_min, price_range_max)
                        VALUES (%s, %s, %s, %s)
                    """, (user_id, categories, min_price, max_price))
                else:
                    # Update existing preferences
                    cur.execute("""
                        UPDATE bedrock_integration.user_preferences
                        SET category_preferences = %s,
                            price_range_min = %s,
                            price_range_max = %s,
                            last_updated = CURRENT_TIMESTAMP
                        WHERE user_id = %s
                    """, (categories, min_price, max_price, user_id))
                
                conn.commit()
                return True
            except psycopg.Error as e:
                st.error(f"Error saving preferences: {e}")
                conn.rollback()
                return False

def get_user_preferences(user_id):
    """Retrieve user preferences"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT category_preferences, price_range_min, price_range_max
                FROM bedrock_integration.user_preferences
                WHERE user_id = %s
            """, (user_id,))
            return cur.fetchone()

def get_personalized_initial_recommendations(user_id, limit=5):
    """Get initial recommendations based on user preferences"""
    preferences = get_user_preferences(user_id)
    if not preferences:
        return None
    
    categories, min_price, max_price = preferences
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT "productId", product_description, category_name, stars, price, 
                       boughtinlastmonth, imgURL, producturl
                FROM bedrock_integration.product_catalog
                WHERE category_name = ANY(%s)
                AND price BETWEEN %s AND %s
                ORDER BY stars DESC, boughtinlastmonth DESC
                LIMIT %s
            """, (categories, min_price, max_price, limit))
            results = cur.fetchall()
            
    return pd.DataFrame(results, columns=[
        'productId', 'product_description', 'category_name', 'stars', 
        'price', 'boughtinlastmonth', 'imgURL', 'producturl'
    ])

def log_search_history(user_id, search_query):
    """Log user search queries"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO bedrock_integration.user_search_history 
                (user_id, search_query)
                VALUES (%s, %s)
            """, (user_id, search_query))
            conn.commit()

def show_login_signup():
    """Display login/signup interface"""
    st.sidebar.subheader("Login / Sign Up")
    action = st.sidebar.radio("Choose action:", ("Login", "Sign Up"))
    
    if action == "Login":
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Login"):
            user = authenticate_user(username, password)
            if user:
                st.session_state.user_id = user[0]
                st.session_state.username = user[1]
                st.success(f"Welcome back, {username}!")
                st.rerun()
            else:
                st.error("Invalid username or password")
    
    else:  # Sign Up
        username = st.sidebar.text_input("Choose username")
        password = st.sidebar.text_input("Choose password", type="password")
        confirm_password = st.sidebar.text_input("Confirm password", type="password")
        if st.sidebar.button("Sign Up"):
            if password != confirm_password:
                st.error("Passwords don't match!")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters long")
            else:
                user_id = create_user(username, password)
                if user_id:
                    st.success("Account created successfully! Please login.")
                    st.session_state.show_preferences = True

def show_preference_settings():
    """Display simplified preference settings interface"""
    st.subheader("Set Your Shopping Preferences")
    
    # Get available categories from the product catalog
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT category_name FROM bedrock_integration.product_catalog")
            available_categories = [cat[0] for cat in cur.fetchall()]
    
    # Get existing preferences if any
    current_preferences = get_user_preferences(st.session_state.user_id)
    
    # Set defaults based on current preferences or defaults
    default_categories = []
    default_min_price = 0.0
    default_max_price = 1000.0
    
    if current_preferences:
        default_categories = current_preferences[0] or []
        default_min_price = float(current_preferences[1] or 0.0)
        default_max_price = float(current_preferences[2] or 1000.0)
    
    # Preference inputs
    selected_categories = st.multiselect(
        "Select your preferred categories:",
        options=available_categories,
        default=default_categories
    )
    
    col1, col2 = st.columns(2)
    with col1:
        min_price = st.number_input("Minimum price ($)", value=default_min_price, step=10.0)
    with col2:
        max_price = st.number_input("Maximum price ($)", value=default_max_price, step=10.0)
    
    if st.button("Save Preferences"):
        if save_user_preferences(
            st.session_state.user_id,
            selected_categories,
            min_price,
            max_price
        ):
            st.success("Preferences saved successfully!")
            st.session_state.show_preferences = False
            time.sleep(1)  # Give user time to see the success message
            st.rerun()
        else:
            st.error("Failed to save preferences. Please try again.")


def keyword_search(query, top_k=5):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            try:
                start_time = time.time()
                cur.execute("""
                    SELECT "productId", product_description, category_name, stars, price, boughtinlastmonth,
                           imgURL, producturl
                    FROM bedrock_integration.product_catalog
                    WHERE to_tsvector('english', product_description || ' ' || category_name) @@ plainto_tsquery('english', %s)
                    ORDER BY ts_rank(to_tsvector('english', product_description || ' ' || category_name), plainto_tsquery('english', %s)) DESC
                    LIMIT %s
                """, (query, query, top_k))
                results = cur.fetchall()
                end_time = time.time()
                query_time = (end_time - start_time) * 1000  # Convert to milliseconds
            except psycopg.Error as e:
                st.error(f"Error: {e}. Please check your database configuration.")
                st.stop()

    return pd.DataFrame(results, columns=['productId', 'product_description', 'category_name', 'stars', 'price', 'boughtinlastmonth', 'imgURL', 'producturl']), query_time

def similarity_search(query_embedding, top_k=5):
    query_embedding_list = query_embedding.tolist()

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            try:
                start_time = time.time()
                cur.execute("""
                    SELECT "productId", product_description, category_name, stars, price, boughtinlastmonth,
                           imgURL, producturl,
                           1 - (embedding <=> %s::vector) AS similarity
                    FROM bedrock_integration.product_catalog
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """, (query_embedding_list, query_embedding_list, top_k))
                results = cur.fetchall()
                end_time = time.time()
                query_time = (end_time - start_time) * 1000  # Convert to milliseconds
            except psycopg.errors.InvalidTextRepresentation as e:
                st.error(f"Error: {e}. The embedding data type might not match. Please check your database schema.")
                st.stop()

    return pd.DataFrame(results, columns=['productId', 'product_description', 'category_name', 'stars', 'price', 'boughtinlastmonth', 'imgURL', 'producturl', 'similarity']), query_time

# Bedrock functions
def generate_embedding(text):
    body = json.dumps({"inputText": text})
    modelId = 'amazon.titan-embed-text-v2:0'
    accept = 'application/json'
    contentType = 'application/json'

    response = bedrock.invoke_model(body=body, modelId=modelId, accept=accept, contentType=contentType)
    response_body = json.loads(response.get('body').read())
    embedding = response_body.get('embedding')
    return np.array(embedding, dtype=np.float32)

def get_claude_response(prompt, max_tokens=4096):
    try:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        })

        response = bedrock.invoke_model(
            body=body,
            modelId=CLAUDE_MODEL_ID,
            accept="application/json",
            contentType="application/json"
        )

        response_body = json.loads(response.get('body').read())
        return response_body['content'][0]['text']
    except ClientError as e:
        st.error(f"An error occurred: {e}")
        return None

def get_personalized_recommendations(user_preferences, top_k=3):
    # Generate embedding for user preferences
    preference_embedding = generate_embedding(user_preferences)
    
    # Perform similarity search in product catalog
    results, query_time = similarity_search(preference_embedding, top_k)
    
    # Prepare the prompt for Claude
    recommendations_prompt = f"""
    Based on the user's preferences: "{user_preferences}"
    And considering these top products from our catalog:
    {results.to_dict('records')}

    Provide {top_k} personalized product recommendations. For each recommendation:
    1. Explain why it's a good fit for the user
    2. Highlight key features or benefits
    3. Suggest how it compares to similar products

    Format your response in markdown for easy reading.
    """
    
    # Get recommendations from Claude
    claude_recommendations = get_claude_response(recommendations_prompt)
    
    return claude_recommendations, results, query_time

def display_products(results, query_time):
    st.subheader(f"Search Results (Query Time: {query_time:.2f} ms)")
    for _, product in results.iterrows():
        col1, col2 = st.columns([1, 3])
        with col1:
            st.image(product['imgURL'], width=100)
        with col2:
            st.write(f"**[{product['product_description']}]({product['producturl']})**")
            st.write(f"Category: {product['category_name']}")
            st.write(f"Price: ${product['price']:.2f}")
            st.write(f"Rating: {product['stars']:.1f}")
            if 'similarity' in product:
                st.write(f"Similarity: {product['similarity']:.4f}")
        st.write("---")

def show_product_recommendations():
    st.subheader("Product Search Comparison")
    
    # Example queries dropdown
    example_queries = [
        "Select an example query",
        "Affordable portable computers",
        "I need something to keep my drinks cold on a picnic",
        "Light jacket for spring evenings",
        "Duffel bags for the gym",
        "Eco-friendly cleaning products",
        "Gift for a tech-savvy teenager",
        "Wireless blutooth headfones",
        "Outdoor cooking equipment",
        "Vacation-ready camera",
        "Stylish but professional attire for a creative office",
        "Cozy home decor"
    ]
    selected_query = st.selectbox("Choose an example query or enter your own:", example_queries)
    
    search_query = st.text_input("Enter a product description:", value=selected_query if selected_query != example_queries[0] else "")
    if st.button("Search"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Keyword-based Search")
            with st.spinner("Performing keyword search..."):
                keyword_results, keyword_query_time = keyword_search(search_query)
            display_products(keyword_results, keyword_query_time)
        
        with col2:
            st.subheader("Semantic Search")
            with st.spinner("Generating embedding..."):
                query_embedding = generate_embedding(search_query)
            with st.spinner("Performing semantic search..."):
                semantic_results, semantic_query_time = similarity_search(query_embedding)
            display_products(semantic_results, semantic_query_time)
            
        st.subheader("Search Comparison Explanation")
        st.write("""
        Semantic search often outperforms keyword-based search because it understands context and intent:
        - It can handle synonyms and related concepts
        - It works well with natural language queries
        - It can infer meaning from complex or abstract queries
        - It's more resilient to misspellings and variations
            
        In this example, notice how semantic search might return more relevant results,
        especially for queries that don't exactly match product descriptions.
        """)
    else:
        st.warning("Please enter a search query.")
    

    # Personalized AI Recommendations
    st.subheader("Personalized AI Recommendations")
    user_preferences = st.text_area("Tell us about your preferences and what you're looking for:")
    if st.button("Get Personalized Recommendations"):
        with st.spinner("Generating personalized recommendations..."):
            recommendations, top_products, query_time = get_personalized_recommendations(user_preferences)
        if recommendations:
            st.markdown(recommendations)
            st.subheader(f"Top Matching Products (Query Time: {query_time:.2f} ms)")
            display_products(top_products, query_time)
        else:
            st.error("Failed to generate personalized recommendations. Please try again later.")

def main():
    st.set_page_config(page_title="Product Recommendations - Blaize Bazaar", page_icon="🛍️", layout="wide")
    
    # Initialize session state
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'show_preferences' not in st.session_state:
        st.session_state.show_preferences = False
    
    # Initialize database tables
    init_user_tables()
    
    st.subheader('Product Recommendations - Blaize Bazaar', divider='orange')
    st.sidebar.image(LOGO_URL, use_container_width=True)
    st.sidebar.title('**About**')
    st.sidebar.info("At Blaize Bazaar, we use AI-powered semantic search to match you with products you'll love, going beyond simple keyword matching to understand what you're really looking for.")
    
    # Show login/signup if user is not logged in
    if not st.session_state.user_id:
        show_login_signup()
        st.info("Please log in or sign up to see personalized recommendations")
        return
    
    # Show preference settings if needed
    if st.session_state.show_preferences:
        show_preference_settings()
        return
    
    # Show user menu in sidebar
    st.sidebar.title(f"Welcome, {st.session_state.username}!")
    if st.sidebar.button("Update Preferences"):
        st.session_state.show_preferences = True
        st.rerun()
    if st.sidebar.button("Logout"):
        st.session_state.user_id = None
        st.session_state.username = None
        st.rerun()
    
    # Show personalized initial recommendations
    st.subheader("Recommended for You")
    initial_recommendations = get_personalized_initial_recommendations(st.session_state.user_id)
    if initial_recommendations is not None:
        display_products(initial_recommendations, 0)
    
    # Show the regular search interface
    show_product_recommendations()

if __name__ == "__main__":
    main()