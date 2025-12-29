# Collector Scalability Guide

## Current Scale Limitations

### Single Instance Capacity

**Current Implementation:**
- Single asyncio event loop (single-threaded async)
- Single UDP socket per port (NetFlow/IPFIX)
- In-memory batching (no persistence)
- Default batch size: 1000 records
- Default batch interval: 5 seconds
- Maximum throughput per instance: ~200 records/second (theoretical)

**Estimated Capacity per Instance:**
- **Light load:** ~100K flows/hour (28 flows/sec)
- **Medium load:** ~500K flows/hour (140 flows/sec)  
- **Heavy load:** ~1M flows/hour (280 flows/sec) - may hit limits

**Bottlenecks:**
1. UDP packet processing (asyncio loop)
2. Batch processing overhead
3. HTTP POST to backend (network latency)
4. Memory usage (grows with batch size)

---

## Scaling Strategies

### Option 1: Horizontal Scaling with SO_REUSEPORT (Recommended)

**How it works:**
- Multiple collector instances bind to the same UDP port using `SO_REUSEPORT`
- OS kernel load balances UDP packets across instances
- Each instance processes packets independently

**Pros:**
- True horizontal scaling
- OS-level load balancing (efficient)
- No single point of failure
- Linear scalability (2x instances ≈ 2x capacity)

**Cons:**
- Requires OS support (Linux 3.9+, modern kernels)
- Packet ordering not guaranteed (acceptable for NetFlow)
- Each switch IP must be hashed consistently (not an issue for NetFlow)

**Implementation:**
```python
# Enable SO_REUSEPORT for UDP socket
netflow_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
```

**Deployment:**
```bash
# Docker Compose - scale to 3 instances
docker-compose up -d --scale collector=3

# Kubernetes - scale deployment
kubectl scale deployment clarion-collector --replicas=3
```

---

### Option 2: Load Balancer in Front (For VMs/Containers)

**Architecture:**
```
Switches → Load Balancer (UDP) → Multiple Collector Instances → Backend
```

**Load Balancer Options:**
- **Linux IPVS** (kernel-level, high performance)
- **HAProxy** (UDP mode, stateless)
- **Nginx** (UDP stream module)
- **Cloud Load Balancers** (AWS ELB, GCP Load Balancer, Azure LB)

**Pros:**
- Works with any OS/kernel version
- Can use different ports for different collector instances
- More control over load balancing algorithm
- Health checks and failover

**Cons:**
- Additional component to manage
- Additional network hop (latency)
- Load balancer becomes potential bottleneck
- More complex configuration

---

### Option 3: Switch-Level Distribution

**Architecture:**
```
Switches → Direct to Different Collector Instances (different ports/IPs) → Backend
```

**How it works:**
- Configure different switches to send to different collector instances
- Use DNS round-robin or switch grouping

**Pros:**
- Simple implementation
- No load balancer needed
- Predictable distribution

**Cons:**
- Manual configuration per switch
- Not automatic failover
- Unbalanced if switch traffic varies

---

## Deployment Options

### Container Deployment (Recommended)

**Advantages:**
- ✅ Easy scaling (Kubernetes/Docker Compose)
- ✅ Consistent environments
- ✅ Resource limits and isolation
- ✅ Easy updates and rollbacks
- ✅ Health checks and auto-restart
- ✅ SO_REUSEPORT works well in containers

**Kubernetes Example:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: clarion-collector
spec:
  replicas: 3  # Scale horizontally
  selector:
    matchLabels:
      app: clarion-collector
  template:
    metadata:
      labels:
        app: clarion-collector
    spec:
      containers:
      - name: collector
        image: clarion-collector:latest
        ports:
        - containerPort: 2055
          protocol: UDP
        - containerPort: 4739
          protocol: UDP
        env:
        - name: CLARION_COLLECTOR_BACKEND_URL
          value: "http://clarion-backend:8000"
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

**Docker Compose:**
```yaml
services:
  collector:
    image: clarion-collector:latest
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
    ports:
      - "2055:2055/udp"
      - "4739:4739/udp"
```

---

### VM Deployment

**Advantages:**
- ✅ Full OS control
- ✅ Better for bare metal deployments
- ✅ Can optimize OS settings (kernel parameters)
- ✅ No container overhead

**Disadvantages:**
- ❌ Manual scaling (need to provision VMs)
- ❌ More complex updates
- ❌ Resource management less flexible
- ❌ Need orchestration tool (Ansible, Terraform)

**Best for:**
- Large-scale deployments (10+ instances)
- When container orchestration is not available
- High-performance requirements (dedicated resources)

---

## Performance Optimization

### Per-Instance Optimizations

