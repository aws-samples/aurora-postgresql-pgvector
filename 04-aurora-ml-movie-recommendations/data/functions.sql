-- Functions
CREATE OR REPLACE FUNCTION movie.get_top6_movies(search_query text) RETURNS TABLE(
                id bigint,
                title text,
                poster text,
                overview text
        ) LANGUAGE plpgsql AS $$
DECLARE r record;
v vector(1024);
rcnt integer;
BEGIN
EXECUTE $x$
SELECT aws_bedrock.invoke_model_get_embeddings(
                model_id := 'amazon.titan-embed-text-v2:0',
                content_type := 'application/json',
                json_key := 'embedding',
                model_input := $1::text
        ) $x$ INTO v USING jsonb_build_object('inputText', search_query, 'dimensions', 1024, 'normalize', true)::text;
RETURN QUERY
SELECT m.id,
        m.title,
        m.poster,
        m.overview
FROM movie.movies m
ORDER BY m.movie_embedding <=>v
LIMIT 6;
END $$;
CREATE OR REPLACE PROCEDURE movie.generate_movie_embeddings(pmovieid bigint default NULL) LANGUAGE plpgsql AS $$
DECLARE r record;
v vector(1024);
v1 text;
rcnt integer := 0;
BEGIN FOR r IN
SELECT id,
        title,
        overview,
        ARRAY_TO_STRING(keywords, ' ') keywords,
        ARRAY_TO_STRING(genre_id, ' ') genres,
        STRING_AGG(c->>'name', ' , ') credits
FROM movie.movies m
        CROSS JOIN jsonb_array_elements(credits) AS c
WHERE movie_embedding IS NULL
        and (
                (pmovieid is NULL)
                OR (
                        pmovieid IS NOT NULL
                        and id = pmovieid
                )
        )
GROUP BY id,
        title,
        overview,
        ARRAY_TO_STRING(keywords, ' '),
        ARRAY_TO_STRING(genre_id, ' ') LOOP RAISE NOTICE 'working on movie id %',
        r.id;
v1 := regexp_replace(
        r.title || ' ' || r.overview || ' ' || r.keywords || ' ' || r.genres || ' ' || r.credits,
        '\s\s+',
        ' ',
        'g'
);
EXECUTE $x$
SELECT aws_bedrock.invoke_model_get_embeddings(
                model_id := 'amazon.titan-embed-text-v2:0',
                content_type := 'application/json',
                json_key := 'embedding',
                model_input := $1::text
        ) $x$ INTO v USING jsonb_build_object('inputText', v1, 'dimensions', 1024, 'normalize', true)::text;
UPDATE movie.movies
set movie_embedding = v
WHERE id = r.id;
rcnt := rcnt + 1;
IF rcnt >= 10 THEN COMMIT;
rcnt := 0;
END IF;
END LOOP;
COMMIT;
END $$;
CREATE OR REPLACE FUNCTION movie.get_reviews_summary(p_movieid bigint) RETURNS jsonb AS $$
DECLARE v_summary jsonb;
v_reviews text;
v_payload text;
BEGIN -- Collect and clean the reviews text
SELECT regexp_replace(
                regexp_replace(
                        regexp_replace(
                                regexp_replace(STRING_AGG(review, ' '), E'[\\n\\r]+', ' ', 'g'),
                                '[\\10|/10]',
                                ' out of 10',
                                'g'
                        ),
                        $y$ ['"-] $y$,
                        '',
                        'g'
                ),
                '[^[:ascii:]]',
                '',
                'g'
        ) INTO v_reviews
FROM movie.reviews
WHERE id = p_movieid
GROUP BY id;
IF v_reviews IS NOT NULL THEN -- Build JSON payload safely using jsonb functions to handle escaping
v_payload := jsonb_build_object(
        'anthropic_version',
        'bedrock-2023-05-31',
        'max_tokens',
        4096,
        'messages',
        jsonb_build_array(
                jsonb_build_object(
                        'role',
                        'user',
                        'content',
                        'Please provide a summary of the following movie reviews: ' || v_reviews
                )
        )
)::text;
EXECUTE $q$
SELECT aws_bedrock.invoke_model(
                model_id := 'global.anthropic.claude-sonnet-5',
                content_type := 'application/json',
                accept_type := 'application/json',
                model_input := $1
        ) $q$ INTO v_summary USING v_payload;
ELSE v_summary := '{"content": [{"text": "No reviews are available for this movie.", "type": "text"}]}'::jsonb;
END IF;
RETURN v_summary;
END $$ LANGUAGE plpgsql;

-- HNSW index for fast cosine-distance (<=>) nearest-neighbour search.
-- Run AFTER generating embeddings with movie.generate_movie_embeddings().
-- If you change the embedding model, drop and recreate this index.
CREATE INDEX IF NOT EXISTS movies_embedding_hnsw_idx
        ON movie.movies
        USING hnsw (movie_embedding vector_cosine_ops);