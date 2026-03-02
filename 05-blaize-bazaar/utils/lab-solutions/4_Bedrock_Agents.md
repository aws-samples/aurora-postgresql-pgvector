```python
async def get_product_price(productId):
    async with await psycopg.AsyncConnection.connect(
        f"host={DB_HOST} dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}",
        row_factory=dict_row
    ) as aconn:
        async with aconn.cursor() as acur:
            await acur.execute(
                "SELECT \"productId\", product_description, price FROM bedrock_integration.product_catalog WHERE \"productId\" = %s;",
                (productId,)
            )
            return await acur.fetchone()
```