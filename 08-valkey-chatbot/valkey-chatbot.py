import streamlit as st
import boto3
import redis
import psycopg
from psycopg.rows import dict_row
import json
import uuid
import os
import time
import hashlib
import hmac
import secrets
from botocore.exceptions import ClientError
from redis.exceptions import RedisError
from datetime import datetime

# AWS configuration
aws_region = os.getenv('AWS_REGION', 'us-west-2')
bedrock = boto3.client('bedrock-runtime', region_name=aws_region)

# ElastiCache configuration
ELASTICACHE_HOST = os.getenv('ELASTICACHE_HOST', '<<your elasticache endpoint>>')
ELASTICACHE_PORT = int(os.getenv('ELASTICACHE_PORT', 6379))

# Aurora PostgreSQL configuration
DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_PORT = int(os.getenv('DB_PORT', '5432'))
EMBEDDING_MODEL_ID = os.getenv('BEDROCK_EMBEDDING_MODEL_ID', 'amazon.titan-embed-text-v2:0')

# Initialize connections
def init_connections():
    # Initialize ElastiCache Valkey connection
    try:
        redis_client = redis.Redis(
            host=ELASTICACHE_HOST,
            port=ELASTICACHE_PORT,
            ssl=True,
            ssl_cert_reqs='none',
            decode_responses=True,
            socket_connect_timeout=5
        )
        redis_client.ping()
        #st.sidebar.success("✅ Connected to ElastiCache")
        return redis_client
    except RedisError as e:
        st.sidebar.error(f"❌ ElastiCache Error: {str(e)}")
        return None

def init_session_state():
    """Initialize all session state variables"""
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if 'cache_hits' not in st.session_state:
        st.session_state.cache_hits = 0
    if 'cache_misses' not in st.session_state:
        st.session_state.cache_misses = 0
    if 'total_cache_time' not in st.session_state:
        st.session_state.total_cache_time = 0.0
    if 'total_db_time' not in st.session_state:
        st.session_state.total_db_time = 0.0
    if 'history_times' not in st.session_state:
        st.session_state.history_times = []
    if 'update_times' not in st.session_state:
        st.session_state.update_times = []
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'preferences' not in st.session_state:
        st.session_state.preferences = {
            "Beach": False,
            "Mountains": False,
            "City": False,
            "Cultural": False,
            "Budget": False
        }
    if 'pref_times' not in st.session_state:
        st.session_state.pref_times = []
    if 'total_response_times' not in st.session_state:
        st.session_state.total_response_times = []

@st.cache_data
def get_embedding(text):
    """Generate embeddings using Amazon Bedrock"""
    try:
        response = bedrock.invoke_model(
            modelId=EMBEDDING_MODEL_ID,
            body=json.dumps({"inputText": text, "dimensions": 1024, "normalize": True})
        )
        response_body = json.loads(response.get('body').read())
        return response_body.get('embedding')
    except Exception as e:
        st.error(f"Error generating embedding: {str(e)}")
        return None

