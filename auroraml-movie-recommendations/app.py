import streamlit as st
import pandas as pd
import psycopg2
import psycopg2.extras
import os
import json
from dotenv import load_dotenv

def write_columns_data(result):
    col1, col2, col3, col4, col5 = st.columns(5)
    colarray = [ col1, col2, col3, col4, col5 ]
    for x in range(5):
        colarray[x].image("https://image.tmdb.org/t/p/w185{}".format(result[x+1].get('poster')))
    return

def main():
    st.title(':orange[Movie Catalog Demo :cinema:]')
    query = st.text_input('Search for a movie')
    if query:
        with psycopg2.connect(database=dbname, host=dbhost, port=dbport, user=dbuser, password=dbpass) as dbconn:
            st.divider()
            st.subheader('Top Matching Movie:')
            dbcur = dbconn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
            dbcur.execute("SELECT * FROM movie.get_top6_movies(%s);", (query,))
            result = dbcur.fetchall()
            col1, col2, col3 = st.columns(3)
            with col1:
                st.subheader(result[0].get('title'))
                st.image("https://image.tmdb.org/t/p/w185{}".format(result[0].get('poster')))
            with col2:
                st.subheader("Story")
                st.write(result[0].get('overview'))
            with col3:
                st.subheader("Summary of user reviews")
                dbcur.execute("SELECT movie.get_reviews_summary(%s)", (result[0].get('id'), ))
                res = dbcur.fetchall()
                if res:
                    st.write( res[0].get('get_reviews_summary').get('completion').replace(' Here is a summary of the key points from the text:\n\n-', '') )
            st.divider()
            st.subheader('Top 5 Recommended Movies:')
            with st.container():
                write_columns_data(result)
        st.divider()
        
if __name__ == '__main__':

    # This function loads the environment variables from a .env file.
    load_dotenv()

    dbname=os.environ.get('DBNAME')
    dbhost=os.environ.get('DBHOST')
    dbuser=os.environ.get('DBUSER')
    dbpass=os.environ.get('DBPASS')
    dbport=os.environ.get('DBPORT')

    main()