1. **Increase Batch Size:**
   ```bash
   CLARION_COLLECTOR_BATCH_SIZE=5000  # Default: 1000
   ```
   - Reduces HTTP requests
   - More memory usage
   - Higher latency per record

2. **Decrease Batch Interval:**
   ```bash
   CLARION_COLLECTOR_BATCH_INTERVAL=2.0  # Default: 5.0 seconds
   ```
   - Lower latency
   - More frequent HTTP requests
   - Better for real-time processing

3. **Connection Pooling:**
   - Use persistent HTTP connections (already using httpx.AsyncClient)
   - Configure connection pool size
   - Enable HTTP/2 if backend supports

4. **Socket Buffer Sizes:**
   ```python
   # Increase UDP receive buffer (requires root/privileges)
   sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4194304)  # 4MB
   ```

5. **CPU Affinity:**
   - Pin collector process to specific CPUs
   - Reduce context switching
   - Better cache locality

---

## Capacity Planning

### Calculate Required Instances

**Formula:**
```
Instances = (Peak flows/sec) / (Instance capacity)
```

**Example:**
- Peak traffic: 10M flows/hour = 2,778 flows/sec
- Instance capacity: 250 flows/sec
- Required instances: 2,778 / 250 = **~12 instances**

**With Safety Margin (2x):**
```
Instances = (Peak flows/sec) / (Instance capacity) * 2
= 2,778 / 250 * 2 = ~22 instances
```

### Resource Requirements per Instance

| Load Level | CPU | Memory | Network | Notes |
|------------|-----|--------|---------|-------|
| Light (<100K/hr) | 0.1 cores | 128 MB | Low | Development/small networks |
| Medium (100K-1M/hr) | 0.25 cores | 256 MB | Moderate | Typical production |
| Heavy (1M-10M/hr) | 0.5 cores | 512 MB | High | Large enterprise |
| Very Heavy (>10M/hr) | 1+ cores | 1 GB+ | Very High | Scale horizontally instead |

---

## Monitoring & Scaling Decisions

### Key Metrics to Monitor

1. **Packet Processing:**
   - Packets received/sec
   - Packets dropped (if UDP buffer full)
   - Parse errors

2. **Batching:**
   - Batch size (average/max)
   - Batch processing time
   - Queue depth (pending records)

3. **Backend Communication:**
   - HTTP request rate
   - HTTP errors (5xx, timeouts)
   - Response time

4. **Resource Usage:**
   - CPU utilization
   - Memory usage
   - Network I/O

### Scaling Triggers

**Scale Up When:**
- CPU > 70% sustained
- Memory > 80%
- Packet drops > 1%
- Batch queue depth > 10,000 records
- HTTP errors > 5%

**Scale Down When:**
- CPU < 30% for 15+ minutes
- All metrics healthy
- Low packet rate

---

## Recommended Deployment Architecture

### Small Scale (< 1M flows/hour)
- **Instances:** 1-2 collectors
- **Deployment:** Docker Compose or single VM
- **Load Balancer:** Not needed (direct switch config)

### Medium Scale (1M - 10M flows/hour)
- **Instances:** 3-10 collectors
- **Deployment:** Kubernetes with SO_REUSEPORT
- **Load Balancer:** Optional (OS handles with SO_REUSEPORT)
- **Auto-scaling:** Based on CPU/memory metrics

### Large Scale (> 10M flows/hour)
- **Instances:** 10+ collectors
- **Deployment:** Kubernetes or VMs with load balancer
- **Load Balancer:** Required (HAProxy or cloud LB)
- **Auto-scaling:** Horizontal Pod Autoscaler (K8s) or VM auto-scaling
- **Regional Distribution:** Deploy collectors close to switches

---

## Implementation Roadmap

### Phase 1: Enable SO_REUSEPORT (Immediate)
- [ ] Add SO_REUSEPORT socket option
- [ ] Update documentation
- [ ] Test with multiple instances

### Phase 2: Kubernetes Deployment (Short-term)
- [ ] Create Kubernetes manifests
- [ ] Add resource limits
- [ ] Configure health checks
- [ ] Set up auto-scaling

### Phase 3: Metrics & Monitoring (Short-term)
- [ ] Add Prometheus metrics export
- [ ] Expose metrics endpoint
- [ ] Create Grafana dashboards
- [ ] Set up alerts

### Phase 4: Performance Tuning (Medium-term)
- [ ] Configurable socket buffer sizes
- [ ] HTTP connection pooling improvements
- [ ] Batch size/interval optimization
- [ ] CPU affinity options

### Phase 5: Advanced Features (Long-term)
- [ ] Flow aggregation/deduplication
- [ ] Rate limiting per switch
- [ ] Backpressure handling
- [ ] Persistence layer (Redis/Kafka for buffering)

