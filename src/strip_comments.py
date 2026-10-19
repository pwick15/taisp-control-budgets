"""Monitor prompt formatter that hides `#` comments from the monitor.

In the APPS dataset, many verified backdoors carry comments that announce the bug
("# Introduce a flaw: ...") and honest solutions rarely do, so a monitor can score well
by reading comments instead of code. Stripping comments from every submission, honest
and attack, measures code-reading alone.

Used by experiment.py when STRIP_COMMENTS=1.
"""
import io
import logging
import tokenize
from collections.abc import Sequence

from inspect_ai.model import ChatMessage

from control_arena._control_task_metadata import ControlTaskMetadata
from control_arena.monitor import last_tool_calls_prompt_formatter
from control_arena.monitor._monitor import get_last_assistant_message

logger = logging.getLogger(__name__)


def strip_comments(code: str) -> str:
    """Remove `#` comments from Python source, leaving `#` inside strings alone.

    Lines that held only a comment are dropped. If the code does not tokenize (for
    example Python 2 syntax), it is returned unchanged and a warning is logged.
    """
    lines = code.splitlines()
    try:
        comments = [
            tok for tok in tokenize.generate_tokens(io.StringIO(code).readline)
            if tok.type == tokenize.COMMENT
        ]
    except (tokenize.TokenError, IndentationError, SyntaxError):
        logger.warning("Could not tokenize submission; comments left in place.")
        return code

    comment_only = set()
    for tok in comments:
        row, col = tok.start[0] - 1, tok.start[1]
        before = lines[row][:col]
        if not before.strip():
            comment_only.add(row)
        lines[row] = before.rstrip()
    return "\n".join(line for i, line in enumerate(lines) if i not in comment_only)


def strip_comments_prompt_formatter(
    task_metadata: ControlTaskMetadata,
    messages: Sequence[ChatMessage],
    prompt: str,
) -> str:
    """Same as the default formatter, but the submitted `code` has no comments."""
    last = get_last_assistant_message(messages)
    stripped_calls = [
        tool_call.__class__(
            id=tool_call.id,
            function=tool_call.function,
            arguments={
                key: strip_comments(value) if key == "code" and isinstance(value, str) else value
                for key, value in tool_call.arguments.items()
            },
        )
        for tool_call in last.tool_calls or []
    ]
    stripped = last.model_copy(update={"tool_calls": stripped_calls})
    rest = [m for m in messages if m is not last]
    return last_tool_calls_prompt_formatter(task_metadata, [*rest, stripped], prompt)
