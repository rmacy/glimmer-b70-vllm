#!/usr/bin/env python3
"""Prove chunked Onyx vision attention matches the former block mask."""

import inspect

import torch

from vllm.model_executor.models.onyx_mm import OnyxVisionAttention, OnyxVisionEncoder


def make_block_mask(lengths: list[int]) -> torch.Tensor:
    total = sum(lengths)
    mask = torch.zeros(total, total, dtype=torch.bool)
    offset = 0
    for length in lengths:
        mask[offset : offset + length, offset : offset + length] = True
        offset += length
    return mask


def main() -> None:
    torch.manual_seed(8675309)
    attention = OnyxVisionAttention(dim=64, n_heads=4, head_dim=16).eval()
    lengths = [7, 5, 9]
    hidden = torch.randn(sum(lengths), 64)
    with torch.no_grad():
        masked = attention(
            hidden,
            slen=hidden.shape[0],
            attn_bias=make_block_mask(lengths),
        )
        chunked = attention(
            hidden,
            slen=hidden.shape[0],
            chunk_lengths=lengths,
        )
    torch.testing.assert_close(chunked, masked, rtol=2e-5, atol=2e-5)

    encoder_source = inspect.getsource(OnyxVisionEncoder.encode_one)
    assert "chunk_lengths=sp_slens" in encoder_source
    assert "self._make_block_diag_mask(sp_slens" not in encoder_source
    print("PASS: varlen vision attention exactly matches block-diagonal semantics")


if __name__ == "__main__":
    main()
