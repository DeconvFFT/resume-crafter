# Guardrails & Anti-Hallucination

## Framework Selection

| Framework | Best For | Approach |
|-----------|----------|----------|
| NeMo Guardrails | Conversational AI, dialog control | Colang rules + LLM checks |
| Guardrails AI | Structured output validation | Pydantic + custom validators |
| Custom | Specific domain requirements | RAG grounding + fact-checking |

## NVIDIA NeMo Guardrails

### Installation
```bash
pip install nemoguardrails
```

### Configuration Structure
```
config/
├── config.yml          # Main configuration
├── prompts.yml         # Custom prompts
└── rails/
    ├── input.co        # Input rails (Colang)
    ├── output.co       # Output rails
    └── dialog.co       # Dialog flow rails
```

### config.yml
```yaml
models:
  - type: main
    engine: anthropic
    model: claude-sonnet-4-5

rails:
  input:
    flows:
      - check jailbreak
      - check toxicity
      - mask sensitive data
  
  output:
    flows:
      - self check facts
      - self check hallucination
      - check toxicity

  config:
    sensitive_data_detection:
      input:
        entities:
          - PERSON
          - EMAIL_ADDRESS
          - PHONE_NUMBER
          - SSN
    
    fact_checking:
      provider: alignscore  # or custom
```

### Colang Rails (input.co)
```colang
define user ask about competitors
  "What do you think about [competitor]?"
  "How does [competitor] compare?"
  "Is [competitor] better?"

define bot refuse competitor discussion
  "I focus on our products and services. 
   I'd be happy to help you with questions about what we offer."

define flow check competitor mentions
  user ask about competitors
  bot refuse competitor discussion
```

### Hallucination Detection
```yaml
# config.yml
rails:
  output:
    flows:
      - self check hallucination

prompts:
  - task: self_check_hallucination
    content: |
      Your task is to check if the bot's response contains any hallucinations.
      
      User message: {{ user_input }}
      Bot response: {{ bot_response }}
      Context provided: {{ context }}
      
      Check if the response:
      1. Contains information not supported by the context
      2. Makes claims that cannot be verified
      3. Invents facts, dates, or statistics
      
      Respond with "yes" if hallucination detected, "no" otherwise.
```

### Python Integration
```python
from nemoguardrails import RailsConfig, LLMRails

config = RailsConfig.from_path("./config")
rails = LLMRails(config)

# With guardrails
response = await rails.generate_async(
    messages=[{"role": "user", "content": "Tell me about our Q3 results"}]
)

# Check if blocked
if response.get("blocked"):
    print(f"Blocked by: {response.get('blocked_by')}")
else:
    print(response["content"])
```

## Guardrails AI

### Structured Validation
```python
from guardrails import Guard
from guardrails.validators import ValidLength, ValidRange, OneLine
from pydantic import BaseModel, Field

class ProductReview(BaseModel):
    summary: str = Field(
        validators=[ValidLength(min=10, max=200, on_fail="reask")]
    )
    rating: float = Field(
        validators=[ValidRange(min=1, max=5, on_fail="fix")]
    )
    pros: list[str]
    cons: list[str]

guard = Guard.from_pydantic(ProductReview)

result = guard(
    llm_api=openai.chat.completions.create,
    model="gpt-4o",
    messages=[{"role": "user", "content": "Review this product..."}]
)

if result.validation_passed:
    review = result.validated_output
else:
    print(f"Validation failed: {result.error}")
```

### Custom Validators
```python
from guardrails.validators import Validator, register_validator
from typing import Any

@register_validator(name="no_competitor_mentions", data_type="string")
class NoCompetitorMentions(Validator):
    def __init__(self, competitors: list[str], on_fail: str = "fix"):
        super().__init__(on_fail=on_fail)
        self.competitors = [c.lower() for c in competitors]
    
    def validate(self, value: Any, metadata: dict) -> dict:
        text_lower = value.lower()
        
        for competitor in self.competitors:
            if competitor in text_lower:
                return {
                    "outcome": "fail",
                    "error_message": f"Response mentions competitor: {competitor}",
                    "fix_value": self._redact(value, competitor)
                }
        
        return {"outcome": "pass"}
    
    def _redact(self, text: str, competitor: str) -> str:
        import re
        return re.sub(competitor, "[REDACTED]", text, flags=re.IGNORECASE)
```

