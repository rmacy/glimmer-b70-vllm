#!/usr/bin/env bash
# Full-parameter Muse Glimmer 30B server for two Intel Arc Pro B70 GPUs.
#
# The FP8 mode preserves every parameter using eight-bit floating-point
# weights plus floating-point scales. It does not use GGUF, pruning,
# distillation, or 4/5/6-bit quantization.
set -euo pipefail

export ZE_AFFINITY_MASK="${ZE_AFFINITY_MASK:-0,1}"
export VLLM_ALLOW_LONG_MAX_MODEL_LEN=1
export VLLM_WORKER_MULTIPROC_METHOD=spawn

MODEL_PATH="${MODEL_PATH:-/models/muse-glimmer-30b-bf16}"
ASSISTANT_PATH="${ASSISTANT_PATH:-/models/muse-glimmer-30b-assistant-official}"
PARSER_PATH="${PARSER_PATH:-/opt/glimmer/muse_glimmer_vllm_parser.py}"
PORT="${PORT:-8000}"
WEIGHT_PRECISION="${WEIGHT_PRECISION:-fp8}"

case "${WEIGHT_PRECISION}" in
  fp8)
    model_dtype="float16"
    served_model_name="muse-glimmer-30b-fp8"
    quantization_args=(--quantization fp8)
    ;;
  bf16)
    model_dtype="bfloat16"
    served_model_name="muse-glimmer-30b-bf16"
    quantization_args=()
    ;;
  *)
    echo "Unsupported WEIGHT_PRECISION=${WEIGHT_PRECISION}; use fp8 or bf16." >&2
    exit 2
    ;;
esac

default_speculative_config=$(printf \
  '{"model":"%s","method":"dflash","num_speculative_tokens":15,"draft_tensor_parallel_size":2,"use_local_argmax_reduction":true}' \
  "${ASSISTANT_PATH}")
default_compilation_config='{"cudagraph_mode":"FULL_DECODE_ONLY","cudagraph_capture_sizes":[16],"max_cudagraph_capture_size":16}'

args=(
  vllm serve
  --host 0.0.0.0
  --port "${PORT}"
  --model "${MODEL_PATH}"
  --served-model-name "${SERVED_MODEL_NAME:-${served_model_name}}"
  --model-impl "${MODEL_IMPL:-auto}"
  --dtype "${model_dtype}"
  --tensor-parallel-size "${TP_SIZE:-2}"
  --gpu-memory-utilization "${GPU_UTIL:-0.72}"
  --max-model-len "${MAX_MODEL_LEN:-131072}"
  --max-num-batched-tokens "${MAX_BATCHED_TOKENS:-4096}"
  --max-num-seqs "${MAX_NUM_SEQS:-1}"
  --block-size "${BLOCK_SIZE:-64}"
  --chat-template "${MODEL_PATH}/chat_template.jinja"
  --enable-auto-tool-choice
  --tool-call-parser muse_glimmer
  --tool-parser-plugin "${PARSER_PATH}"
  --reasoning-parser muse_glimmer
  --reasoning-parser-plugin "${PARSER_PATH}"
)

if [[ "${LANGUAGE_MODEL_ONLY:-0}" == "1" ]]; then
  args+=(--language-model-only)
fi

args+=("${quantization_args[@]}")

if [[ "${KV_CACHE_DTYPE:-auto}" != "auto" ]]; then
  args+=(--kv-cache-dtype "${KV_CACHE_DTYPE}")
fi

if [[ -n "${KV_CACHE_DTYPE_SKIP_LAYERS:-}" ]]; then
  args+=(--kv-cache-dtype-skip-layers "${KV_CACHE_DTYPE_SKIP_LAYERS}")
fi

if [[ -n "${LOAD_FORMAT:-}" ]]; then
  args+=(--load-format "${LOAD_FORMAT}")
fi

if [[ -n "${PROFILER_CONFIG:-}" ]]; then
  args+=(--profiler-config "${PROFILER_CONFIG}")
fi

compilation_config="${COMPILATION_CONFIG:-${default_compilation_config}}"
if [[ -n "${compilation_config}" ]]; then
  args+=(--compilation-config "${compilation_config}")
fi

if [[ "${ENFORCE_EAGER:-0}" == "1" ]]; then
  args+=(--enforce-eager)
fi

case "${ASYNC_SCHEDULING:-auto}" in
  auto) ;;
  1) args+=(--async-scheduling) ;;
  0) args+=(--no-async-scheduling) ;;
  *)
    echo "Unsupported ASYNC_SCHEDULING=${ASYNC_SCHEDULING}; use auto, 1, or 0." >&2
    exit 2
    ;;
esac

speculative_config="${SPECULATIVE_CONFIG:-${default_speculative_config}}"
if [[ "${DISABLE_SPECULATION:-0}" != "1" && -n "${speculative_config}" ]]; then
  args+=(--speculative-config "${speculative_config}")
fi

exec "${args[@]}"
