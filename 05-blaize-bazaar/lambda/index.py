import json
import os
import asyncio
import psycopg
from psycopg.rows import dict_row
from decimal import Decimal

# Database connection parameters
DB_HOST = os.environ['DB_HOST']
DB_NAME = os.environ['DB_NAME']
DB_USER = os.environ['DB_USER']
DB_PASSWORD = os.environ['DB_PASSWORD']

# Custom JSON encoder to handle Decimal
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

async def get_products_inventory():
    async with await psycopg.AsyncConnection.connect(
        f"host={DB_HOST} dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}",
        row_factory=dict_row
    ) as aconn:
        async with aconn.cursor() as acur:
            await acur.execute("SELECT \"productId\", LEFT(product_description,100), stars, reviews, price, isbestseller, boughtinlastmonth, category_name, quantity FROM bedrock_integration.product_catalog where quantity in (0, 1, 2, 3, 25, 70, 90) ORDER BY \"productId\" LIMIT 20;")
            return await acur.fetchall()

async def get_product_price(productId):
    async with await psycopg.AsyncConnection.connect(
        f"host={DB_HOST} dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}",
        row_factory=dict_row
    ) as aconn:
        async with aconn.cursor() as acur:
            await acur.execute(
                # TO-DO: Implement the query
                # Hint: Return productId, product_description, and price
            )
            return await acur.fetchone()

async def restock_product(productId, quantity):
    async with await psycopg.AsyncConnection.connect(
        f"host={DB_HOST} dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}",
        row_factory=dict_row
    ) as aconn:
        async with aconn.cursor() as acur:
            try:
                # First, check if the product exists
                await acur.execute(
                    "SELECT \"productId\", quantity FROM bedrock_integration.product_catalog WHERE \"productId\" = %s;",
                    (productId,)
                )
                product = await acur.fetchone()
                
                if not product:
                    return {"status": "Failure", "error": f"Product with ID {productId} not found"}
                
                # Update the quantity
                await acur.execute(
                    "UPDATE bedrock_integration.product_catalog SET quantity = quantity + %s WHERE \"productId\" = %s RETURNING \"productId\", quantity;",
                    (quantity, productId)
                )
                result = await acur.fetchone()
                
                if result:
                    await aconn.commit()
                    return {"status": "Success", "productId": result['productId'], "newQuantity": result['quantity']}
                else:
                    await aconn.rollback()
                    return {"status": "Failure", "error": "Update operation did not return a result"}
            except Exception as e:
                await aconn.rollback()
                print(f"Error restocking product: {str(e)}")
                return {"status": "Failure", "error": str(e)}

async def async_handler(event, context):
    print("Received event: " + json.dumps(event))
    
    # Use get() method with a default value to avoid KeyError
    api_path = event.get('apiPath', '/UnknownPath')
    
    if api_path == "/GetProductsInventory":
        try:
            response_data = await get_products_inventory()
        except Exception as e:
            print(f"Error querying database: {str(e)}")
            response_data = {"error": "Failed to retrieve product inventory"}
    
    elif api_path == "/GetProductPrice":
        print(f"Processing GetProductPrice request. Full event: {json.dumps(event)}")
        try:
            productId = None
            if event.get('queryStringParameters'):
                productId = event['queryStringParameters'].get('productId')
            if not productId and event.get('body'):
                body = json.loads(event['body'])
                productId = body.get('productId')
                    
            print(f"Extracted productId: {productId}")
                    
            if not productId:
                print("productId not found in request")
                response_data = {"error": "Missing productId parameter"}
            else:
                response_data = await get_product_price(productId)
                print(f"get_product_price result: {json.dumps(response_data, cls=DecimalEncoder)}")
        except json.JSONDecodeError as je:
            print(f"JSON Decode Error: {str(je)}")
            response_data = {"error": "Invalid request format"}
        except Exception as e:
            print(f"Error processing GetProductPrice request: {str(e)}")
            response_data = {"error": "Failed to retrieve product price"}
            
    elif api_path == "/RestockProduct":
        print(f"Processing RestockProduct request. Full event: {json.dumps(event)}")
        try:
            # Extract parameters from requestBody
            request_body = event.get('requestBody', {})
            content = request_body.get('content', {})
            json_content = content.get('application/json', {})
            properties = json_content.get('properties', [])
        
            print(f"Properties: {properties}")
        
            # Convert the list of dictionaries to a single dictionary
            params = {item['name']: item['value'] for item in properties if 'name' in item and 'value' in item}
        
            print(f"Extracted params: {params}")
        
            # Get productId and quantity
            productId = params.get('productId')
            quantity = params.get('quantity')
        
            print(f"Extracted parameters: productId={productId}, quantity={quantity}")
        
            if not productId:
                raise ValueError("Missing productId parameter")
            if quantity is None:
                raise ValueError("Missing quantity parameter")
        
            try:
                quantity = int(quantity)
            except ValueError:
                raise ValueError(f"Invalid quantity: '{quantity}' is not an integer")
        
            if quantity <= 0:
                raise ValueError("Quantity must be a positive integer")
        
            response_data = await restock_product(productId, quantity)
            print(f"restock_product result: {json.dumps(response_data, cls=DecimalEncoder)}")
        except ValueError as ve:
            print(f"Validation error: {str(ve)}")
            response_data = {"error": str(ve)}
        except Exception as e:
            print(f"Error processing RestockProduct request: {str(e)}")
            response_data = {"error": f"Failed to restock product: {str(e)}"}
    else:
        response_data = {"message": f"Unknown API Path: {api_path}"}

    response_body = {
        'application/json': {
            'body': json.dumps(response_data, cls=DecimalEncoder)
        }
    }
    
    action_response = {
        'actionGroup': event.get('actionGroup', 'UnknownActionGroup'),
        'apiPath': api_path,
        'httpMethod': event.get('httpMethod', 'GET'),
        'httpStatusCode': 200,
        'responseBody': response_body
    }
    
    session_attributes = event.get('sessionAttributes', {})
    prompt_session_attributes = event.get('promptSessionAttributes', {})
    
    api_response = {
        'messageVersion': '1.0', 
        'response': action_response,
        'sessionAttributes': session_attributes,
        'promptSessionAttributes': prompt_session_attributes
    }
    
    print("Returning API response: " + json.dumps(api_response, cls=DecimalEncoder))
        
    return api_response

def lambda_handler(event, context):
    return asyncio.get_event_loop().run_until_complete(async_handler(event, context))
