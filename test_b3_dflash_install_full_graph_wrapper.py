from pathlib import Path


runner = Path(
    "/opt/venv/lib/python3.12/site-packages/vllm/v1/worker/gpu_model_runner.py"
).read_text()

assert 'if isinstance(getattr(self, "drafter", None), DFlashProposer):' in runner
assert "dflash_backbone = drafter_model.model" in runner
assert "draft_vllm_config = dflash_backbone.vllm_config" in runner
assert "drafter_model._full_graph_backbone = CUDAGraphWrapper(" in runner
assert "runtime_mode=CUDAGraphMode.FULL" in runner

draft = Path(
    "/opt/venv/lib/python3.12/site-packages/vllm/model_executor/models/qwen3_dflash.py"
).read_text()
assert 'backbone = getattr(self, "_full_graph_backbone", self.model)' in draft
assert "return backbone(input_ids, positions, inputs_embeds)" in draft