def query_similar_texts(embedding, limit=3):
    """Query similar texts from Aurora PostgreSQL"""
    embedding_literal = "[" + ",".join(str(value) for value in embedding) + "]"
    try:
        with psycopg.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            row_factory=dict_row
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT content, 1 - (embedding <=> %s::vector) AS similarity
                    FROM travel_knowledge_base
                    WHERE 1 - (embedding <=> %s::vector) > 0.7
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """, (embedding_literal, embedding_literal, embedding_literal, limit))
                results = cur.fetchall()
                if not results:
                    return []
                return results
    except psycopg.Error as e:
        st.error(f"Database query error: {str(e)}")
        return []

# Chat History Management with ElastiCache
class ChatHistoryManager:
    def __init__(self, redis_client):
        self.redis_client = redis_client
    
    def get_chat_history(self, session_id, limit=6):
        """Retrieve chat history with metrics tracking"""
        start_time = time.time()
        try:
            if self.redis_client:
                history = self.redis_client.lrange(f"chat_history:{session_id}", 0, limit-1)
                history = [json.loads(msg) for msg in history]
                return history, time.time() - start_time
        except RedisError as e:
            st.error(f"Chat history error: {str(e)}")
        return [], 0
    
    def update_chat_history(self, session_id, user_msg, assistant_msg):
        """Update chat history with new messages"""
        start_time = time.time()
        try:
            if self.redis_client:
                pipeline = self.redis_client.pipeline()
                pipeline.rpush(f"chat_history:{session_id}", 
                             json.dumps({"role": "user", "content": user_msg}))
                pipeline.rpush(f"chat_history:{session_id}", 
                             json.dumps({"role": "assistant", "content": assistant_msg}))
                pipeline.expire(f"chat_history:{session_id}", 3600)  # 1 hour expiry
                pipeline.execute()
                return True, time.time() - start_time
        except RedisError as e:
            st.error(f"Chat history update error: {str(e)}")
        return False, 0

# User Preferences Management
class PreferencesManager:
    def __init__(self, redis_client):
        self.redis_client = redis_client
    
    def get_preferences(self, username):
        """Get user preferences with metrics"""
        start_time = time.time()
        try:
            if self.redis_client:
                prefs = self.redis_client.hget(f"user:{username}", "preferences")
                budget_range = self.redis_client.hget(f"user:{username}", "budget_range")
                
                result = {}
                if prefs:
                    prefs_dict = json.loads(prefs)
                    # Only return active preferences
                    active_prefs = {k: v for k, v in prefs_dict.items() if v}
                    result.update(active_prefs)
                
                if budget_range:
                    result['budget_range'] = json.loads(budget_range)
                
                return result, time.time() - start_time
        except RedisError as e:
            st.error(f"Preferences retrieval error: {str(e)}")
        return {}, 0
    
    def save_preferences(self, username, preferences, budget_range=None):
        """Save user preferences with metrics"""
        start_time = time.time()
        try:
            if self.redis_client:
                pipeline = self.redis_client.pipeline()
                pipeline.hset(f"user:{username}", "preferences", json.dumps(preferences))
                if budget_range is not None:
                    pipeline.hset(f"user:{username}", "budget_range", json.dumps(budget_range))
                pipeline.execute()
                return True, time.time() - start_time
        except RedisError as e:
            st.error(f"Preferences save error: {str(e)}")
        return False, 0

def handle_preferences(st, prefs_manager, username):
    """Handle preference UI and saving without triggering reruns"""
    st.sidebar.title("Travel Preferences")
    
    # Create container for preferences
    with st.sidebar.container():
        # Use form to batch all preference changes
        with st.form(key="preferences_form", clear_on_submit=False):
            # Get current preferences from Redis
            stored_prefs, _ = prefs_manager.get_preferences(username)
            if not stored_prefs:
                stored_prefs = {
                    "Beach": False,
                    "Mountains": False,
                    "City": False,
                    "Cultural": False,
                    "Budget": False
                }
            
            # Create checkboxes using stored preferences
            new_prefs = {}
            for pref in ["Beach", "Mountains", "City", "Cultural", "Budget"]:
                new_prefs[pref] = st.checkbox(
                    f"{pref} {'Destinations' if pref == 'Beach' else 'Adventures' if pref == 'Mountains' else 'Exploration' if pref == 'City' else 'Experiences' if pref == 'Cultural' else 'Friendly'}",
                    value=stored_prefs.get(pref, False),
                )
            
            # Add budget range slider
            st.write("Daily Budget Range (USD)")
            default_min = stored_prefs.get('budget_range', [50, 500])[0]
            default_max = stored_prefs.get('budget_range', [50, 500])[1]
            budget_range = st.slider(
                "Select your daily budget range (USD)",
                min_value=0,
                max_value=1000,
                value=(default_min, default_max),
                step=50,
                help="Slide to set your minimum and maximum daily budget in USD"
            )
            
            # Save button within form
            if st.form_submit_button("Save Preferences"):
                # Save to Redis
                success, _ = prefs_manager.save_preferences(username, new_prefs, budget_range)
                if success:
                    st.success("✅ Preferences saved! Click 'Reset Chat' to start a new conversation with updated preferences.")

# Semantic Search Cache
class SemanticSearchCache:
    def __init__(self, redis_client):
        self.redis_client = redis_client

    def get_cache_key(self, text, embedding):
        """Generate a unique cache key based on the query text"""
        text_hash = hashlib.sha256(text.lower().strip().encode()).hexdigest()
        return f"semantic_search:{text_hash}"

    def get_cached_search(self, text, embedding):
        """Get cached search results with timing"""
        start_time = time.time()
        try:
            if self.redis_client:
                cache_key = self.get_cache_key(text, embedding)
                cached = self.redis_client.get(cache_key)
                if cached:
                    return json.loads(cached), time.time() - start_time, True
        except RedisError as e:
            st.error(f"Cache retrieval error: {str(e)}")
        return None, 0, False

    def cache_search_results(self, text, embedding, results, expiry=3600):
        """Cache search results"""
        try:
            if self.redis_client:
                cache_key = self.get_cache_key(text, embedding)
                self.redis_client.setex(cache_key, expiry, json.dumps(results))
        except RedisError as e:
            st.error(f"Cache storage error: {str(e)}")

def get_similar_texts_with_cache(search_cache, text, embedding, limit=3):
    """Query similar texts with cache handling and status display"""
    # Try to get from cache
    cached_results, cache_time, is_cache_hit = search_cache.get_cached_search(text, embedding)
    
    if is_cache_hit:
        cache_time_ms = cache_time * 1000
        #st.info(f" Cache hit! Retrieval time: {cache_time_ms:.2f} milliseconds")
        return cached_results, cache_time, True
    else:
        db_start = time.time()
        results = query_similar_texts(embedding, limit)
        db_time = time.time() - db_start
        db_time_ms = db_time * 1000
        #st.info(f" Database query time: {db_time_ms:.2f} milliseconds")
        
        # Cache the results for future use
        search_cache.cache_search_results(text, embedding, results)
        return results, db_time, False


# Authentication functions
def hash_password(password):
    salt = secrets.token_hex(16)
    iterations = 120000
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        iterations,
    ).hex()
    return json.dumps({
        "algorithm": "pbkdf2_sha256",
        "iterations": iterations,
        "salt": salt,
        "hash": digest,
    })

def verify_password(password, stored_hash):
    try:
        payload = json.loads(stored_hash)
        if payload.get("algorithm") != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            payload["salt"].encode(),
            int(payload["iterations"]),
        ).hex()
        return hmac.compare_digest(digest, payload["hash"])
    except (TypeError, ValueError, KeyError, json.JSONDecodeError):
        return hmac.compare_digest(stored_hash or "", password)

def authenticate_user(redis_client, username, password):
    try:
        if redis_client:
            stored = redis_client.hget(f"user:{username}", "password")
            return stored and verify_password(password, stored)
    except RedisError:
        return False
    return False

def register_user(redis_client, username, password):
    try:
        if redis_client:
            if not redis_client.hexists(f"user:{username}", "password"):
                redis_client.hset(f"user:{username}", "password", hash_password(password))
                return True
    except RedisError:
        return False
    return False

def generate_response_with_context(messages, user_prefs, chat_history=[]):
    """Generate response with enhanced context and chat history using Converse stream API."""
    try:
        # Format preferences for context
        prefs_context = ""
        if user_prefs:
            pref_list = []
            for k, v in user_prefs.items():
                if k == 'budget_range':
                    pref_list.append(f"daily budget range: ${v[0]}-${v[1]}")
                elif v:  # Only add non-budget preferences if they're True
                    pref_list.append(k)

            if pref_list:
                prefs_context = f"\nPlease consider these user preferences: {', '.join(pref_list)}"

        # System prompt passed via the Converse 'system' parameter
        system_prompt = (
            "You are a knowledgeable travel assistant. "
            "Provide detailed, relevant responses incorporating user preferences when applicable. "
            f"Focus on giving specific, actionable advice.{prefs_context}\n\n"
            "Maintain context from the conversation history when answering questions."
        )

        # Build a multi-turn message list from chat history
        converse_messages = []
        for msg in chat_history:
            converse_messages.append({
                "role": msg["role"],
                "content": [{"text": msg["content"]}]
            })

        # Append current user message (already contains the RAG context)
        converse_messages.append({
            "role": "user",
            "content": [{"text": messages[0]["content"]}]
        })

        return bedrock.converse_stream(
            modelId=os.environ.get('BEDROCK_MODEL_ID', 'us.anthropic.claude-haiku-4-5-20251001-v1:0'),
            messages=converse_messages,
            system=[{"text": system_prompt}],
            inferenceConfig={"maxTokens": 1000, "temperature": 0.7, "topP": 0.95}
        )

    except Exception as e:
        raise Exception(f"Error in generate_response_with_context: {str(e)}")

def update_sidebar_metrics(st):
    """Update sidebar performance metrics with detailed millisecond values"""
    st.sidebar.title("Performance Metrics")
    
    # Cache Performance
    st.sidebar.subheader("Cache Performance")
    col1, col2 = st.sidebar.columns(2)
    col1.metric("Cache Hits", st.session_state.cache_hits)
    col2.metric("Cache Misses", st.session_state.cache_misses)

    # Response Times
    st.sidebar.subheader("Response Times")
   
    # Cache timing
    if st.session_state.cache_hits > 0:
        avg_cache_time_ms = (st.session_state.total_cache_time * 1000) / st.session_state.cache_hits
        st.sidebar.metric(
            "Cache Retrieval",
            f"{avg_cache_time_ms:.2f} ms",
            help="Average time to retrieve results from cache"
        )
   
    # Database timing
    if st.session_state.cache_misses > 0:
        avg_db_time_ms = (st.session_state.total_db_time * 1000) / st.session_state.cache_misses
        st.sidebar.metric(
            "Database Query",
            f"{avg_db_time_ms:.2f} ms",
            help="Average time to query the database"
        )
    
    # Chat History Performance
    st.sidebar.subheader("Chat History Performance")
    if st.session_state.history_times:
        avg_history_time = sum(t * 1000 for t in st.session_state.history_times) / len(st.session_state.history_times)
        st.sidebar.metric(
            "History Retrieval",
            f"{avg_history_time:.2f} ms",
            help="Average time to retrieve chat history"
        )
   
    if st.session_state.update_times:
        avg_update_time = sum(t * 1000 for t in st.session_state.update_times) / len(st.session_state.update_times)
        st.sidebar.metric(
            "History Update",
            f"{avg_update_time:.2f} ms",
            help="Average time to update chat history"
        )
    
    # Other Metrics
    st.sidebar.subheader("Other Metrics")
    if st.session_state.pref_times:
        avg_pref_time = sum(t * 1000 for t in st.session_state.pref_times) / len(st.session_state.pref_times)
        st.sidebar.metric(
            "Preference Integration",
            f"{avg_pref_time:.2f} ms",
            help="Average time to integrate user preferences"
        )
    
    # Total Response Time (at the end)
    if st.session_state.total_response_times:
        avg_total_time = sum(t * 1000 for t in st.session_state.total_response_times) / len(st.session_state.total_response_times)
        st.sidebar.metric(
            "Total Response Time",
            f"{avg_total_time:.2f} ms",
            help="Average end-to-end response time",
            delta_color="inverse"
        )
    


def main():
    st.title(":airplane: AZFlights Travel Bot")
    st.write("© Powered by Amazon Bedrock, Amazon Aurora and Amazon ElastiCache for Valkey")
    
    # Initialize all session state
    init_session_state()

    # Initialize connections and managers
    redis_client = init_connections()
    chat_manager = ChatHistoryManager(redis_client)
    prefs_manager = PreferencesManager(redis_client)
    search_cache = SemanticSearchCache(redis_client)
        
    if not st.session_state.logged_in:
        st.subheader("Login / Register")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        col1, col2 = st.columns(2)
        if col1.button("Login"):
            if authenticate_user(redis_client, username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid credentials")
                
        if col2.button("Register"):
            if register_user(redis_client, username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("Registered successfully!")
                st.rerun()
            else:
                st.error("Registration failed")
                
    else:
        # Sidebar content
        st.sidebar.success(f"Logged in as {st.session_state.username}")
        
        LOGO_URL = "static/AZFlights.jpg"
        st.sidebar.image(LOGO_URL, width="stretch")

        # Reset Chat and Logout buttons in sidebar
        col1, col2 = st.sidebar.columns(2)
        
        if col1.button("Reset Chat"):
            # Clear chat-related session state
            for key in ['session_id', 'cache_hits', 'cache_misses', 
                       'total_cache_time', 'total_db_time', 
                       'history_times', 'update_times']:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.session_id = str(uuid.uuid4())
            st.rerun()
            
        if col2.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        # Handle preferences in a form to prevent auto-rerun
        handle_preferences(st, prefs_manager, st.session_state.username)

        # Handle user input
        prompt = st.chat_input("Ask your travel question...")
        
        if prompt and prompt.strip():
            try:
                total_start_time = time.time()  # Start timing total response

                st.subheader("Your Question:")
                st.write(prompt)

                # Get chat history and timings
                history_start = time.time()
                chat_history, history_time = chat_manager.get_chat_history(st.session_state.session_id)
                st.session_state.history_times.append(time.time() - history_start)
            
                # Get fresh preferences from Redis only when processing a question and timings
                pref_start = time.time()
                user_prefs, prefs_time = prefs_manager.get_preferences(st.session_state.username)
                st.session_state.pref_times.append(time.time() - pref_start)
            
                if user_prefs:
                    st.info(f"🎯 Active preferences: {', '.join(user_prefs.keys())}")
           
                # Generate embedding and search
                with st.spinner("Processing your question..."):
                    embedding = get_embedding(prompt)
                    if embedding is None:
                        st.error("Failed to generate embedding")
                        return
               
                    # Search with cache handling
                    similar_texts, query_time, is_cache_hit = get_similar_texts_with_cache(
                        search_cache,
                        prompt,
                        embedding
                    )
               
                    # Only show cache hit/miss status in chat interface
                    if is_cache_hit:
                        st.session_state.cache_hits += 1
                        st.session_state.total_cache_time += query_time
                        st.info("💾 Cache hit!")
                    else:
                        st.session_state.cache_misses += 1
                        st.session_state.total_db_time += query_time
                        st.info("🔍 Cache miss - Querying database...")
               
                    # Generate response
                    st.subheader("Chatbot Response:")
                    context = "\n".join([text['content'] for text in similar_texts])
               
                    # Prepare message with context
                    messages = [
                        {
                            "role": "user",
                            "content": f"Using this context:\n{context}\n\nPlease answer this question: {prompt}"
                        }
                    ]
               
                    response_container = st.empty()
                    full_response = ""
                    start_time = time.time()
               
                    try:
                        # Generate response with preferences and chat history
                        response = generate_response_with_context(messages, user_prefs, chat_history)

                        for event in response["stream"]:
                            if "contentBlockDelta" in event:
                                delta = event["contentBlockDelta"].get("delta", {})
                                if "text" in delta:
                                    full_response += delta["text"]
                                    response_container.markdown(full_response + "▌")

                        response_container.markdown(full_response)

                    except Exception as e:
                        st.error(f"Error generating response: {str(e)}")
                        return
               
                    # Update chat history if response was successful
                    success = False
                    update_time = None
                    if full_response:
                        success, update_time = chat_manager.update_chat_history(
                            st.session_state.session_id, prompt, full_response)

                    if success:
                        st.session_state.update_times.append(update_time)
                   
                    # Record total time and update metrics
                    total_time = time.time() - total_start_time
                    st.session_state.total_response_times.append(total_time)

                    # Update sidebar metrics
                    update_sidebar_metrics(st)
           
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                return
        
        # Version info
        st.sidebar.divider()
        st.sidebar.caption(f"""
        Version: 1.0.0
        Last Updated: {datetime.now().strftime('%Y-%m-%d')}
        """)

if __name__ == "__main__":
    main()
