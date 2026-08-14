#!/usr/bin/env bash
set -euo pipefail

fake_dir=$(mktemp -d)
cleanup() {
  find "${fake_dir}" -type f -delete 2>/dev/null || true
  rmdir "${fake_dir}" 2>/dev/null || true
}
trap cleanup EXIT
launcher=${LAUNCHER_PATH:-/opt/glimmer/serve-glimmer.sh}

printf '%s\n' '#!/usr/bin/env bash' 'printf "<%s>\\n" "$@"' > "${fake_dir}/vllm"
chmod 0755 "${fake_dir}/vllm"

run_launcher() {
  PATH="${fake_dir}:${PATH}" bash "${launcher}"
}

default_output=$(run_launcher)
grep -Fxq '<serve>' <<<"${default_output}"
grep -Fxq '<--quantization>' <<<"${default_output}"
grep -Fxq '<fp8>' <<<"${default_output}"
grep -Fxq '<--tool-call-parser>' <<<"${default_output}"
grep -Fxq '<muse_glimmer>' <<<"${default_output}"
grep -Fxq '<--speculative-config>' <<<"${default_output}"
grep -Fxq '<--gpu-memory-utilization>' <<<"${default_output}"
grep -Fxq '<0.74>' <<<"${default_output}"

secured_output=$(API_KEY=release-audit-placeholder run_launcher)
grep -Fxq '<--api-key>' <<<"${secured_output}"
grep -Fxq '<release-audit-placeholder>' <<<"${secured_output}"

no_spec_output=$(DISABLE_SPECULATION=1 run_launcher)
if grep -Fxq '<--speculative-config>' <<<"${no_spec_output}"; then
  echo 'DISABLE_SPECULATION=1 still emitted --speculative-config' >&2
  exit 1
fi

if WEIGHT_PRECISION=invalid run_launcher >/dev/null 2>&1; then
  echo 'invalid WEIGHT_PRECISION unexpectedly succeeded' >&2
  exit 1
fi

echo 'Muse Glimmer launcher regression checks passed'
