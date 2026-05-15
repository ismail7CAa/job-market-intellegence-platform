# ADR 005: Why GitHub Actions and GHCR for Deployment

- Status: Accepted
- Date: 2026-05-16

## Context

The project needs a repeatable way to build the application container and deploy it to the EC2 demo host. The code already lives in GitHub, and the repository includes a Dockerfile.

The deployment workflow should:

- run tests before deployment
- build the same container image that will run on EC2
- avoid manually copying source code to the server
- avoid adding another paid registry or deployment service
- stay easy to explain in a portfolio review

## Decision

Use GitHub Actions for CI/CD and GitHub Container Registry (GHCR) for Docker images.

The workflow:

1. checks out the repository
2. runs tests
3. builds the Docker image
4. pushes the image to GHCR
5. SSHes into the EC2 host
6. pulls the new image
7. restarts Docker Compose

## Options Considered

### Option 1: GitHub Actions and GHCR

Pros:

- integrated with the repository
- no extra registry account needed
- clear CI/CD story
- works well with Docker Compose on EC2
- avoids manually building images on the server

Cons:

- requires GitHub secrets setup
- requires GHCR permissions to be configured correctly
- SSH deployment is simpler than a full deployment platform but less sophisticated

### Option 2: Build Directly on EC2

Pros:

- fewer moving parts
- no external container registry required
- easy for quick experiments

Cons:

- slower and less reproducible
- consumes resources on the small EC2 instance
- mixes build and runtime responsibilities
- weaker CI/CD story

### Option 3: AWS ECR and CodeDeploy or ECS

Pros:

- AWS-native deployment path
- stronger production integration
- better fit for ECS later

Cons:

- adds more AWS setup
- not needed for the one-EC2 demo
- can introduce more cost and IAM complexity

## Why GitHub Actions and GHCR Were Chosen

GitHub Actions and GHCR fit the current project stage because they keep the deployment close to the repository and avoid unnecessary AWS services.

They also provide a professional portfolio signal: tests run before the image is deployed, and the EC2 host only pulls a built artifact.

## Tradeoffs Accepted

By using GitHub Actions over a full AWS-native deployment pipeline, we accept:

- SSH-based deployment
- dependency on GitHub secrets
- less advanced rollout control than ECS or CodeDeploy

Those tradeoffs are acceptable for a single-host demo.

## Consequences

Positive consequences:

- repeatable image builds
- cleaner EC2 host
- simple CI/CD explanation
- no separate registry cost

Negative consequences:

- GitHub secret setup must be correct
- future production deployment may move image hosting to ECR

