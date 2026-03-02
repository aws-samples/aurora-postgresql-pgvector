import streamlit as st
from datetime import datetime
import psycopg
import pandas as pd
import plotly.express as px
import numpy as np
import os
from dotenv import load_dotenv
import boto3
import json
import base64
import warnings
import logging
import time
from botocore.config import Config
from botocore.exceptions import ClientError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress the specific SQLAlchemy warning
warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy connectable.*")

# Load environment variables
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

# Add this test function
def test_bedrock_connection():
    try:
        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 100,
                "messages": [
                    {"role": "user", "content": "Say hello"}
                ]
            })
        )
        response_body = json.loads(response.get('body').read())
        return response_body['content'][0]['text']
    except Exception as e:
        print(f"Error type: {type(e)}")
        print(f"Error message: {str(e)}")
        raise e

# Constants and configurations
LOGO_URL = "static/Blaize.png"
CLAUDE_MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"

# Helper functions
@st.cache_data
def get_base64_of_bin_file(bin_file):
    with open(bin_file, "rb") as f:
        data = f.read()
        return base64.b64encode(data).decode()

# Database functions
def get_db_connection():
    try:
        return psycopg.connect(
            host=os.getenv("DB_HOST"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            port=os.getenv("DB_PORT", "5432")
        )
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        st.error("Failed to connect to database. Please check your configuration.")
        return None

# Database query function with proper error handling
def execute_db_query(query, params=None):
    try:
        with get_db_connection() as conn:
            return pd.read_sql(query, conn, params=params)
    except Exception as e:
        logger.error(f"Database query error: {e}")
        st.error("Failed to execute database query.")
        return pd.DataFrame()

# Functions for graphs
def get_product_data():
    query = """
    SELECT "productId", product_description, category_name, stars, price, boughtinlastmonth, embedding
    FROM bedrock_integration.product_catalog
    """
    return execute_db_query(query)

def similarity_search(query_embedding, top_k=5):
    """
    SELECT "productId", product_description, category_name, stars, price, boughtinlastmonth,
           imgURL, producturl,
           1 - (embedding <=> %s::vector) AS similarity
    FROM bedrock_integration.product_catalog
    WHERE embedding IS NOT NULL
    ORDER BY embedding <=> %s::vector
    LIMIT %s
    """
    query_embedding_list = query_embedding.tolist() if isinstance(query_embedding, np.ndarray) else query_embedding
    start_time = time.time()

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(similarity_search.__doc__, 
                          (query_embedding_list, query_embedding_list, min(int(top_k), 100)))
                results = cur.fetchall()
                
                df = pd.DataFrame(results, columns=[
                    'productId', 'product_description', 'category_name', 
                    'stars', 'price', 'boughtinlastmonth', 
                    'imgURL', 'producturl', 'similarity'
                ])
                
                query_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                return df, query_time
                
    except Exception as e:
        st.error(f"Error in similarity search: {str(e)}")
        return pd.DataFrame(), 0

def get_top_trending_categories(top_n=10):
    """
    SELECT category_name, SUM(boughtinlastmonth) as total_bought
    FROM bedrock_integration.product_catalog
    GROUP BY category_name
    ORDER BY total_bought DESC
    LIMIT %s
    """
    query = get_top_trending_categories.__doc__
    return execute_db_query(query, (top_n,))
        
def get_top_grossing_products(top_n=10):
    """
    SELECT product_description, category_name, price * boughtinlastmonth as total_revenue, 
           boughtinlastmonth, stars, price
    FROM bedrock_integration.product_catalog
    ORDER BY total_revenue DESC
    LIMIT %s
    """
    query = get_top_grossing_products.__doc__
    return execute_db_query(query, (top_n,))
        
def get_top_selling_products(top_n=10):
    """
    SELECT product_description, category_name, boughtinlastmonth, stars, price
    FROM bedrock_integration.product_catalog
    ORDER BY boughtinlastmonth DESC
    LIMIT %s
    """
    query = get_top_selling_products.__doc__
    return execute_db_query(query, (top_n,))

def get_top_rated_categories(top_n=10):
    """
    SELECT category_name, AVG(stars) as avg_rating
    FROM bedrock_integration.product_catalog
    GROUP BY category_name
    ORDER BY avg_rating DESC
    LIMIT %s
    """
    query = get_top_rated_categories.__doc__
    return execute_db_query(query, (top_n,))

# TO-DO
def get_best_selling_by_category(top_n=10):
    """
    # TO-DO
    """
    query = get_best_selling_by_category.__doc__
    return execute_db_query(query, (top_n,))

def get_spending_habits():
    """
    WITH price_ranges AS (
        SELECT 
            CASE 
                WHEN price < 20 THEN 'Under $20'
                WHEN price >= 20 AND price < 50 THEN '$20 - $49.99'
                WHEN price >= 50 AND price < 100 THEN '$50 - $99.99'
                WHEN price >= 100 AND price < 200 THEN '$100 - $199.99'
                ELSE '$200 and above'
            END AS price_range,
            boughtinlastmonth
        FROM bedrock_integration.product_catalog
    )
    SELECT 
        price_range,
        COUNT(*) as product_count,
        SUM(boughtinlastmonth) as total_sold
    FROM price_ranges
    GROUP BY price_range
    ORDER BY 
        CASE price_range
            WHEN 'Under $20' THEN 1
            WHEN '$20 - $49.99' THEN 2
            WHEN '$50 - $99.99' THEN 3
            WHEN '$100 - $199.99' THEN 4
            ELSE 5
        END
    """
    query = get_spending_habits.__doc__
    return execute_db_query(query)

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

# Get Claude response
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
    except Exception as e:
        print(f"Claude error: {str(e)}")  # For debugging
        return None

# UI functions
def show_product_insights():
    st.subheader("Product Insights Dashboard")

    with st.spinner("Loading product insights..."):
        # Create three columns for the first row of charts
        col1, col2, col3 = st.columns(3)

        with col1:
            # Top 10 Trending Categories
            trending_categories = get_top_trending_categories(10)
            if not trending_categories.empty:
                fig_trending = px.bar(trending_categories.sort_values('total_bought', ascending=True), 
                                  x='total_bought', y='category_name',
                                  labels={'total_bought': 'Units Sold Last Month', 'category_name': 'Category'},
                                  title="Top 10 Trending Categories",
                                  orientation='h',
                                  color='total_bought',
                                  color_continuous_scale=px.colors.sequential.Viridis)
                fig_trending.update_layout(showlegend=True, height=400, yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_trending, use_container_width=True)
            else:
                st.warning("No trending categories data available")

        with col2:
            # Top 10 Highest Grossing Products
            top_grossing = get_top_grossing_products(10)
            if not top_grossing.empty:
                # Create a shortened product name
                top_grossing['short_name'] = top_grossing['product_description'].str[:20] + '...'
                fig_grossing = px.bar(top_grossing, x='total_revenue', y='short_name',
                                  color='category_name', 
                                  hover_data=['product_description', 'boughtinlastmonth', 'price'],
                                  labels={'total_revenue': 'Total Revenue', 
                                          'short_name': 'Product',
                                          'product_description': 'Full Product Name'},
                                  title="Top 10 Highest Grossing Products",
                                  color_discrete_sequence=px.colors.qualitative.Vivid)
                fig_grossing.update_layout(showlegend=True, height=400, legend_title_text='Category', yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_grossing, use_container_width=True)
            else:
                st.warning("No revenue data available")

        with col3:
            # Top 10 Best Selling Products
            top_selling = get_top_selling_products(10)
            if not top_selling.empty:
                top_selling['short_name'] = top_selling['product_description'].str[:20] + '...'
                fig_top_selling = px.bar(top_selling, x='boughtinlastmonth', y='short_name',
                                     color='category_name', 
                                     hover_data=['product_description', 'stars', 'price'],
                                     labels={'boughtinlastmonth': 'Units Sold Last Month', 
                                             'short_name': 'Product',
                                             'product_description': 'Full Product Name'},
                                     title="Top 10 Best Selling Products",
                                     orientation='h',
                                     height=500,
                                     color_discrete_sequence=px.colors.qualitative.Bold)
                fig_top_selling.update_layout(showlegend=True, legend_title_text='Category', yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_top_selling, use_container_width=True)
            else:
                st.warning("No sales data available")

        # Create three columns for the second row of charts
        col4, col5, col6 = st.columns(3)

        with col4:
            # Top 10 Categories by Rating
            top_categories = get_top_rated_categories(10)
            if not top_categories.empty:
                fig_categories = px.bar(top_categories.sort_values('avg_rating', ascending=True), 
                                    x='avg_rating', y='category_name',
                                    labels={'avg_rating': 'Average Rating', 'category_name': 'Category'},
                                    title="Top 10 Categories by Average Rating",
                                    orientation='h',
                                    color='avg_rating',
                                    color_continuous_scale=px.colors.sequential.Magma)
                fig_categories.update_layout(height=400, yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_categories, use_container_width=True)
            else:
                st.warning("No rating data available")

        with col5:
            # Best Selling Products in each category
            best_selling_by_category = get_best_selling_by_category()
            if not best_selling_by_category.empty:
                fig_best_selling = px.bar(best_selling_by_category.sort_values('boughtinlastmonth', ascending=True), 
                                      x='boughtinlastmonth', y='category_name',
                                      labels={'boughtinlastmonth': 'Units Sold Last Month', 'category_name': 'Category'},
                                      title="Best Selling Product in Each Category",
                                      orientation='h',
                                      color='product_description',
                                      hover_data=['product_description'],
                                      color_continuous_scale=px.colors.sequential.Inferno)
                fig_best_selling.update_layout(showlegend=False, height=400, yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_best_selling, use_container_width=True)
            else:
                st.warning("No category sales data available")

        with col6:
            # General Spending Habits
            spending_habits = get_spending_habits()
            if not spending_habits.empty:
                fig_spending = px.pie(spending_habits.sort_values('total_sold', ascending=False), 
                                  values='total_sold', names='price_range',
                                  title="General Spending Habits of Online Shoppers",
                                  hover_data=['product_count'],
                                  color_discrete_sequence=px.colors.qualitative.G10)
                fig_spending.update_traces(textposition='inside', textinfo='percent+label')
                fig_spending.update_layout(showlegend=True, legend_title_text='Price Range', height=400)
                st.plotly_chart(fig_spending, use_container_width=True)
            else:
                st.warning("No spending habits data available")

    # Show SQL queries in expanders
    with st.expander("View SQL Queries"):
        st.caption("These are the SQL Queries used to generate the Product Insights Dashboard.")
        st.code(get_top_trending_categories.__doc__, language="sql")
        st.code(get_top_grossing_products.__doc__, language="sql")
        st.code(get_top_selling_products.__doc__, language="sql")
        st.code(get_top_rated_categories.__doc__, language="sql")
        st.code(get_best_selling_by_category.__doc__, language="sql")
        st.code(get_spending_habits.__doc__, language="sql")

    # AI-Powered Market Insights
    st.subheader("AI-Powered Market Insights")
    
    # Add button for generating insights
    if st.button("📊 Generate AI Insights", type="primary"):
        with st.spinner("Generating AI insights..."):
            # Prepare simplified data for the prompt
            insights_data = {
                "trending_categories": trending_categories[['category_name', 'total_bought']].head().to_dict('records'),
                "top_grossing": top_grossing[['product_description', 'total_revenue', 'price']].head().to_dict('records'),
                "top_selling": top_selling[['product_description', 'boughtinlastmonth', 'price']].head().to_dict('records'),
                "category_ratings": top_categories[['category_name', 'avg_rating']].head().to_dict('records'),
                "spending_habits": spending_habits[['price_range', 'total_sold']].to_dict('records')
            }
            
            insights_prompt = f"""
            Based on this e-commerce data:
            Trending Categories: {insights_data['trending_categories']}
            Top Grossing Products: {insights_data['top_grossing']}
            Best Selling Products: {insights_data['top_selling']}
            Category Ratings: {insights_data['category_ratings']}
            Customer Spending: {insights_data['spending_habits']}

            Provide a brief analysis of:
            1. Key market trends and patterns
            2. Top performing products and categories
            3. Customer spending patterns
            4. Actionable recommendations for inventory and pricing

            Format the response in markdown with clear sections and bullet points.
            """
            
            try:
                claude_insights = get_claude_response(insights_prompt)
                if claude_insights:
                    st.markdown(claude_insights)
                    
                    # Add a download button for the insights
                    st.download_button(
                        label="📥 Download Insights",
                        data=claude_insights,
                        file_name="market_insights.md",
                        mime="text/markdown"
                    )
                else:
                    st.error("Unable to generate AI insights. Please try again.")
            except Exception as e:
                st.error(f"Error generating insights: {str(e)}")
    else:
        st.info("Click the button above to generate AI-powered insights from your product data.")
                
        # Add feedback section
        st.divider()
        feedback = st.radio(
            "Was this AI analysis helpful?",
            ("Very Helpful", "Somewhat Helpful", "Not Helpful"),
            index=None,
            horizontal=True
            )
        if feedback:
            st.toast(f"Thank you for your feedback: {feedback}")

def main():
    st.set_page_config(
        page_title="Product Insights - Blaize Bazaar",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Page Header
    st.subheader('Product Insights - Blaize Bazaar', divider='orange')
    
    # Sidebar
    st.sidebar.image(LOGO_URL, use_container_width=True)
    st.sidebar.title('**About**')
    st.sidebar.info("""
    This dashboard provides comprehensive product insights using AI-powered analysis.
    
    Features:
    - Real-time sales analytics
    - Category performance metrics
    - Revenue analysis
    - AI-powered market insights
    - Customer behavior analysis
    """)
    
    # Add refresh button in sidebar
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    
    # Add version info
    st.sidebar.divider()
    st.sidebar.caption(f"""
    Version: 1.0.0
    Last Updated: {datetime.now().strftime('%Y-%m-%d')}
    """)

    st.sidebar.image("static/Powered-By_logo-stack_RGB_REV.png", width=150)
    
    try:
        show_product_insights()
    except Exception as e:
        logger.error(f"Error in main application: {e}")
        st.error("An unexpected error occurred. Please try again later or contact support.")
        if st.button("Show Error Details"):
            st.code(str(e))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Application startup error: {e}")
        st.error("Failed to start the application. Please check the logs and try again.")