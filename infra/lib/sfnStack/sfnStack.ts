import * as cdk from 'aws-cdk-lib';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';
import { RustFunction } from 'cargo-lambda-cdk';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as dynamo from 'aws-cdk-lib/aws-dynamodb';
import * as path from 'path';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import * as logs from 'aws-cdk-lib/aws-logs';

interface LambdaStackProps extends cdk.StackProps {
  graphsPlotsBucket: s3.Bucket;
  graphsBucket: s3.Bucket;
  graphsDatabase: dynamo.Table;
}

export class SfnStack extends cdk.Stack {
  public readonly graphsStateMachine: sfn.StateMachine;
  constructor(scope: Construct, id: string, props: LambdaStackProps) {
    super(scope, id, props);

    const graphsPlotsBucket = props.graphsPlotsBucket;
    const graphsBucket = props.graphsBucket;
    const graphsDatabase = props.graphsDatabase;

    const getGraphsImage = lambda.DockerImageCode.fromImageAsset(__dirname, {
      buildArgs: {FUNCTION_NAME: "getGraph"},
      cmd: ["lambdas.getGraph.lambda_function.lambda_handler"]
    });
    const plotPathImage = lambda.DockerImageCode.fromImageAsset(__dirname, {
      buildArgs: {FUNCTION_NAME: "plotPath"}, 
      cmd: ["lambdas.plotPath.lambda_function.lambda_handler"]
    });

    const getGraphLambda = new lambda.DockerImageFunction(this, "getGraphLambda", {
      functionName: "getGraph",
      code: getGraphsImage,
      environment: {
        GRAPHS_BUCKET: graphsBucket.bucketName,
        PATHS_BUCKET: graphsPlotsBucket.bucketName,
        GRAPHS_TABLE_NAME: graphsDatabase.tableName
      },
      timeout: cdk.Duration.minutes(7),
      memorySize: 2048,
      ephemeralStorageSize: cdk.Size.mebibytes(1024)
    });

    graphsDatabase.grantReadWriteData(getGraphLambda);

    const plotPathLambda = new lambda.DockerImageFunction(this, "plotPathLambda", {
      functionName: "plotPath",
      code: plotPathImage,
      environment: {
        GRAPHS_BUCKET: graphsBucket.bucketName,
        PATHS_BUCKET: graphsPlotsBucket.bucketName,
        GRAPHS_TABLE_NAME: graphsDatabase.tableName
      },
      timeout: cdk.Duration.minutes(7),
      memorySize: 2048,
      ephemeralStorageSize: cdk.Size.mebibytes(1024)
    });

    graphsDatabase.grantReadData(plotPathLambda);

    const algorithmsLambda = new RustFunction(this, "algorithmsLambda", {
      manifestPath: path.join(__dirname, "../../algorithms/Cargo.toml"),
      runtime: "provided.al2023",
      environment: {
        GRAPHS_BUCKET: graphsBucket.bucketName,
        PATHS_BUCKET: graphsPlotsBucket.bucketName
      },
      timeout: cdk.Duration.seconds(15),
      memorySize: 2048
    });

    for (const graphLambda of [getGraphLambda, plotPathLambda, algorithmsLambda]){
      for (const bucket of [graphsPlotsBucket, graphsBucket]) {
        bucket.grantReadWrite(graphLambda);  
      }
      graphLambda.role?.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaBasicExecutionRole"))
    }

    const getGraphTask = new tasks.LambdaInvoke(this, "getGraphTask", {
      lambdaFunction: getGraphLambda,
      resultPath: "$.output",
      outputPath: "$.output.Payload"
    });
    const algorithmsTask = new tasks.LambdaInvoke(this, "algorithmTask", {
      lambdaFunction: algorithmsLambda,
      resultPath: "$.output",
      outputPath: "$.output.Payload"
    });
    const plotPathTask = new tasks.LambdaInvoke(this, "plotPathTask", {
      lambdaFunction: plotPathLambda,
      resultPath: "$.output",
      outputPath: "$.output.Payload"
    });

    const logGroup = new logs.LogGroup(this, "stateMachineLogGroup");

    const stateMachineDefinition = getGraphTask.next(algorithmsTask).next(plotPathTask);
    this.graphsStateMachine = new sfn.StateMachine(this, "graphsStateMachine", {
      definitionBody: sfn.DefinitionBody.fromChainable(stateMachineDefinition),
      timeout: cdk.Duration.minutes(15),
      stateMachineName: "GraphsAlgorithms",
      stateMachineType: sfn.StateMachineType.STANDARD,
      logs: {
        destination: logGroup,
        level: sfn.LogLevel.ALL,
        includeExecutionData: true
      },
    });
  }
}
