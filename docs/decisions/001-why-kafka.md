# ADR 001: Why Kafka for Job Ingestion

- Status: Accepted
- Date: 2026-04-25

## Context

The platform ingests job postings from multiple sources and needs to move those records through downstream processing in a way that supports:

- decoupling producers from consumers
- replaying historical events when downstream logic changes
- supporting more than one consumer over time
- fitting a data-platform style architecture rather than only request-response application flows

In this repository, the data pipeline already publishes job postings as events and a downstream consumer processes those events into analytics storage. The local development stack also includes Kafka and a consumer service.

## Decision

We use Kafka as the event backbone for job posting ingestion instead of RabbitMQ or a direct synchronous write from the pipeline into downstream storage.

## Options Considered

### Option 1: Kafka

Pros:

- strong fit for event streams and append-only ingestion
- supports replaying old messages, which is valuable for rebuilding downstream tables or reprocessing logic
- allows multiple consumers to read the same job posting stream independently
- aligns well with future data-engineering patterns such as bronze/silver/gold pipelines

Cons:

- more operational complexity than simpler queues
- can be heavy for small-scale projects
- adds infrastructure overhead in local and cloud environments

### Option 2: RabbitMQ

Pros:

- simpler mental model for many queue-based workflows
- good for task distribution and work queues
- lighter for classic producer-consumer application flows

Cons:

- less natural fit for replayable event streaming
- less aligned with log-based data platform patterns
- weaker fit for keeping job-posting events available for multiple downstream consumers over time

### Option 3: Direct Write from Pipeline to Database or BigQuery

Pros:

- simplest implementation path
- fewer moving parts
- easier to reason about at very small scale

Cons:

- tightly couples ingestion to downstream storage
- makes retries, replay, and reprocessing more awkward
- limits flexibility when adding new consumers or transformations later

## Why Kafka Was Chosen

Kafka was chosen because this project is closer to a data platform than a simple background-job application.

The important requirement is not only delivering a message once, but preserving a stream of job-posting events that downstream systems can consume independently. Kafka gives us a better fit for:

- replayable ingestion
- consumer decoupling
- future expansion into additional analytics or ML consumers
- a more realistic event-driven architecture for a portfolio project in data engineering

RabbitMQ would have been a valid option for task queues, but Kafka better matches the event-streaming and reprocessing needs of this platform.

## Tradeoffs Accepted

By choosing Kafka, we accept:

- a steeper operational footprint than RabbitMQ or direct writes
- extra setup in local development and future cloud deployment
- the possibility that Kafka is temporarily heavier than the current project scale strictly requires

This tradeoff is acceptable because the architectural benefits are directly aligned with the kind of system this project is intended to demonstrate.

## Consequences

Positive consequences:

- the ingestion pipeline and downstream consumers are more loosely coupled
- historical event replay is possible
- the architecture is easier to extend with new consumers
- the project better reflects industry event-streaming patterns in data engineering

Negative consequences:

- deployment and local setup are more complex
- debugging infrastructure issues is harder than in a direct-write design
- operating Kafka in production will require more care than a simpler queueing choice

## Notes

This decision does not claim Kafka is universally better than RabbitMQ. It is a fit-for-purpose choice based on this project’s event-streaming goals, multi-consumer potential, and data-platform orientation.
