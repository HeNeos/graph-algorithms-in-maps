import * as cdk from 'aws-cdk-lib';
import * as dynamo from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';

export class DatabaseStack extends cdk.Stack {
  public readonly graphsDatabase: dynamo.Table;
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    this.graphsDatabase = new dynamo.Table(this, "graphsTable", {
      tableName: "graphsTable",
      billingMode: dynamo.BillingMode.PAY_PER_REQUEST,
      partitionKey: {name: "Country", type: dynamo.AttributeType.STRING},
      sortKey: {name: "City", type: dynamo.AttributeType.STRING},
    });
  }
}
