#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { S3Stack } from '../lib/s3/s3Stack';
import { DatabaseStack } from '../lib/database/dabaseStack';
import { SfnStack } from '../lib/sfn/sfnStack';

const app = new cdk.App();
const s3Stack = new S3Stack(app, "S3Stack");
const databaseStack = new DatabaseStack(app, "DatabaseStack");
const sfnStack = new SfnStack(app, "SfnStack", {
  graphsPlotsBucket: s3Stack.graphsPlotsBucket,
  graphsBucket: s3Stack.graphsBucket,
  graphsDatabase: databaseStack.graphsDatabase
});

app.synth();