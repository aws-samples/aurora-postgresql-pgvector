import streamlit as st
import pandas as pd
import psycopg2
import psycopg2.extras
import os
import json

dbhost=os.environ.get('DBHOST', 'host.docker.internal')
dbport=os.environ.get('DBPORT', 5432)
dbuser=os.environ.get('DBUSER', 'postgres')
dbpass=os.environ.get('DBPASSWORD', 'postgres')
dbname=os.environ.get('DBNAME', 'moviedb')

st.write("## :orange[Movie Recommendations :cinema:]")

@st.cache_data
def load_data():
    with psycopg2.connect(database=dbname, host=dbhost, port=dbport, user=dbuser, password=dbpass) as dbconn:
        sql = "SELECT id, title FROM movie.movies;"
        return pd.read_sql_query(sql, dbconn, index_col="id")

def write_columns_data(result):
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.image("https://image.tmdb.org/t/p/w185{}".format(result[0].get('poster')))
    col2.image("https://image.tmdb.org/t/p/w185{}".format(result[1].get('poster')))
    col3.image("https://image.tmdb.org/t/p/w185{}".format(result[2].get('poster')))
    col4.image("https://image.tmdb.org/t/p/w185{}".format(result[3].get('poster')))
    col5.image("https://image.tmdb.org/t/p/w185{}".format(result[4].get('poster')))
    return

def get_review_summary(option, dbconn):
        qry = """WITH 
                    p AS ( 
                        SELECT '\\n\\nHuman: Please provide a summary of the following text.\\n<text>\\n{doc_text}\\n </text>\\n\\nAssistant:' AS prompt
                        )
                    , m AS (
                        SELECT 
                            id, 
                            regexp_replace(
                            regexp_replace(regexp_replace(regexp_replace(STRING_AGG(review, '\\n'), E'[\\n\\r]+', '\\n', 'g'),
                            '[\\10|/10]', ' out of 10', 'g'), $$['\"-]$$, '', 'g'), '[^[:ascii:]]', '', 'g')  
                            AS reviews 
                        FROM movie.reviews
                        WHERE id = (select id from movie.movies where title = %s limit 1)
                        GROUP BY id
                        )
                    SELECT
                        aws_bedrock.invoke_model(
                            model_id        := 'anthropic.claude-v2',
                            content_type    := 'application/json',
                            accept_type  := 'application/json',
                            model_input  := '{\"prompt": \"'|| replace(p.prompt, '{doc_text}', m.reviews) || '\", \"max_tokens_to_sample\": 4096, \"temperature\": 0.5, \"top_k\": 250, \"top_p\": 0.5, \"stop_sequences\":[] }'
                        )
                    FROM m cross join p;"""

        with dbconn.cursor(cursor_factory = psycopg2.extras.RealDictCursor) as tcur:
            tcur.execute(qry, (option, ))
            result = tcur.fetchall()
            return json.loads( result[0].get('invoke_model') )

try:
    df = load_data()
    option = st.selectbox('##### :orange[Select a movie you watched?]', df.title.unique())
    st.write('You have selected :orange[', option, ']')
    st.divider()
    with psycopg2.connect(database=dbname, host=dbhost, port=dbport, user=dbuser, password=dbpass) as dbconn:
        dbcur = dbconn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
        dbcur.execute("SELECT m.id, m.title, m.poster, m.overview FROM movie.movies m WHERE title = %s", (option, ))
        result = dbcur.fetchall()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.header(option)
            st.image("https://image.tmdb.org/t/p/w185{}".format(result[0].get('poster')))
        with col2:
            st.header("Story")
            st.write(result[0].get('overview'))
        with col3:
            st.header("Summary of user reviews")
            res = get_review_summary(option, dbconn)
            st.write(res.get('completion'))
        
    st.divider()
    with st.container():
        st.write("##### :green[Personalized Movie Recommendations]")
        with psycopg2.connect(database=dbname, host=dbhost, port=dbport, user=dbuser, password=dbpass) as dbconn:
            dbcur = dbconn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
            dbcur.execute("SELECT m.id, m.title, m.poster FROM movie.movies m WHERE title <> %s ORDER BY m.movie_embedding <-> (SELECT movie_embedding FROM movie.movies WHERE title = %s LIMIT 1)  LIMIT 5;", (option, option, ))
            result = dbcur.fetchall()
            write_columns_data(result)
        st.divider()
        
except Exception as e:
    print ("Error {}".format(e))
