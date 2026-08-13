#!/usr/bin/env python3
"""vLLM response parsers for Muse Glimmer's Onyx/ATEM wire format."""

from __future__ import annotations

import html
import json
import re
from collections.abc import Iterable, Sequence
from typing import Any

from vllm.entrypoints.chat_utils import make_tool_call_id
from vllm.entrypoints.openai.engine.protocol import (
    DeltaFunctionCall,
    DeltaMessage,
    DeltaToolCall,
    ExtractedToolCallInformation,
    FunctionCall,
    ToolCall,
)
from vllm.reasoning import ReasoningParser, ReasoningParserManager
from vllm.tool_parsers import ToolParser, ToolParserManager


_REASONING_MARKER = "to=self<|message|>"
_CONTENT_MARKER = "to=user<|message|>"
_EOM = "<|eom|>"
_EOT = "<|eot|>"
_ASSISTANT_START = "<|start|>assistant"

_INVOKE_RE = re.compile(
    r'<atem:invoke\b[^>]*?\bname="(?P<name>[^"]+)">(?P<body>.*?)</atem:invoke>',
    re.DOTALL,
)
_PARAM_RE = re.compile(
    r'<atem:parameter\b[^>]*?\bname="(?P<name>[^"]+)"[^>]*?>(?P<value>.*?)</atem:parameter>',
    re.DOTALL,
)


def _trim_partial_delimiter(text: str, delimiters: tuple[str, ...]) -> str:
    """Hold back a suffix that may be the beginning of a control delimiter."""

    for size in range(min(max(map(len, delimiters)) - 1, len(text)), 0, -1):
        suffix = text[-size:]
        if any(delimiter.startswith(suffix) for delimiter in delimiters):
            return text[:-size]
    return text


def _channel_body(text: str, marker: str) -> str | None:
    """Return a complete or in-progress recipient channel body."""

    start = text.rfind(marker)
    if start < 0:
        return None
    body = text[start + len(marker) :]
    end_positions = [
        position
        for token in (_EOM, _EOT)
        if (position := body.find(token)) >= 0
    ]
    if end_positions:
        body = body[: min(end_positions)]
    else:
        body = _trim_partial_delimiter(body, (_EOM, _EOT, _ASSISTANT_START))
    return body


def _decode_parameter(value: str) -> Any:
    decoded = html.unescape(value).strip()
    if not decoded:
        return ""
    try:
        return json.loads(decoded)
    except (json.JSONDecodeError, ValueError):
        return decoded


def _parse_invocations(text: str) -> list[tuple[str, dict[str, Any]]]:
    invocations: list[tuple[str, dict[str, Any]]] = []
    for invoke in _INVOKE_RE.finditer(text):
        arguments: dict[str, Any] = {}
        for parameter in _PARAM_RE.finditer(invoke.group("body")):
            arguments[parameter.group("name")] = _decode_parameter(
                parameter.group("value")
            )
        invocations.append((html.unescape(invoke.group("name")), arguments))
    return invocations


def _contains_subsequence(values: Sequence[int], needle: Sequence[int]) -> bool:
    if not needle or len(needle) > len(values):
        return False
    return any(
        list(values[index : index + len(needle)]) == list(needle)
        for index in range(len(values) - len(needle) + 1)
    )


@ToolParserManager.register_module("muse_glimmer")
class MuseGlimmerToolParser(ToolParser):
    """Parse Muse Glimmer ATEM invocations into OpenAI function calls."""

    supports_required_and_named = False

    def __init__(self, tokenizer, tools=None):
        super().__init__(tokenizer, tools)
        self._streamed_tool_count = 0
        self._streamed_content_length = 0

    def adjust_request(self, request):
        if request.tools and request.tool_choice != "none":
            request.skip_special_tokens = False
        return request

    def extract_tool_calls(self, model_output, request):
        invocations = _parse_invocations(model_output)
        if not invocations:
            content = _channel_body(model_output, _CONTENT_MARKER)
            if content is None:
                content = model_output
            return ExtractedToolCallInformation(
                tools_called=False,
                tool_calls=[],
                content=content,
            )

        tool_calls = [
            ToolCall(
                type="function",
                function=FunctionCall(
                    name=name,
                    arguments=json.dumps(arguments, ensure_ascii=False),
                ),
            )
            for name, arguments in invocations
        ]
        return ExtractedToolCallInformation(
            tools_called=True,
            tool_calls=tool_calls,
            content=_channel_body(model_output, _CONTENT_MARKER),
        )

    def extract_tool_calls_streaming(
        self,
        previous_text: str,
        current_text: str,
        delta_text: str,
        previous_token_ids: Sequence[int],
        current_token_ids: Sequence[int],
        delta_token_ids: Sequence[int],
        request,
    ) -> DeltaMessage | None:
        invocations = _parse_invocations(current_text)
        tool_deltas: list[DeltaToolCall] = []
        for index in range(self._streamed_tool_count, len(invocations)):
            name, arguments = invocations[index]
            tool_deltas.append(
                DeltaToolCall(
                    index=index,
                    type="function",
                    id=make_tool_call_id(),
                    function=DeltaFunctionCall(
                        name=name,
                        arguments=json.dumps(arguments, ensure_ascii=False),
                    ).model_dump(exclude_none=True),
                )
            )
        self._streamed_tool_count = len(invocations)

        content_delta = None
        content = _channel_body(current_text, _CONTENT_MARKER)
        if content is not None and len(content) > self._streamed_content_length:
            content_delta = content[self._streamed_content_length :]
            self._streamed_content_length = len(content)

        if content_delta or tool_deltas:
            return DeltaMessage(content=content_delta, tool_calls=tool_deltas)
        return None


