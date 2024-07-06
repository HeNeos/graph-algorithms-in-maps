import json
import boto3
import os
import time

from typing import Dict, Optional

sfn_client = boto3.client("stepfunctions")
GRAPHS_STATE_MACHINE_ARN = os.environ["GRAPHS_STATE_MACHINE_ARN"]


def lambda_handler(
    event: Dict[str, Dict[str, str]], _: Dict[str, str]
) -> Dict[str, int | str | Dict[str, str]]:
    if "queryStringParameters" not in event:
        body_message: Dict[str, str] = {"message": "Bad request"}
        return {"statusCode": 400, "body": json.dumps(body_message)}

    input_data: Dict[str, Dict[str, str]] = {
        "querystring": event["queryStringParameters"]
    }

    response = sfn_client.start_execution(
        stateMachineArn=GRAPHS_STATE_MACHINE_ARN, input=json.dumps(input_data)
    )

    execution_arn = response["executionArn"]

    while True:
        execution_status = sfn_client.describe_execution(executionArn=execution_arn)[
            "status"
        ]
        if execution_status in ["SUCCEEDED", "FAILED", "TIMED_OUT"]:
            break
        time.sleep(3)

    execution_output: Dict[str, str] = json.loads(
        sfn_client.describe_execution(executionArn=execution_arn)["output"]
    )
    json_execution: str = execution_output.get("body", "")
    json_output: Dict[str, str] = json.loads(json_execution)
    url: Optional[str] = json_output.get("url")

    if url is None:
        body_message = {"message": "Failed to generate a path"}
        return {
            "statusCode": 400,
            "body": json.dumps(body_message),
        }

    return {"statusCode": 302, "headers": {"Location": url}}
