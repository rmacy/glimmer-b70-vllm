from pathlib import Path


dflash = Path(
    "/opt/venv/lib/python3.12/site-packages/vllm/v1/spec_decode/dflash.py"
).read_text()

assert "proposal_max_seq_len = self.max_model_len" in dflash
assert "dummy_common_attn_metadata = CommonAttentionMetadata(" in dflash
assert "dummy_per_layer_attn_metadata" in dflash
assert "dummy_per_layer_attn_metadata,\n            self.vllm_config" in dflash
dummy_start = dflash.index("    def dummy_run(")
dummy_end = dflash.index("    def build_model_inputs_first_pass(", dummy_start)
dummy = dflash[dummy_start:dummy_end]
assert "slot_mapping_dict = self._get_slot_mapping(num_input_tokens)" in dummy
assert "if not is_graph_capturing:" in dummy
assert "cudagraph_runtime_mode=CUDAGraphMode.NONE" in dummy
