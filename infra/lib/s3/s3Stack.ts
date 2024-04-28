import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';

export class S3Stack extends cdk.Stack {
  public readonly graphsPlotsBucket: s3.Bucket;
  public readonly graphsBucket: s3.Bucket;
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    this.graphsPlotsBucket = new s3.Bucket(this, "graphsPlotsBucket");
    this.graphsBucket = new s3.Bucket(this, "graphsBucket");
  }
}
