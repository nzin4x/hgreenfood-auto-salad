import os
import json
import logging
import boto3
from typing import Any, Dict

LOGGER = logging.getLogger()
if not LOGGER.handlers:
    logging.basicConfig(level=logging.INFO)
LOGGER.setLevel(logging.INFO)

def get_registration_status_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """
    Returns the current number of registered users and the maximum allowed.
    """
    LOGGER.info("=== GET REGISTRATION STATUS HANDLER STARTED ===")
    
    try:
        table_name = os.environ.get("CONFIG_TABLE_NAME", "HGreenFoodAutoReserve")
        max_users = int(os.environ.get("MAX_USERS", "10"))
        
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(table_name)

        # Scan for all user profiles whose PK starts with "USER#"
        # Note: Scan is inefficient for large tables, but acceptable for small user base (<100)
        from boto3.dynamodb.conditions import Attr

        filter_expr = Attr("PK").begins_with("USER#") & Attr("SK").eq("PROFILE")

        response = table.scan(
            FilterExpression=filter_expr,
            ProjectionExpression="userId"
        )

        items = response.get("Items", [])
        count = len(items)

        # Handle pagination if necessary (though unlikely for <100 users)
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                FilterExpression=filter_expr,
                ProjectionExpression="userId",
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items.extend(response.get("Items", []))
            count = len(items)
            
        LOGGER.info("Current user count: %d, Max users: %d", count, max_users)
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "count": count,
                "limit": max_users,
                "isFull": count >= max_users
            })
        }
        
    except Exception as e:
        LOGGER.error("Error getting registration status: %s", str(e), exc_info=True)
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"message": str(e)})
        }
