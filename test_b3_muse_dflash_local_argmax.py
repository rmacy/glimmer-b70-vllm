from types import SimpleNamespace

import torch

from vllm.model_executor.models.qwen3_dflash import DFlashQwen3ForCausalLM


class FakeLogitsProcessor:
    def get_top_tokens(self, lm_head, hidden_states):
        assert lm_head == "shared-target-head"
        assert hidden_states.shape == (2, 3)
        return torch.tensor([1, 0], dtype=torch.int64)


base = SimpleNamespace(
    logits_processor=FakeLogitsProcessor(),
    lm_head="shared-target-head",
    draft_id_to_target_id=None,
)
hidden = torch.zeros((2, 3))
result = DFlashQwen3ForCausalLM.get_top_tokens(base, hidden)
assert result.tolist() == [1, 0]

remapped = SimpleNamespace(
    logits_processor=FakeLogitsProcessor(),
    lm_head="shared-target-head",
    draft_id_to_target_id=torch.tensor([10, 20], dtype=torch.int64),
)
result = DFlashQwen3ForCausalLM.get_top_tokens(remapped, hidden)
assert result.tolist() == [21, 10]
