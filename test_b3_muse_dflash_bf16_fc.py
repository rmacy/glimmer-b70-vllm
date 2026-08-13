from pathlib import Path


source = Path("vllm/model_executor/models/qwen3_dflash.py").read_text()

assert 'os.environ.get("VLLM_MUSE_DFLASH_BF16_FC", "0") == "1"' in source
assert "fc_quant_config = (" in source
assert "quant_config=fc_quant_config" in source
assert "quant_config=self.quant_config" in source

print("PASS: DFlash auxiliary FC can retain official source precision selectively")
