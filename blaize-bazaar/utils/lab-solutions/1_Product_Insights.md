# Solutions Guide: Product Insights 🎯
> This guide provides detailed solutions and explanations for exercises and challenges in the workshop.

1. **Get best selling products by category**
```python
def get_best_selling_by_category(top_n=10):
    """
    SELECT DISTINCT ON (category_name) 
        category_name, product_description, boughtinlastmonth
    FROM bedrock_integration.product_catalog
    ORDER BY category_name, boughtinlastmonth DESC
    LIMIT %s
    """
    query = get_best_selling_by_category.__doc__
    return execute_db_query(query, (top_n,))
```

2. **(OPTIONAL) Challenge Exercise: Extending the Search**
```sql
-- Original query:
SELECT "productId", product_description, 
       1 - (embedding <=> %s::vector) AS similarity
FROM product_catalog
ORDER BY embedding <=> %s::vector
LIMIT %s;

-- Enhanced query with all requirements:
SELECT 
    p."productId",
    p.product_description,
    p.category_name,
    p.price,
    p.stars,
    1 - (p.embedding <=> %s::vector) AS similarity
FROM 
    product_catalog p
WHERE 
    -- 1. Minimum similarity threshold (similarity score ranges from 0 to 1)
    1 - (p.embedding <=> %s::vector) >= 0.7  -- 70% similarity threshold
    
    -- 2. Category filter
    AND p.category_name = 'Electronics'  -- Replace with desired category
    
    -- 3. Traditional filters
    AND p.price BETWEEN 100 AND 500     -- Price range filter
    AND p.stars >= 4.0                  -- Minimum rating filter
    
ORDER BY 
    -- Order by similarity score (most similar first)
    p.embedding <=> %s::vector
LIMIT 10;

-- Alternative version with parameterized filters:
SELECT 
    p."productId",
    p.product_description,
    p.category_name,
    p.price,
    p.stars,
    1 - (p.embedding <=> %s::vector) AS similarity
FROM 
    product_catalog p
WHERE 
    -- Parameterized minimum similarity
    1 - (p.embedding <=> %s::vector) >= %s  
    
    -- Optional category filter
    AND (%s IS NULL OR p.category_name = %s)
    
    -- Optional price range filter
    AND (p.price BETWEEN %s AND %s)
    
    -- Optional rating filter
    AND (p.stars >= %s)
ORDER BY 
    p.embedding <=> %s::vector
LIMIT %s;
```