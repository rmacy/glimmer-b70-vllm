from pathlib import Path


dflash = Path(
    "/opt/venv/lib/python3.12/site-packages/vllm/v1/spec_decode/dflash.py"
).read_text()

assert "self._query_start_loc_buffer = torch.zeros(" in dflash
assert "out=new_query_start_loc" in dflash
assert "proposal_max_seq_len = self.max_model_len" in dflash
assert "max_seq_len=proposal_max_seq_len" in dflash
assert "max_seq_len=cad.max_seq_len + num_query_per_req" not in dflash
assert 'getattr(self.draft_model_config.hf_config, "sliding_window", 2048)' not in dflash
