# Go Realtime Gateway

A small Go/chi service for learning high-concurrency SSE fan-out and NATS event
bridging. It deliberately drops events for slow local subscribers rather than
blocking the whole fan-out path; durable delivery belongs to NATS/JetStream.

Upstreams: `go-chi/chi` (MIT) and `nats.go` (Apache-2.0).
