from pathlib import Path


dflash = Path(
    "/opt/venv/lib/python3.12/site-packages/vllm/v1/spec_decode/dflash.py"
).read_text()

assert "self._seq_lens_buffer = torch.zeros(" in dflash
assert "proposal_seq_lens = self._seq_lens_buffer[:batch_size]" in dflash
assert "torch.add(effective_seq_lens, num_query_per_req, out=proposal_seq_lens)" in dflash
assert "seq_lens=proposal_seq_lens" in dflash
assert "seq_lens=effective_seq_lens + num_query_per_req" not in dflash
