import * as cdk from 'aws-cdk-lib';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as python from '@aws-cdk/aws-lambda-python-alpha';
import * as path from 'path';
import { Construct } from 'constructs';

interface ApiStackProps extends cdk.StackProps {
  graphsStateMachine: sfn.StateMachine;
}

export class ApiStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: ApiStackProps) {
    super(scope, id, props);

    if (!props) throw new Error("Missing props");

    // const graphsRestApi = new apigw.StepFunctionsRestApi(this, "graphsRestApi", {
    //   stateMachine: props.graphsStateMachine,
    //   deploy: true
    // });
    // graphsRestApi.root.addMethod("GET", apigw.StepFunctionsIntegration.startExecution(props.graphsStateMachine, {
    //   timeout: cdk.Duration.minutes(1),
    //   querystring: true
    // }));

    const graphsLambdaUrl = new python.PythonFunction(this, "graphsLambdaUrl", {
      runtime: lambda.Runtime.PYTHON_3_10,
      handler: "lambda_handler",
      timeout: cdk.Duration.minutes(5),
      entry: path.join(__dirname, "lambdas"),
      index: "lambda_function.py",
      environment: {
        "GRAPHS_STATE_MACHINE_ARN": props.graphsStateMachine.stateMachineArn
      }
    });

    const graphsUrl = graphsLambdaUrl.addFunctionUrl({
      authType: lambda.FunctionUrlAuthType.NONE
    });

    props.graphsStateMachine.grantStartExecution(graphsLambdaUrl);
    props.graphsStateMachine.grantTaskResponse(graphsLambdaUrl);
    props.graphsStateMachine.grantRead(graphsLambdaUrl);

    new cdk.CfnOutput(this, "graphsUrl", {value: graphsUrl.url})

  }
}