## RAG-Based Fact Grounding

### Grounded Response Generation
```python
from typing import Optional

class GroundedAgent:
    def __init__(self, llm_client, retriever):
        self.client = llm_client
        self.retriever = retriever
    
    async def respond(
        self, 
        query: str, 
        require_citation: bool = True
    ) -> dict:
        # Retrieve relevant context
        docs = await self.retriever.search(query, k=5)
        context = "\n\n".join([d.content for d in docs])
        
        # Generate grounded response
        response = await self.client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2048,
            system=f"""Answer based ONLY on the provided context.
If the answer is not in the context, say "I don't have information about that."
Always cite your sources using [Source N] notation.

Context:
{context}""",
            messages=[{"role": "user", "content": query}]
        )
        
        answer = response.content[0].text
        
        # Verify citations exist
        if require_citation:
            verified = await self._verify_citations(answer, docs)
            if not verified["all_valid"]:
                answer = await self._regenerate_with_valid_citations(
                    query, context, verified["invalid_claims"]
                )
        
        return {
            "answer": answer,
            "sources": docs,
            "grounded": True
        }
    
    async def _verify_citations(
        self, 
        answer: str, 
        docs: list
    ) -> dict:
        """Verify that cited claims actually appear in sources."""
        verification = await self.client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": f"""Verify each claim in this answer is supported by the sources.

Answer: {answer}

Sources:
{[d.content for d in docs]}

List any claims NOT supported by sources."""
            }]
        )
        
        unsupported = verification.content[0].text
        return {
            "all_valid": "none" in unsupported.lower() or unsupported.strip() == "",
            "invalid_claims": unsupported
        }
```

### Confidence Scoring
```python
class ConfidenceScorer:
    def __init__(self, llm_client):
        self.client = llm_client
    
    async def score(
        self, 
        question: str, 
        answer: str, 
        context: Optional[str] = None
    ) -> dict:
        prompt = f"""Rate the confidence of this answer on a scale of 0-1.

Question: {question}
Answer: {answer}
{"Context: " + context if context else ""}

Consider:
- Factual accuracy (is it verifiable?)
- Completeness (does it fully answer?)
- Hedging language (does it express uncertainty?)
- Specificity (are claims specific or vague?)

Respond with JSON: {{"confidence": 0.X, "reasoning": "..."}}"""

        response = await self.client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        import json
        return json.loads(response.content[0].text)
```

## Multi-Layer Guardrails

### Complete Pipeline
```python
class GuardedAgent:
    def __init__(self, llm_client, retriever, config: dict):
        self.client = llm_client
        self.retriever = retriever
        self.config = config
    
    async def respond(self, user_input: str) -> dict:
        # Layer 1: Input validation
        input_check = await self._check_input(user_input)
        if not input_check["safe"]:
            return {"blocked": True, "reason": input_check["reason"]}
        
        # Layer 2: RAG grounding
        context = await self._get_context(user_input)
        
        # Layer 3: Generate with constraints
        response = await self._generate(user_input, context)
        
        # Layer 4: Output validation
        output_check = await self._check_output(response, context)
        if not output_check["valid"]:
            # Regenerate with feedback
            response = await self._regenerate(
                user_input, context, output_check["issues"]
            )
        
        # Layer 5: Confidence check
        confidence = await self._score_confidence(
            user_input, response, context
        )
        
        if confidence["score"] < self.config["min_confidence"]:
            response = self._add_uncertainty_disclaimer(response)
        
        return {
            "response": response,
            "confidence": confidence["score"],
            "sources": context.sources if context else []
        }
    
    async def _check_input(self, text: str) -> dict:
        """Check for jailbreaks, PII, off-topic."""
        # Use NeMo or custom checks
        pass
    
    async def _check_output(self, response: str, context) -> dict:
        """Verify factual accuracy, no hallucinations."""
        pass
```

## Best Practices

1. **Layer defenses**: Input → Generation → Output → Confidence
2. **Ground in sources**: Always retrieve context before generating
3. **Verify claims**: Cross-check generated facts against sources
4. **Express uncertainty**: Add disclaimers for low-confidence answers
5. **Monitor and iterate**: Log blocked content, refine rules
6. **Test adversarially**: Regularly probe for bypasses
