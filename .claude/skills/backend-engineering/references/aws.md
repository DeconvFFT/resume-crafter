# AWS Deployment Patterns

## ECS vs EKS Decision

| Factor | ECS | EKS |
|--------|-----|-----|
| Control plane cost | Free | $73/month/cluster |
| Operational complexity | Lower | Higher |
| Multi-cloud portability | No | Yes |
| Learning curve | AWS-native | Kubernetes expertise |

**Choose ECS** for AWS-native workloads, smaller teams.
**Choose EKS** for multi-cloud, existing K8s expertise.

## ECS Fargate with CDK

```typescript
import * as cdk from 'aws-cdk-lib';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as ecsPatterns from 'aws-cdk-lib/aws-ecs-patterns';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';

export class ApiStack extends cdk.Stack {
  constructor(scope: cdk.App, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const cluster = new ecs.Cluster(this, 'Cluster', {
      containerInsights: true,
    });

    const repo = ecr.Repository.fromRepositoryName(
      this, 'Repo', 'api-service'
    );

    const dbSecret = secretsmanager.Secret.fromSecretNameV2(
      this, 'DbSecret', 'production/db'
    );

    const service = new ecsPatterns.ApplicationLoadBalancedFargateService(
      this, 'Service',
      {
        cluster,
        memoryLimitMiB: 512,
        cpu: 256,
        desiredCount: 2,
        taskImageOptions: {
          image: ecs.ContainerImage.fromEcrRepository(repo, 'latest'),
          containerPort: 8000,
          secrets: {
            DATABASE_URL: ecs.Secret.fromSecretsManager(dbSecret, 'url'),
          },
          environment: {
            LOG_LEVEL: 'info',
          },
        },
        capacityProviderStrategies: [
          { capacityProvider: 'FARGATE_SPOT', weight: 2 },
          { capacityProvider: 'FARGATE', weight: 1 },
        ],
        circuitBreaker: { rollback: true },
        healthCheckGracePeriod: cdk.Duration.seconds(60),
      }
    );

    // Auto-scaling
    const scaling = service.service.autoScaleTaskCount({
      minCapacity: 2,
      maxCapacity: 20,
    });

    scaling.scaleOnCpuUtilization('CpuScaling', {
      targetUtilizationPercent: 70,
      scaleInCooldown: cdk.Duration.seconds(300),
      scaleOutCooldown: cdk.Duration.seconds(60),
    });

    scaling.scaleOnRequestCount('RequestScaling', {
      requestsPerTarget: 1000,
      targetGroup: service.targetGroup,
    });
  }
}
```

## Lambda Optimization

### Python Lambda with Powertools
```python
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger(service="payment-service")
tracer = Tracer()
metrics = Metrics(namespace="Payments")

@metrics.log_metrics(capture_cold_start_metric=True)
@tracer.capture_lambda_handler
@logger.inject_lambda_context
def handler(event: dict, context: LambdaContext) -> dict:
    logger.info("Processing payment", extra={"order_id": event.get("order_id")})
    
    with tracer.capture_method():
        result = process_payment(event)
    
    metrics.add_metric(name="PaymentProcessed", unit=MetricUnit.Count, value=1)
    
    return {
        "statusCode": 200,
        "body": json.dumps(result)
    }
```

### Lambda Best Practices
- **Memory sizing**: CPU scales with memory. Use AWS Lambda Power Tuning
- **ARM/Graviton2**: 20% cost reduction, often better performance
- **Provisioned concurrency**: Eliminates cold starts for critical paths
- **SnapStart (Java)**: 90% cold start reduction

### Lambda with SQS
```typescript
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as lambdaEventSources from 'aws-cdk-lib/aws-lambda-event-sources';

const queue = new sqs.Queue(this, 'OrderQueue', {
  visibilityTimeout: cdk.Duration.seconds(300),
  deadLetterQueue: {
    queue: dlq,
    maxReceiveCount: 3,
  },
});

const processor = new lambda.Function(this, 'Processor', {
  runtime: lambda.Runtime.PYTHON_3_12,
  architecture: lambda.Architecture.ARM_64,
  handler: 'handler.main',
  code: lambda.Code.fromAsset('lambda'),
  memorySize: 256,
  timeout: cdk.Duration.seconds(30),
  reservedConcurrentExecutions: 10,
});

processor.addEventSource(new lambdaEventSources.SqsEventSource(queue, {
  batchSize: 10,
  maxBatchingWindow: cdk.Duration.seconds(5),
  reportBatchItemFailures: true,
}));
```

## API Gateway

### REST vs HTTP API

