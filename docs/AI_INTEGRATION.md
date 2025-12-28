# AI Integration Architecture

## Overview

Clarion supports **optional** AI/LLM integration to enhance categorization, labeling, and SGT naming. The AI integration is designed to be:
- **Optional** - Can be disabled entirely
- **Flexible** - Supports local models (Llama, Mistral) and cloud models (OpenAI, Anthropic)
- **Context-Aware** - Optional RAG (Retrieval-Augmented Generation) using database context
- **Fallback-Ready** - Gracefully degrades to rule-based labeling if AI unavailable

---

## Architecture

### AI Categorization Agent

```
┌─────────────────────────────────────────────────────────────┐
│              AI Categorization Agent                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Cluster Analysis                                          │
│    ↓                                                        │
│  ┌──────────────────────────────────────────────────┐      │
│  │          LLM Backend (Pluggable)                  │      │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐       │      │
│  │  │  Local   │  │  OpenAI  │  │Anthropic │       │      │
│  │  │ (Ollama) │  │   API    │  │   API    │       │      │
│  │  └──────────┘  └──────────┘  └──────────┘       │      │
│  └──────────────────────────────────────────────────┘      │
│    ↓                                                        │
│  ┌──────────────────────────────────────────────────┐      │
│  │        Optional RAG Context Builder               │      │
│  │  • Database context (similar clusters)            │      │
│  │  • Historical SGT assignments                     │      │
│  │  • Domain-specific knowledge                      │      │
│  └──────────────────────────────────────────────────┘      │
│    ↓                                                        │
│  Label & SGT Recommendations                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Use Cases

### 1. Cluster Labeling

**Input:** Cluster characteristics (behavior patterns, device types, communication patterns)

**AI Task:** Generate semantic label for the cluster

**Example:**
```
Input:
  - Cluster members: 150 endpoints
  - Communication: High outbound to servers (ports 443, 80)
  - Device types: 80% Windows laptops
  - AD Groups: Engineering, IT-Support
  - Traffic pattern: 9-5 workday pattern

AI Output:
  Label: "Engineering Workstations"
  Confidence: 0.92
  Reasoning: "Cluster shows typical workstation behavior with engineering 
              department association, regular business hours activity, and 
              standard web/application access patterns."
```

### 2. SGT Name Generation

**Input:** Cluster label, category, existing SGT names

**AI Task:** Suggest appropriate SGT name following naming conventions

**Example:**
```
Input:
  - Cluster label: "Engineering Workstations"
  - Category: "users"
  - Existing SGTs: ["Corp-Users", "IT-Staff", "Sales"]

AI Output:
  Suggested SGT Name: "Engineering-Users"
  Alternatives: ["Eng-Workstations", "Engineering-Team"]
  Reasoning: "Follows established naming pattern, clearly identifies 
              engineering department, distinct from existing SGTs"
```

### 3. Anomaly Detection

**Input:** Endpoint behavior that doesn't fit existing clusters

**AI Task:** Identify if this is a new device category or anomaly

**Example:**
```
Input:
  - New endpoint behavior
  - Communication: Very different from existing clusters
  - Identity: Unknown/No AD group

AI Output:
  Classification: "Potential New Device Category"
  Suggested Action: "Monitor for 24 hours before assigning SGT"
  Reasoning: "Behavior patterns suggest IoT device or specialized equipment"
```

### 4. Policy Justification

**Input:** SGACL policy rules

**AI Task:** Generate human-readable justification for policy recommendations

---

## LLM Backend Support

### Local Models (Ollama)

**Requirements:**
- Ollama installed and running
- Model downloaded (e.g., `ollama pull llama2`)

**Configuration:**
```yaml
ai:
  enabled: true
  provider: "local"
  local:
    model_type: "ollama"
    model_name: "llama2"  # or "mistral", "codellama", etc.
    base_url: "http://localhost:11434"
```

**Advantages:**
- No API costs
- Data stays local (privacy)
- No internet required

**Disadvantages:**
- Requires local GPU/CPU resources
- Lower performance than cloud models
- Model management overhead

### Local Models (Transformers)

**Requirements:**
- `transformers` library installed
- Sufficient RAM/VRAM for model

**Configuration:**
```yaml
ai:
  enabled: true
  provider: "local"
  local:
    model_type: "transformers"
    model_name: "meta-llama/Llama-2-7b-chat-hf"  # HuggingFace model
    device: "cuda"  # or "cpu"
```

### OpenAI (Cloud)

**Requirements:**
- OpenAI API key

**Configuration:**
```yaml
ai:
  enabled: true
  provider: "openai"
  openai:
    api_key: "${CLARION_OPENAI_API_KEY}"  # From environment
    model: "gpt-4-turbo-preview"
    temperature: 0.3
```

### Anthropic Claude (Cloud)

**Requirements:**
- Anthropic API key

**Configuration:**
```yaml
ai:
  enabled: true
  provider: "anthropic"
  anthropic:
    api_key: "${CLARION_ANTHROPIC_API_KEY}"  # From environment
    model: "claude-3-opus-20240229"
