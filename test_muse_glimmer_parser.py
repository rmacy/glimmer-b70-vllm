#!/usr/bin/env python3
"""Regression checks for Muse Glimmer's ATEM and recipient-channel parser."""

import importlib.util
from pathlib import Path


parser_path = Path("/opt/glimmer/muse_glimmer_vllm_parser.py")
spec = importlib.util.spec_from_file_location("muse_glimmer_vllm_parser", parser_path)
assert spec is not None and spec.loader is not None
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)

wire = (
    'to=self<|message|>Check the account.<|eom|>'
    '<atem:invoke name="lookup_account">'
    '<atem:parameter name="account_id">42</atem:parameter>'
    '<atem:parameter name="active">true</atem:parameter>'
    '<atem:parameter name="label">R&amp;D</atem:parameter>'
    '</atem:invoke>'
    'to=user<|message|>Done.<|eot|>'
)

assert parser._channel_body(wire, parser._REASONING_MARKER) == "Check the account."
assert parser._channel_body(wire, parser._CONTENT_MARKER) == "Done."
assert parser._parse_invocations(wire) == [
    ("lookup_account", {"account_id": 42, "active": True, "label": "R&D"})
]
assert parser._trim_partial_delimiter("answer<|eo", ("<|eom|>", "<|eot|>")) == "answer"

print("Muse Glimmer parser regression checks passed")
