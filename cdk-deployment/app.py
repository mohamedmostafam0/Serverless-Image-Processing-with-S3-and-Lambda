#!/usr/bin/env python3
import aws_cdk as cdk

from cdk_deployment.cdk_deployment_stack import CdkDeploymentStack


app = cdk.App()
CdkDeploymentStack(app, "CdkDeploymentStack")

app.synth()