```

---

## RAG (Retrieval-Augmented Generation)

### Overview

Optional RAG enhances AI categorization by providing relevant context from:
- Historical cluster assignments
- Similar clusters and their labels
- Domain-specific knowledge (if provided)
- Customer-specific naming conventions

### When to Use RAG

- **Recommended:** When you want consistency with historical categorizations
- **Recommended:** When you have domain-specific terminology
- **Optional:** For basic categorization, RAG may not be necessary

### Implementation

```python
class RAGContextBuilder:
    """Build context for RAG from database."""
    
    def build_cluster_context(
        self, 
        cluster_features: Dict,
        cluster_members: List[str],
        limit: int = 50
    ) -> str:
        """
        Build context from similar historical clusters.
        
        Returns formatted context string for LLM prompt.
        """
        # Query database for similar clusters
        similar_clusters = self.db.query_similar_clusters(
            cluster_features, 
            limit=limit
        )
        
        # Format as context
        context = "Similar historical clusters:\n"
        for cluster in similar_clusters:
            context += f"- {cluster.label} (SGT: {cluster.sgt_name})\n"
            context += f"  Pattern: {cluster.description}\n"
        
        return context
```

---

## Prompt Engineering

### Cluster Labeling Prompt

```
You are a network security expert analyzing endpoint behavior clusters.

Cluster Characteristics:
- Member count: {member_count}
- Communication patterns: {communication_patterns}
- Device types: {device_types}
- AD Groups: {ad_groups}
- Traffic volume: {traffic_volume}
- Active hours: {active_hours}

{rag_context}  # If RAG enabled

Task: Generate a clear, concise label (2-4 words) for this cluster.

Consider:
1. Primary function (user workstation, server, IoT device, etc.)
2. Department/organizational unit if identifiable
3. Role or responsibility if clear

Format:
Label: <your label>
Reasoning: <brief explanation>
```

### SGT Name Generation Prompt

```
You are generating Security Group Tag (SGT) names for network segmentation.

Cluster Label: {cluster_label}
Category: {category}  # "users", "servers", "devices", "special"
Existing SGTs: {existing_sgts}

Naming Guidelines:
- Use kebab-case (e.g., "Engineering-Users")
- Be descriptive but concise (2-3 words max)
- Avoid duplicates
- Follow customer conventions if provided

Task: Suggest an appropriate SGT name.

Output:
Suggested Name: <name>
Alternatives: <name1>, <name2>
Reasoning: <brief explanation>
```

---

## Fallback Strategy

### When AI is Disabled

- Use rule-based semantic labeling (existing `SemanticLabeler`)
- Use template-based SGT naming (existing `SGTMapper`)
- No AI calls made

### When AI Fails

- Log error and continue without AI
- Fall back to rule-based labeling
- Don't block clustering pipeline

### Error Handling

```python
try:
    label = ai_agent.generate_label(cluster_features)
except AIServiceUnavailable:
    logger.warning("AI service unavailable, using rule-based labeling")
    label = rule_based_labeler.label(cluster_features)
except Exception as e:
    logger.error(f"AI error: {e}, using fallback")
    label = rule_based_labeler.label(cluster_features)
```

---

## Performance Considerations

### Latency

- **Local Models:** 1-5 seconds per request (depends on hardware)
- **Cloud Models:** 0.5-3 seconds per request (depends on model)
- **Caching:** Cache AI responses for similar clusters

### Cost

- **Local Models:** Free (compute cost only)
- **OpenAI GPT-4:** ~$0.01-0.03 per cluster analysis
- **Anthropic Claude:** ~$0.015-0.04 per cluster analysis

### Optimization

1. **Batch Processing:** Process multiple clusters in one request
2. **Caching:** Cache responses for similar clusters
3. **Selective AI:** Only use AI for ambiguous clusters
4. **Async Processing:** Don't block clustering pipeline

---

## Implementation Plan

### Phase 1: Core AI Agent

1. Create `AICategorizationAgent` class
2. Implement LLM backend abstraction
3. Support Ollama (local) backend
4. Implement basic cluster labeling

### Phase 2: Cloud Integration

1. Add OpenAI support
2. Add Anthropic support
3. Add configuration management
4. Add error handling and fallback

### Phase 3: RAG (Optional)

1. Implement RAG context builder
2. Add database queries for similar clusters
3. Integrate RAG into prompts
4. Make RAG optional via config

### Phase 4: Advanced Features

1. SGT name generation
2. Anomaly detection
3. Policy justification
4. Batch processing optimization

---

## Testing

### Unit Tests

- Test AI agent with mock LLM responses
- Test fallback to rule-based labeling
- Test configuration parsing

### Integration Tests

- Test with actual Ollama (if available)
- Test error handling (unavailable service)
- Test RAG context building

### Manual Testing

- Run clustering with AI enabled
- Compare AI labels vs rule-based labels
- Validate SGT name suggestions

---

## Security & Privacy

### Data Privacy

- **Local Models:** All data stays local
- **Cloud Models:** Cluster characteristics sent to API (no PII)
- **No Flow Data:** Only aggregated cluster features sent to AI

### API Keys

- Store in environment variables
- Never commit to repository
- Use secret management in production

### Content Filtering

- Filter sensitive information from prompts
- Sanitize cluster characteristics
- Don't include IP addresses or hostnames in prompts

---

## Future Enhancements

1. **Fine-tuning:** Fine-tune local model on customer data
2. **Multi-agent:** Multiple AI agents for different tasks
3. **Learning:** Learn from user corrections to improve labeling
4. **Custom Prompts:** Allow customers to customize prompts
5. **Evaluation Metrics:** Track AI accuracy vs rule-based labeling