@ReasoningParserManager.register_module("muse_glimmer")
class MuseGlimmerReasoningParser(ReasoningParser):
    """Parse Muse Glimmer's private and user recipient channels."""

    def __init__(self, tokenizer, *args, **kwargs):
        super().__init__(tokenizer, *args, **kwargs)
        self._eom_ids = tokenizer.encode(_EOM, add_special_tokens=False)
        self._reasoning_marker_ids = tokenizer.encode(
            _REASONING_MARKER, add_special_tokens=False
        )
        self._streamed_reasoning_length = 0
        self._streamed_content_length = 0

    @property
    def reasoning_start_str(self) -> str:
        return _REASONING_MARKER

    @property
    def reasoning_end_str(self) -> str:
        return _EOM

    def adjust_request(self, request):
        request.skip_special_tokens = False
        return request

    def is_reasoning_end(self, input_ids: Sequence[int]) -> bool:
        return _contains_subsequence(input_ids, self._eom_ids)

    def is_reasoning_end_streaming(
        self, input_ids: Sequence[int], delta_ids: Iterable[int]
    ) -> bool:
        return self.is_reasoning_end(input_ids)

    def extract_content_ids(self, input_ids: list[int]) -> list[int]:
        if not self._eom_ids:
            return input_ids
        for index in range(len(input_ids) - len(self._eom_ids), -1, -1):
            if input_ids[index : index + len(self._eom_ids)] == self._eom_ids:
                return input_ids[index + len(self._eom_ids) :]
        return input_ids

    def count_reasoning_tokens(self, token_ids: Sequence[int]) -> int:
        if not self._reasoning_marker_ids or not self._eom_ids:
            return 0
        start = -1
        for index in range(len(token_ids) - len(self._reasoning_marker_ids) + 1):
            if list(
                token_ids[index : index + len(self._reasoning_marker_ids)]
            ) == list(self._reasoning_marker_ids):
                start = index + len(self._reasoning_marker_ids)
                break
        if start < 0:
            return 0
        for index in range(start, len(token_ids) - len(self._eom_ids) + 1):
            if list(token_ids[index : index + len(self._eom_ids)]) == list(
                self._eom_ids
            ):
                return index - start
        return len(token_ids) - start

    def extract_reasoning(self, model_output, request):
        reasoning = _channel_body(model_output, _REASONING_MARKER)
        content = _channel_body(model_output, _CONTENT_MARKER)
        if content is None and _INVOKE_RE.search(model_output):
            content = model_output
        if reasoning is None and content is None:
            return None, model_output
        return reasoning, content

    def extract_reasoning_streaming(
        self,
        previous_text: str,
        current_text: str,
        delta_text: str,
        previous_token_ids: Sequence[int],
        current_token_ids: Sequence[int],
        delta_token_ids: Sequence[int],
    ) -> DeltaMessage | None:
        reasoning_delta = None
        reasoning = _channel_body(current_text, _REASONING_MARKER)
        if reasoning is not None and len(reasoning) > self._streamed_reasoning_length:
            reasoning_delta = reasoning[self._streamed_reasoning_length :]
            self._streamed_reasoning_length = len(reasoning)

        content_delta = None
        content = _channel_body(current_text, _CONTENT_MARKER)
        if content is not None and len(content) > self._streamed_content_length:
            content_delta = content[self._streamed_content_length :]
            self._streamed_content_length = len(content)

        if _EOM in delta_text:
            tool_tail = delta_text.rsplit(_EOM, 1)[1]
            if tool_tail:
                content_delta = tool_tail

        if reasoning_delta or content_delta:
            return DeltaMessage(
                reasoning_content=reasoning_delta,
                content=content_delta,
            )
        return None
