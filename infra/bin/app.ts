#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { StorageStack } from '../lib/storageStack/storageStack';
import { DatabaseStack } from '../lib/databaseStack/dabaseStack';
import { SfnStack } from '../lib/sfnStack/sfnStack';
import { ApiStack } from '../lib/apiStack/apiStack';

const app = new cdk.App();
const storageStack = new StorageStack(app, "StorageStack");
const databaseStack = new DatabaseStack(app, "DatabaseStack");
const sfnStack = new SfnStack(app, "SfnStack", {
  graphsPlotsBucket: storageStack.graphsPlotsBucket,
  graphsBucket: storageStack.graphsBucket,
  graphsDatabase: databaseStack.graphsDatabase
});
const apiStack = new ApiStack(app, "ApiStack", {
  graphsStateMachine: sfnStack.graphsStateMachine
});

app.synth();