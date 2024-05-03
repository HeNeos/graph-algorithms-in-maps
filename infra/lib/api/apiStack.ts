import * as cdk from 'aws-cdk-lib';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as apigw from 'aws-cdk-lib/aws-apigateway';
import { Construct } from 'constructs';

interface ApiStackProps extends cdk.StackProps {
  graphsStateMachine: sfn.StateMachine;
}

export class ApiStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: ApiStackProps) {
    super(scope, id, props);

    if (!props) throw new Error("Missing props");

    const graphsRestApi = new apigw.StepFunctionsRestApi(this, "graphsRestApi", {
      stateMachine: props.graphsStateMachine,
      deploy: true
    });
    // graphsRestApi.root.addMethod("GET", apigw.StepFunctionsIntegration.startExecution(props.graphsStateMachine, {
    //   timeout: cdk.Duration.minutes(1),
    //   querystring: true
    // }));
  }
}
