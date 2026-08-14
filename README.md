# Muse Glimmer 30B on 2x Intel Arc Pro B70

Native Intel-vLLM runtime for Meta Muse Glimmer 30B on two 32 GiB Intel Arc
Pro B70 GPUs. The image serves the complete 131,072-token context, official
DFlash assistant, ATEM tool calls, and vision path.

Read [SECURITY.md](SECURITY.md) before exposing the service. Release `0.1.1`
adds the upstream fix for CVE-2026-48746 to the pinned Intel-vLLM base.

The default target path is full-parameter FP8: every eligible linear weight is
represented in eight-bit floating point with floating-point scales. This is
not GGUF, pruning, distillation, or 4/5/6-bit quantization. Official BF16 target
weights are mounted at runtime and converted during load. Model weights are
not included in the image.

## Measured profile

One two-B70 system produced single-stream, post-prefill medians of 88.43 tok/s
at approximately 32K context, 84.84 tok/s at approximately 64K, and 79.59 tok/s
across a 12-request approximately 126K exact-retrieval soak. The largest
observed 32K run was 94.88 tok/s. Results depend on host drivers, thermals,
prompt shape, and output distribution.

The production defaults are TP=2, 131,072 model context, 4,096 batched prefill
tokens, one active sequence, 0.72 GPU-memory utilization, 15 DFlash proposal
tokens, XPU decode graphs, BF16 assistant auxiliary projection, and FP16
activations around the FP8 weights.

## Requirements

- Linux host with two Intel Arc Pro B70 32 GiB GPUs
- Docker with access to `/dev/dri`
- Current Intel compute/runtime drivers compatible with the pinned base image
- Approximately 75 GB for the official BF16 target and DFlash assistant, plus
  container storage
- Access to Meta's official Hugging Face repositories and accepted terms

Download the official checkpoints with a current Hugging Face CLI:

```bash
mkdir -p models
hf download meta-models/Muse-Glimmer-30B \
  --local-dir models/muse-glimmer-30b-bf16
hf download meta-models/Muse-Glimmer-30B-assistant \
  --local-dir models/muse-glimmer-30b-assistant-official
```

## Published images

The same release is published to GitHub Container Registry and Google Artifact
Registry:

```text
ghcr.io/rmacy/glimmer-b70-vllm:0.1.1
us-central1-docker.pkg.dev/home-504803/open-models/glimmer-b70-vllm:0.1.1
```

## Run the prebuilt image

```bash
docker pull ghcr.io/rmacy/glimmer-b70-vllm:0.1.1

docker run --rm --name muse-glimmer \
  --device /dev/dri \
  -v /dev/dri/by-path:/dev/dri/by-path:ro \
  --ipc=host \
  --shm-size 32g \
  -p 127.0.0.1:8000:8000 \
  -v "$PWD/models:/models:ro" \
  ghcr.io/rmacy/glimmer-b70-vllm:0.1.1
```

Health and model checks:

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/v1/models
```

For Compose:

```bash
GHCR_OWNER=rmacy GLIMMER_TAG=0.1.1 docker compose up -d
docker compose logs -f glimmer
```

## Build locally

```bash
docker build \
  -f Dockerfile.b3-glimmer-one \
  -t glimmer-b70-vllm:0.1.1 .
```

The Dockerfile pins both the Intel base-image digest and the Transformers
revision. It applies only the selected 24-patch production series and runs the
patch-specific tests while building.

## Runtime overrides

All important defaults can be overridden with environment variables:

- `MODEL_PATH` and `ASSISTANT_PATH`
- `GPU_UTIL`, `MAX_MODEL_LEN`, `MAX_BATCHED_TOKENS`, and `MAX_NUM_SEQS`
- `TP_SIZE`, `BLOCK_SIZE`, and `KV_CACHE_DTYPE`
- `SPECULATIVE_CONFIG`, `COMPILATION_CONFIG`, and `DISABLE_SPECULATION`
- `API_KEY` to enable vLLM's bearer-token authentication
- `WEIGHT_PRECISION=fp8` or the BF16 rollback mode

Reducing context, disabling official DFlash semantics, or using lower-bit
weights is not part of the validated profile.

## Privacy and contents

The release contains runtime code, patches, tests, and a parser only. It does
not contain model weights, prompts, request logs, credentials, private keys,
tokens, hostnames, private network addresses, home-directory paths, or user
data. Build provenance and SBOM attestations are disabled in the publishing
workflow so local runner paths cannot be attached to the image manifest.

Upstream dependencies retain their own public author and license metadata.

Official model pages:

- https://huggingface.co/meta-models/Muse-Glimmer-30B
- https://huggingface.co/meta-models/Muse-Glimmer-30B-assistant
