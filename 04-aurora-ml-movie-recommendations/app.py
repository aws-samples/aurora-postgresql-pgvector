import streamlit as st
import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv

st.set_page_config(page_title="Movie Recommendations", page_icon="🎬", layout="wide")

# Minimal custom styling
st.markdown("""
<style>
    .stApp { max-width: 1200px; margin: 0 auto; }
    div[data-testid="stImage"] img { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)


def write_columns_data(result):
    cols = st.columns(5)
    for i, col in enumerate(cols):
        movie = result[i + 1]
        with col:
            st.image(
                "https://image.tmdb.org/t/p/w185{}".format(movie.get('poster')),
                width="stretch",
            )
            st.caption(movie.get('title', ''))


def main():
    st.title("🎬 Movie Recommendations")
    st.caption("Powered by Aurora PostgreSQL, pgvector, and Amazon Bedrock")

    query = st.text_input(
        "What kind of movie are you looking for?",
        placeholder="e.g. Tom Cruise action movies, sci-fi space adventures, romantic comedies...",
    )

    if not query:
        st.info("Enter a search above to find movies using semantic similarity search.")
        return

    with psycopg2.connect(
        database=dbname, host=dbhost, port=dbport, user=dbuser, password=dbpass
    ) as dbconn:
        dbcur = dbconn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Fetch top 6 matches
        dbcur.execute("SELECT * FROM movie.get_top6_movies(%s);", (query,))
        result = dbcur.fetchall()

        if not result:
            st.warning("No movies found. Try a different search.")
            return

        # --- Top match ---
        st.divider()
        st.subheader("Top Match")

        col_poster, col_details = st.columns([1, 3])

        with col_poster:
            st.image(
                "https://image.tmdb.org/t/p/w342{}".format(result[0].get('poster')),
                width="stretch",
            )

        with col_details:
            st.markdown(f"### {result[0].get('title')}")

            with st.expander("Story", expanded=True):
                st.write(result[0].get('overview'))

            with st.expander("AI Review Summary", expanded=True):
                with st.spinner("Generating review summary with Claude Sonnet 4.6..."):
                    dbcur.execute(
                        "SELECT movie.get_reviews_summary(%s)",
                        (result[0].get('id'),),
                    )
                    res = dbcur.fetchall()
                    if res:
                        summary = (
                            res[0]
                            .get('get_reviews_summary', {})
                            .get('content', [{}])[0]
                            .get('text', 'No summary available.')
                        )
                        st.markdown(summary)
                    else:
                        st.write("No reviews available for this movie.")


        # --- Recommended movies ---
        if len(result) > 1:
            st.divider()
            st.subheader("You Might Also Like")
            write_columns_data(result)

        st.divider()


if __name__ == '__main__':
    load_dotenv()

    dbname = os.environ.get('DBNAME')
    dbhost = os.environ.get('DBHOST')
    dbuser = os.environ.get('DBUSER')
    dbpass = os.environ.get('DBPASS')
    dbport = os.environ.get('DBPORT')

    main()