| Feature | REST API | HTTP API |
|---------|----------|----------|
| Cost | $3.50/million | $1.00/million |
| Latency | ~29ms | ~10ms |
| WAF | Yes | No |
| Caching | Yes | No |
| Request validation | Yes | No |

### HTTP API with JWT Auth
```typescript
import * as apigatewayv2 from 'aws-cdk-lib/aws-apigatewayv2';
import * as integrations from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import * as authorizers from 'aws-cdk-lib/aws-apigatewayv2-authorizers';

const httpApi = new apigatewayv2.HttpApi(this, 'HttpApi', {
  corsPreflight: {
    allowHeaders: ['Authorization', 'Content-Type'],
    allowMethods: [apigatewayv2.CorsHttpMethod.ANY],
    allowOrigins: ['https://example.com'],
  },
});

const jwtAuthorizer = new authorizers.HttpJwtAuthorizer(
  'JwtAuthorizer',
  'https://cognito-idp.us-east-1.amazonaws.com/us-east-1_xxx',
  {
    jwtAudience: ['api'],
  }
);

httpApi.addRoutes({
  path: '/orders',
  methods: [apigatewayv2.HttpMethod.GET],
  integration: new integrations.HttpLambdaIntegration('OrdersIntegration', ordersLambda),
  authorizer: jwtAuthorizer,
});
```

## EventBridge

```typescript
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';

const bus = new events.EventBus(this, 'OrdersBus', {
  eventBusName: 'orders',
});

// Rule with content filtering
new events.Rule(this, 'HighValueOrders', {
  eventBus: bus,
  eventPattern: {
    source: ['com.orders'],
    detailType: ['OrderCreated'],
    detail: {
      amount: [{ numeric: ['>', 1000] }],
    },
  },
  targets: [
    new targets.LambdaFunction(highValueHandler),
    new targets.SqsQueue(auditQueue),
  ],
});

// Archive for replay
new events.Archive(this, 'OrdersArchive', {
  sourceEventBus: bus,
  eventPattern: { source: ['com.orders'] },
  retention: cdk.Duration.days(30),
});
```

## Cost Optimization

| Strategy | Savings | Best For |
|----------|---------|----------|
| Graviton/ARM | 20-40% | ECS, Lambda, RDS |
| Spot instances | 50-90% | Fault-tolerant workloads |
| Savings Plans | Up to 66% | Steady-state compute |
| Reserved Instances | Up to 72% | Predictable workloads |

### Fargate Spot Strategy
```typescript
capacityProviderStrategies: [
  { capacityProvider: 'FARGATE_SPOT', weight: 3 },  // 75% Spot
  { capacityProvider: 'FARGATE', weight: 1 },       // 25% On-Demand fallback
]
```

## Secrets Management

```typescript
// Create secret
const dbSecret = new secretsmanager.Secret(this, 'DbSecret', {
  secretName: 'production/db',
  generateSecretString: {
    secretStringTemplate: JSON.stringify({ username: 'admin' }),
    generateStringKey: 'password',
    excludePunctuation: true,
  },
});

// Rotate secret
dbSecret.addRotationSchedule('Rotation', {
  automaticallyAfter: cdk.Duration.days(30),
  rotationLambda: rotationLambda,
});

// Reference in ECS
secrets: {
  DB_PASSWORD: ecs.Secret.fromSecretsManager(dbSecret, 'password'),
}
```

## Monitoring Stack

```typescript
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as sns from 'aws-cdk-lib/aws-sns';

const dashboard = new cloudwatch.Dashboard(this, 'ApiDashboard');

dashboard.addWidgets(
  new cloudwatch.GraphWidget({
    title: 'Latency',
    left: [service.service.metricCpuUtilization()],
    right: [service.loadBalancer.metric('TargetResponseTime')],
  })
);

// Alarm
const alarm = new cloudwatch.Alarm(this, 'HighLatencyAlarm', {
  metric: service.loadBalancer.metric('TargetResponseTime', {
    statistic: 'p99',
    period: cdk.Duration.minutes(5),
  }),
  threshold: 1,
  evaluationPeriods: 3,
  comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
});

alarm.addAlarmAction(new cw_actions.SnsAction(alertsTopic));
```

## Production Checklist

- [ ] Multi-AZ deployment
- [ ] Auto-scaling configured
- [ ] Secrets in Secrets Manager
- [ ] CloudWatch alarms set
- [ ] X-Ray tracing enabled
- [ ] VPC with private subnets
- [ ] Security groups least-privilege
- [ ] IAM roles with minimal permissions
- [ ] Backup strategy defined
- [ ] Cost allocation tags applied
