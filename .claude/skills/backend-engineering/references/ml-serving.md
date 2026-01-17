# ML Inference Serving

## Runtime Selection

| Runtime | Best For | Optimization |
|---------|----------|--------------|
| ONNX Runtime | Cross-platform, general models | Graph optimization, EP fallback |
| vLLM | LLM serving | PagedAttention, continuous batching |
| TensorRT | NVIDIA GPUs, vision models | FP16/INT8, kernel fusion |
| Triton | Multi-model serving | Dynamic batching, model ensembles |

## ONNX Runtime Configuration

```python
import onnxruntime as ort

# Execution provider fallback chain
providers = [
    ('TensorrtExecutionProvider', {
        'device_id': 0,
        'trt_fp16_enable': True,
        'trt_engine_cache_enable': True,
        'trt_engine_cache_path': './trt_cache'
    }),
    ('CUDAExecutionProvider', {
        'arena_extend_strategy': 'kNextPowerOfTwo',
        'gpu_mem_limit': 4 * 1024 * 1024 * 1024,
        'cudnn_conv_algo_search': 'EXHAUSTIVE',
    }),
    'CPUExecutionProvider'
]

sess_options = ort.SessionOptions()
sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
sess_options.intra_op_num_threads = 4

session = ort.InferenceSession("model.onnx", sess_options, providers=providers)
```

## vLLM for LLM Serving

PagedAttention eliminates memory fragmentation, achieving **24x throughput** over naive implementations.

### CLI Launch
```bash
vllm serve meta-llama/Llama-3.1-70B-Instruct \
    --tensor-parallel-size 4 \
    --gpu-memory-utilization 0.90 \
    --max-model-len 8192 \
    --max-num-seqs 256 \
    --enable-chunked-prefill \
    --enable-prefix-caching \
    --quantization awq
```

### Key Parameters
| Parameter | Latency-Optimized | Throughput-Optimized |
|-----------|-------------------|----------------------|
| `max_num_batched_tokens` | 2048 | 8192 |
| `gpu_memory_utilization` | 0.85 | 0.95 |
| `max_num_seqs` | 64 | 256 |

### Python Integration
```python
from vllm import LLM, SamplingParams

llm = LLM(
    model="meta-llama/Llama-3.1-8B-Instruct",
    tensor_parallel_size=2,
    gpu_memory_utilization=0.9,
    quantization="awq"
)

sampling_params = SamplingParams(
    temperature=0.7,
    top_p=0.9,
    max_tokens=512
)

outputs = llm.generate(prompts, sampling_params)
```

## Quantization Strategies

| Method | Memory Reduction | Speed | Best For |
|--------|------------------|-------|----------|
| AWQ INT4 | 4x | 5-10% faster | GPU inference, production |
| GPTQ INT4 | 4x | Good with Marlin | Fine control needed |
| FP8 | 2x | 2-4x on H100/Ada | Latest hardware |
| GGUF | 4-8x | Variable | CPU inference, Apple Silicon |

### AWQ Quantization
```python
from awq import AutoAWQForCausalLM
from transformers import AutoTokenizer

model_path = "meta-llama/Llama-3.1-8B-Instruct"
quant_path = "./llama-3.1-8b-awq"

tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoAWQForCausalLM.from_pretrained(model_path)

quant_config = {
    "zero_point": True,
    "q_group_size": 128,
    "w_bit": 4
}

model.quantize(tokenizer, quant_config=quant_config)
model.save_quantized(quant_path)
tokenizer.save_pretrained(quant_path)
```

## Batching Strategies

### Static vs Continuous Batching
- **Static**: Waits for batch to fill, pads sequences
- **Continuous**: Inserts requests immediately, **23x throughput improvement**

### Triton Inference Server Config
```protobuf
# config.pbtxt
dynamic_batching {
    preferred_batch_size: [4, 8, 16, 32]
    max_queue_delay_microseconds: 100
}

instance_group [
    { count: 4, kind: KIND_GPU }
]
```

## FastAPI Inference Service

```python
from fastapi import FastAPI
from pydantic import BaseModel
import onnxruntime as ort
from contextlib import asynccontextmanager

class InferenceRequest(BaseModel):
    inputs: list[list[float]]

class InferenceResponse(BaseModel):
    outputs: list[list[float]]

session: ort.InferenceSession = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global session
    session = ort.InferenceSession(
        "model.onnx",
        providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
    )
    yield
    del session

app = FastAPI(lifespan=lifespan)

@app.post("/predict", response_model=InferenceResponse)
async def predict(request: InferenceRequest):
    import numpy as np
    inputs = np.array(request.inputs, dtype=np.float32)
    outputs = session.run(None, {"input": inputs})
    return InferenceResponse(outputs=outputs[0].tolist())
```

## Rust ONNX Serving (ort crate)

```rust
use ort::{Session, Value, tensor::OrtOwnedTensor};
use ndarray::Array2;

fn load_model() -> ort::Result<Session> {
    Session::builder()?
        .with_optimization_level(ort::GraphOptimizationLevel::Level3)?
        .with_intra_threads(4)?
        .commit_from_file("model.onnx")
}

async fn inference(session: &Session, input: Array2<f32>) -> ort::Result<Vec<f32>> {
    let input_tensor = Value::from_array(input)?;
    let outputs = session.run(ort::inputs![input_tensor]?)?;
    let output: OrtOwnedTensor<f32, _> = outputs[0].try_extract()?;
    Ok(output.view().iter().copied().collect())
}
```

## Model Optimization Checklist

- [ ] Profile baseline latency and throughput
- [ ] Export to ONNX with opset 17+
- [ ] Run ONNX graph optimization
- [ ] Quantize (AWQ for LLMs, INT8 for vision)
- [ ] Enable TensorRT if NVIDIA GPU
- [ ] Configure continuous batching
- [ ] Set up model warmup on startup
- [ ] Monitor GPU memory and utilization
