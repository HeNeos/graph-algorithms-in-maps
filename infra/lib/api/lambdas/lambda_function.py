import json
import boto3
import os
import time

sfn_client = boto3.client('stepfunctions')
GRAPHS_STATE_MACHINE_ARN = os.environ["GRAPHS_STATE_MACHINE_ARN"]

def lambda_handler(event, _):
  if "queryStringParameters" not in event:
    return {
      "statusCode": 400,
      "body": json.dumps({"message": "Bad request"})
    }

  input_data = {"querystring": event["queryStringParameters"]}

  response = sfn_client.start_execution(
    stateMachineArn=GRAPHS_STATE_MACHINE_ARN,
    input=json.dumps(input_data)
  )

  execution_arn = response['executionArn']

  while True:
    execution_status = sfn_client.describe_execution(executionArn=execution_arn)['status']
    if execution_status in ['SUCCEEDED', 'FAILED', 'TIMED_OUT']:
      break
    time.sleep(3)

  execution_output = json.loads(sfn_client.describe_execution(executionArn=execution_arn)['output'])
  execution_output = execution_output.get("body", {})
  url = json.loads(execution_output)
  url = url.get("url")

  if url is None:
    return {
      "statusCode": 400,
      "body": json.dumps({"message": "Failed to generate a path"})
    }

  return {
    "statusCode": 302,
    "headers": {
      "Location": url
    }
  }
