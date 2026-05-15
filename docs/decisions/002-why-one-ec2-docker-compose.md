# ADR 002: Why One EC2 Instance with Docker Compose for the Portfolio Demo

- Status: Accepted
- Date: 2026-05-16

## Context

The project needs a public deployment for portfolio review, but the goal is to keep the AWS path simple, understandable, and low cost. The repository includes production-oriented scaffolding for ECS, Terraform, Kubernetes, RDS, and other managed resources, but those services are not necessary for a first live demo and can create ongoing AWS charges.

For this stage, the platform needs to run:

- one FastAPI application
- one Postgres database
- a small reproducible demo dataset
- health checks and simple restart behavior
- a deployment process that can be explained clearly to reviewers

## Decision

Use one AWS EC2 instance running Docker Compose as the default public deployment path.

The EC2 host runs:

- the FastAPI app container
- a local Postgres container
- a persistent Docker volume for database storage

GitHub Actions can still build and push the application image to GHCR, and deployment can restart the containers on the EC2 host.

## Options Considered

### Option 1: One EC2 Instance with Docker Compose

Pros:

- lowest operational complexity for a first portfolio demo
- easy to inspect, SSH into, and debug
- avoids RDS, ECS, ALB, NAT Gateway, and Kubernetes costs
- maps closely to the local Docker Compose workflow
- enough capacity for a small FastAPI demo

Cons:

- not highly available
- no managed database backups
- limited scaling story
- requires manual host maintenance

### Option 2: ECS Fargate with RDS and an Application Load Balancer

Pros:

- closer to a production cloud architecture
- managed task scheduling
- easier path to scaling and deployment hardening
- RDS provides managed database operations

Cons:

- introduces multiple paid managed services
- more networking and IAM complexity
- overkill for a small portfolio demo
- harder to explain quickly during review

### Option 3: Kubernetes

Pros:

- strong fit for complex multi-service systems
- portable orchestration model
- useful for demonstrating platform engineering knowledge

Cons:

- much too heavy for the current deployment need
- adds cluster management complexity
- can distract from the actual data/ML platform work

## Why One EC2 Was Chosen

The first public deployment should prove the product works, not prove that the infrastructure is maximal.

One EC2 instance with Docker Compose is enough to show:

- the API running publicly
- the German market demo landing page
- Postgres-backed service startup
- containerized deployment
- CI/CD image flow through GitHub Actions and GHCR

This gives a clean portfolio story while keeping the expensive production path optional.

## Tradeoffs Accepted

By using one EC2 host, we accept:

- no high availability
- no automatic horizontal scaling
- host-level responsibility for Docker, disk usage, and security updates
- a simpler database persistence model than managed RDS

Those tradeoffs are acceptable because this deployment is for a portfolio demo, not a production SaaS workload.

## Consequences

Positive consequences:

- lower cost risk
- faster deployment
- easier debugging
- clearer demo architecture

Negative consequences:

- limited resilience
- manual operational care
- future production deployment will need additional hardening

