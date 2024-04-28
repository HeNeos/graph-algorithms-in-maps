import * as cdk from 'aws-cdk-lib';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';
import { RustFunction } from 'cargo-lambda-cdk';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as dynamo from 'aws-cdk-lib/aws-dynamodb';
import * as path from 'path';
import { LambdaAction } from 'aws-cdk-lib/aws-cloudwatch-actions';

interface LambdaStackProps extends cdk.StackProps {
  graphsPlotsBucket?: s3.Bucket;
  graphsBucket?: s3.Bucket;
  graphsDatabase?: dynamo.Table;
}

export class SfnStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: LambdaStackProps) {
    super(scope, id, props);

    const graphsPlotsBucket = props?.graphsPlotsBucket;
    const graphsBucket = props?.graphsBucket;
    const graphsDatabase = props?.graphsDatabase;

    if (!graphsBucket || !graphsPlotsBucket) throw new Error("Missing bucket props");
    if (!graphsDatabase) throw new Error("Missing database prop");

    const getGraphsImage = lambda.DockerImageCode.fromImageAsset(path.join(__dirname, "./lambdas/getGraph"));
    const plotPathImage = lambda.DockerImageCode.fromImageAsset(path.join(__dirname, "./lambdas/plotPath"));

    const getGraphLambda = new lambda.DockerImageFunction(this, "getGraphLambda", {
      functionName: "getGraph",
      code: getGraphsImage,
      environment: {
        GRAPHS_BUCKET: graphsBucket.bucketName,
        PATHS_BUCKET: graphsPlotsBucket.bucketName,
        GRAPHS_TABLE_NAME: graphsDatabase.tableName
      },
      timeout: cdk.Duration.minutes(4),
      memorySize: 2048,
      ephemeralStorageSize: cdk.Size.mebibytes(2048)
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
      timeout: cdk.Duration.minutes(4)
    });

    graphsDatabase.grantReadData(plotPathLambda);

    const algorithmsLambda = new RustFunction(this, "algorithmsLambda", {
      manifestPath: path.join(__dirname, "../../algorithms/Cargo.toml"),
      runtime: "provided.al2023",
      environment: {
        GRAPHS_BUCKET: graphsBucket.bucketName,
        PATHS_BUCKET: graphsPlotsBucket.bucketName
      }
    });

    for (const graphLambda of [getGraphLambda, plotPathLambda, algorithmsLambda]){
      for (const bucket of [graphsPlotsBucket, graphsBucket]) {
        bucket.grantReadWrite(graphLambda);  
      }
      graphLambda.role?.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaBasicExecutionRole"))
    }
  }
}
