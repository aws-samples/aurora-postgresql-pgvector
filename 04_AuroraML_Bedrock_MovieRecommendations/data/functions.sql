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
    rcnt integer;
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

CREATE OR REPLACE FUNCTION movie.get_reviews_summary(pmovieid bigint) 
RETURNS jsonb LANGUAGE plpgsql  AS $$
DECLARE 
    v1 text ;
    rsummary jsonb;
BEGIN
	WITH 
    p AS ( 
        SELECT '\n\nHuman: Please provide a summary of the following text.\n<text>\n{doc_text}\n </text>\n\nAssistant:' AS prompt
    )
    , m AS (
        SELECT 
            id, 
            regexp_replace(
            regexp_replace(regexp_replace(regexp_replace(STRING_AGG(review, '\n'), E'[\\n\\r]+', '\n', 'g'),
                '[\\10|/10]', ' out of 10', 'g'), $y$['"-]$y$, '', 'g'), '[^[:ascii:]]', '', 'g')  
            AS reviews 
        FROM movie.reviews
        WHERE id = pmovieid
        GROUP BY id
    )
    SELECT replace(p.prompt, '{doc_text}', m.reviews)  
    	INTO v1
    FROM m CROSS JOIN p ;
    
    EXECUTE $x$ 
        	SELECT aws_bedrock.invoke_model(
         		model_id      := 'anthropic.claude-v2',
         		content_type  := 'application/json',
         		accept_type  := 'application/json',
         		model_input := $1::text
         		)
         		$x$
         into rsummary
         using '{"prompt": "'|| v1 || '", "max_tokens_to_sample": 4096, "temperature": 0.5, "top_k": 250, "top_p": 0.5, "stop_sequences":[] }' ;
	RETURN rsummary;         
END$$;

