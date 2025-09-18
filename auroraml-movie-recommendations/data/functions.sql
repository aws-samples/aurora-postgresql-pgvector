-- Functions

CREATE OR REPLACE FUNCTION movie.get_top6_movies(search_query text) 
RETURNS TABLE(
    id bigint,
    title text,
    poster text,
    overview text
)
LANGUAGE plpgsql
AS $$
DECLARE 
    r record; 
    v vector(1536); 
    rcnt integer;
BEGIN
    RAISE NOTICE '%s', '{"inputText": "'|| search_query ||'"}'::text ;
    EXECUTE $x$ 
        SELECT aws_bedrock.invoke_model_get_embeddings(
         		model_id      := 'amazon.titan-embed-text-v1',
         		content_type  := 'application/json',
         		json_key      := 'embedding',
                model_input := $1::text
        )
         	$x$
    INTO v 
    USING  '{"inputText": "'|| search_query ||'"}'::text ; 
    RETURN QUERY SELECT  m.id, m.title, m.poster, m.overview FROM movie.movies m ORDER BY m.movie_embedding <-> v LIMIT 6 ;
END$$;

CREATE OR REPLACE PROCEDURE movie.generate_movie_embeddings(pmovieid bigint default NULL) 
LANGUAGE plpgsql
AS $$
DECLARE 
    r record; 
    v vector(1536); 
    v1 text ;
    rcnt integer := 0;
BEGIN
    FOR r IN SELECT id, 
                title, overview, 
                ARRAY_TO_STRING(keywords, ' ') keywords, 
                ARRAY_TO_STRING(genre_id, ' ') genres, 
                STRING_AGG(c->>'name', ' , ') credits
            FROM movie.movies m CROSS JOIN jsonb_array_elements(credits) AS c
            WHERE movie_embedding IS NULL
             and ((pmovieid is NULL) OR (pmovieid IS NOT NULL and id = pmovieid))
            GROUP BY id, title, overview, ARRAY_TO_STRING(keywords, ' '),  ARRAY_TO_STRING(genre_id, ' ') 
    LOOP
        RAISE NOTICE 'working on movie id %', r.id ;
        v1 := replace(replace(replace(r.title||' '||r.overview||' '||r.keywords||' '||r.genres||' '||r.credits, chr(39), ''), '"', ''), '-', ' ') ;
	v1 := regexp_replace(v1, '\s\s+', ' ', 'g');

        EXECUTE $x$ 
        	SELECT aws_bedrock.invoke_model_get_embeddings(
         		model_id      := 'amazon.titan-embed-text-v1',
         		content_type  := 'application/json',
         		json_key      := 'embedding',
                model_input   := $1::text
            )
         		$x$
        INTO v 
        USING  '{"inputText": "'|| v1 ||'"}'::text ; 

        UPDATE movie.movies set movie_embedding = v
        WHERE id = r.id ;
        rcnt := rcnt + 1;
        IF rcnt > 10 THEN
            COMMIT;
            rcnt := 0;
        END IF;
    END LOOP;
    COMMIT;
END$$;

CREATE OR REPLACE FUNCTION movie.get_reviews_summary(p_movieid bigint) RETURNS jsonb AS 
$$
DECLARE 
        v_summary jsonb;
        v_count int;
        v_sql text;
BEGIN
        SELECT aws_bedrock.invoke_model(
                model_id := 'anthropic.claude-v2',
                content_type := 'application/json',
                accept_type := 'application/json',
                model_input := '{"prompt": "\n\nHuman: Please provide a summary of the following text.\n<text>\n'|| sub.reviews || '\n </text>\n\nAssistant:", "max_tokens_to_sample": 4096, "temperature": 0.5, "top_k": 250, "top_p": 0.5, "stop_sequences":[] }' )
        INTO v_summary
        FROM    (
                SELECT id, 
                        regexp_replace(regexp_replace(regexp_replace(regexp_replace(STRING_AGG(review, '\n'), E'[\\n\\r]+', '\n', 'g'), '[\\10|/10]', ' out of 10', 'g'), $y$['"-]$y$, '', 'g'), '[^[:ascii:]]', '', 'g')  as reviews
                FROM movie.reviews
                WHERE id = p_movieid
                GROUP BY id
                ) AS sub;
        GET DIAGNOSTICS v_count := ROW_COUNT;

        IF v_count = 0 THEN
                v_sql := 'SELECT aws_bedrock.invoke_model(
                        model_id := ''anthropic.claude-v2'',
                        content_type := ''application/json'',
                        accept_type := ''application/json'',
                        model_input := ''{"prompt": "\n\nHuman: Please provide a summary of the following text.\n<text>\nNo reviews are available.\n </text>\n\nAssistant:", "max_tokens_to_sample": 4096, "temperature": 0.5, "top_k": 250, "top_p": 0.5, "stop_sequences":[] }'' )';
                EXECUTE v_sql 
                INTO v_summary;
        END IF;
        RETURN v_summary;         
END
$$
LANGUAGE plpgsql;

