# Load testing

Install Locust in a separate benchmark environment and run:

```bash
locust -f benchmarks/omniai/load/locustfile.py --host http://127.0.0.1:8090
```

Collect RPS, P50/P95/P99 latency and error rate. The repository does not contain
pre-filled performance numbers; results are valid only when produced on the
actual target machine with the exact service profile recorded.
