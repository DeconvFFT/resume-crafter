# Kubernetes Production Patterns

## Deployment Configuration

### Production-Ready Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-service
  labels:
    app: api-service
    version: v1
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: api-service
  template:
    metadata:
      labels:
        app: api-service
        version: v1
    spec:
      serviceAccountName: api-service
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
        - name: api
          image: myregistry/api-service:v1.2.3@sha256:abc123
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 8000
              protocol: TCP
          resources:
            requests:
              cpu: "100m"
              memory: "256Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: api-secrets
                  key: database-url
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 15
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 3
          lifecycle:
            preStop:
              exec:
                command: ["/bin/sh", "-c", "sleep 10"]
      terminationGracePeriodSeconds: 30
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app: api-service
                topologyKey: kubernetes.io/hostname
```

## Health Probes

| Probe | Purpose | Failure Action |
|-------|---------|----------------|
| Liveness | Is container running? | Restart container |
| Readiness | Can container serve traffic? | Remove from service |
| Startup | Has container started? | Block other probes |

```yaml
# Startup probe for slow-starting apps
startupProbe:
  httpGet:
    path: /health/startup
    port: 8000
  failureThreshold: 30
  periodSeconds: 10
```

## Pod Disruption Budget

Ensure minimum availability during maintenance:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-service-pdb
spec:
  minAvailable: 2  # or use maxUnavailable: 1
  selector:
    matchLabels:
      app: api-service
```

## Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-service-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-service
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15
```

## Network Policies

### Default Deny All
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

### Allow Specific Traffic
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-service-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api-service
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8000
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: database
      ports:
        - protocol: TCP
          port: 5432
    - to:  # Allow DNS
        - namespaceSelector: {}
      ports:
        - protocol: UDP
          port: 53
```

## RBAC

```yaml
# ServiceAccount
apiVersion: v1
kind: ServiceAccount
metadata:
  name: api-service
  namespace: production

---
# Role with minimal permissions
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: api-service-role
  namespace: production
rules:
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get", "list"]

---
# RoleBinding
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: api-service-binding
  namespace: production
subjects:
  - kind: ServiceAccount
    name: api-service
    namespace: production
roleRef:
  kind: Role
  name: api-service-role
  apiGroup: rbac.authorization.k8s.io
```

## ConfigMaps and Secrets

```yaml
# ConfigMap for non-sensitive config
apiVersion: v1
kind: ConfigMap
metadata:
  name: api-config
data:
  LOG_LEVEL: "info"
  CACHE_TTL: "300"

---
# External Secrets (with external-secrets operator)
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: api-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    kind: ClusterSecretStore
    name: aws-secrets-manager
  target:
    name: api-secrets
  data:
    - secretKey: database-url
      remoteRef:
        key: production/api/database
        property: url
```

## Ingress with TLS

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  tls:
    - hosts:
        - api.example.com
      secretName: api-tls
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: api-service
                port:
                  number: 8000
```

## Resource Quotas

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: production-quota
  namespace: production
spec:
  hard:
    requests.cpu: "20"
    requests.memory: "40Gi"
    limits.cpu: "40"
    limits.memory: "80Gi"
    pods: "50"
```

## Deployment Strategies

| Strategy | Use Case | Risk |
|----------|----------|------|
| Rolling | Default, zero-downtime | Gradual rollout |
| Recreate | Breaking changes, stateful | Brief downtime |
| Blue/Green | Full validation before switch | 2x resources |
| Canary | Gradual traffic shift | Complex setup |

### Blue/Green with Service Selector
```yaml
# Switch traffic by changing selector
apiVersion: v1
kind: Service
metadata:
  name: api-service
spec:
  selector:
    app: api-service
    version: v2  # Change from v1 to v2
  ports:
    - port: 80
      targetPort: 8000
```

## Production Checklist

- [ ] Resource requests and limits set
- [ ] Liveness and readiness probes configured
- [ ] Pod Disruption Budget defined
- [ ] Horizontal Pod Autoscaler configured
- [ ] Network Policies applied
- [ ] RBAC with least privilege
- [ ] Secrets externalized (not in manifests)
- [ ] Pod anti-affinity for HA
- [ ] Graceful shutdown handling
- [ ] Image pinned to digest
- [ ] Security context (non-root)
- [ ] Resource quotas per namespace
