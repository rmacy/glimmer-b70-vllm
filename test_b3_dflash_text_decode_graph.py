from pathlib import Path


runner = Path(
    "/opt/venv/lib/python3.12/site-packages/vllm/v1/worker/gpu_model_runner.py"
).read_text()

assert "is_dflash = isinstance(self.drafter, DFlashProposer)" in runner
assert "use_drafter_cudagraphs = not is_dflash or not any(" in runner
assert "spec_decode_metadata is not None\n                and not any(" not in runner
assert "bool(self.requests[req_id].mm_features)" in runner
assert "use_cudagraphs=use_drafter_cudagraphs" in runner

