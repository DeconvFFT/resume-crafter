# Structured Outputs with Pydantic

## Instructor Library

Instructor provides reliable structured extraction from LLMs with automatic validation and retries.

### Basic Usage
```python
import instructor
from pydantic import BaseModel, Field
from typing import Optional

class User(BaseModel):
    name: str = Field(description="User's full name")
    age: int = Field(ge=0, le=150, description="User's age")
    email: Optional[str] = Field(default=None, description="Email address")

# Multi-provider support
client = instructor.from_provider("anthropic/claude-sonnet-4-5")
# or: instructor.from_provider("openai/gpt-4o")
# or: instructor.from_provider("ollama/llama3")

user = client.create(
    response_model=User,
    messages=[{"role": "user", "content": "Extract: John Doe, 30 years old, john@example.com"}],
    max_retries=3
)

print(user)  # User(name='John Doe', age=30, email='john@example.com')
```

### Complex Nested Structures
```python
from pydantic import BaseModel
from typing import List, Literal
from enum import Enum

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Task(BaseModel):
    title: str
    description: str
    priority: Priority
    assignee: Optional[str] = None

class Project(BaseModel):
    name: str
    tasks: List[Task]
    deadline: Optional[str] = None

project = client.create(
    response_model=Project,
    messages=[{
        "role": "user",
        "content": """
        Project: Website Redesign
        - Task: Update homepage (high priority, assigned to Alice)
        - Task: Fix mobile layout (medium priority)
        - Deadline: March 2025
        """
    }]
)
```

### Streaming Partial Objects
```python
from instructor import Partial

# Stream partial results as they're generated
for partial in client.create(
    response_model=Partial[Project],
    messages=[{"role": "user", "content": "..."}],
    stream=True
):
    print(partial)
    # Project(name='Website...', tasks=None)
    # Project(name='Website Redesign', tasks=[Task(...)])
    # ... progressively more complete
```

### Custom Validators
```python
from pydantic import BaseModel, field_validator, model_validator

class Analysis(BaseModel):
    summary: str
    confidence: float
    sources: List[str]
    
    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        return v
    
    @field_validator("sources")
    @classmethod
    def validate_sources(cls, v):
        if len(v) < 1:
            raise ValueError("At least one source required")
        return v
    
    @model_validator(mode="after")
    def validate_model(self):
        if self.confidence < 0.5 and len(self.sources) < 3:
            raise ValueError("Low confidence requires more sources")
        return self
```

### LLM-Powered Validation
```python
from instructor import llm_validator
from typing import Annotated
from pydantic import BeforeValidator

class ContentModeration(BaseModel):
    content: Annotated[
        str,
        BeforeValidator(
            llm_validator(
                """Content must be:
                1. Professional and appropriate
                2. Free of harmful or offensive language
                3. Factually accurate where verifiable
                """,
                client=client
            )
        )
    ]
```

## Anthropic Native Structured Outputs

### Tool-Based Extraction
```python
import anthropic

client = anthropic.Anthropic()

# Define schema as tool
extraction_tool = {
    "name": "extract_entities",
    "description": "Extract structured entities from text",
    "input_schema": {
        "type": "object",
        "properties": {
            "people": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "role": {"type": "string"}
                    },
                    "required": ["name"]
                }
            },
            "organizations": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": ["people", "organizations"]
    }
}

response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    tools=[extraction_tool],
    tool_choice={"type": "tool", "name": "extract_entities"},
    messages=[{
        "role": "user",
        "content": "Extract entities: John Smith, CEO of Acme Corp, met with Jane Doe from Tech Inc."
    }]
)

# Parse tool use result
for block in response.content:
    if block.type == "tool_use":
        entities = block.input  # Already parsed JSON
```

## OpenAI Native Structured Outputs

```python
from openai import OpenAI
from pydantic import BaseModel

client = OpenAI()

class MathSolution(BaseModel):
    steps: List[str]
    final_answer: float
    units: Optional[str] = None

response = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[{
        "role": "user",
        "content": "Solve: If a train travels 120 miles in 2 hours, what is its speed?"
    }],
    response_format=MathSolution
)

solution = response.choices[0].message.parsed
print(solution.final_answer)  # 60.0
print(solution.units)  # "miles per hour"
```

## Error Handling & Retries

```python
from instructor import Instructor
from tenacity import retry, stop_after_attempt, wait_exponential

class RobustExtractor:
    def __init__(self, provider: str):
        self.client = instructor.from_provider(provider)
    
    def extract(
        self,
        response_model: type,
        content: str,
        max_retries: int = 3
    ):
        try:
            return self.client.create(
                response_model=response_model,
                messages=[{"role": "user", "content": content}],
                max_retries=max_retries
            )
        except instructor.IncompleteOutputException as e:
            # Model output was truncated
            logger.warning(f"Incomplete output: {e}")
            return self._handle_incomplete(response_model, content)
        except ValidationError as e:
            # Pydantic validation failed after all retries
            logger.error(f"Validation failed: {e}")
            raise
```

## Best Practices

1. **Use descriptive Field descriptions** - Helps the LLM understand intent
2. **Start simple** - Add complexity only when needed
3. **Validate at multiple levels** - Field, model, and semantic validators
4. **Handle partial results** - Use streaming for long extractions
5. **Set appropriate retries** - Usually 2-3 is sufficient
6. **Test edge cases** - Empty inputs, ambiguous data, long text
