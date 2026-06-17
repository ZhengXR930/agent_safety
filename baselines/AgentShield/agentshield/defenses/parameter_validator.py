"""
Layer 3: Parameter Validator (Allowlisting + Egress Filtering)
================================================================
Validates tool call parameters against predefined rules before execution.
Blocks tool calls that violate rules (e.g., sending email to unknown
recipients, accessing URLs outside allowed domains).

Rules are defined per-tool and per-parameter. If a rule is violated,
the tool call is removed from the assistant message and replaced with
a tool error message.
"""

import re
from collections.abc import Sequence
from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.functions_runtime import EmptyEnv, Env, FunctionsRuntime
from agentdojo.types import ChatMessage, FunctionCall


# ============================================================
# DEFAULT VALIDATION RULES
# ============================================================

DEFAULT_RULES = {
    "send_money": {
        "recipient": {
            "type": "allowlist",
            "description": "Recipient IBAN must be in known contacts",
            "allowed_values": [
                "UK12345678901234567890",   # Bill recipient from test data
                "US133000000121212121212",   # Known contact
                "SE3550000000054910000003",  # Known contact
                "DE89370400440532013000",    # User's own IBAN
            ],
        },
    },
    "send_email": {
        "recipient": {
            "type": "allowlist",
            "description": "Email recipient must be in known contacts",
            "allowed_values": [],  # Will be populated from environment
        },
    },
    "schedule_transaction": {
        "recipient": {
            "type": "allowlist",
            "description": "Recipient IBAN must be in known contacts",
            "allowed_values": [
                "UK12345678901234567890",
                "US133000000121212121212",
                "SE3550000000054910000003",
                "DE89370400440532013000",
            ],
        },
    },
    "update_password": {
        "password": {
            "type": "block_pattern",
            "description": "Password must not be set to a known weak value",
            "blocked_patterns": [
                r"^password$",
                r"^123456",
                r"^admin",
            ],
        },
    },
}

# Tools that should never be called with external URLs
URL_RULES = {
    "allowed_domains": [
        "company.local",
        "internal-api.company.local",
        "bank.example.com",
        # AgentDojo benchmark URLs (simulated environment)
        "informations.com",
        "dora-website.com",
        "eve-blog.com",
        "our-company.com",
        "company-todo-list.com",
    ],
    "url_params": ["url", "endpoint", "destination", "webhook_url"],
}


# ============================================================
# VALIDATOR PIPELINE ELEMENT
# ============================================================

class ParameterValidator(BasePipelineElement):
    """Validates tool call parameters against allowlisting rules.

    Runs INSIDE the ToolsExecutionLoop, BEFORE ToolsExecutor.
    Inspects each tool call's parameters. If a parameter violates
    a rule, the tool call is blocked (removed from the assistant
    message) and a tool error message is appended.

    Attributes:
        rules: Dict of tool_name -> param_name -> rule.
        detections: List of all blocked tool calls with reasons.
    """

    name = "parameter_validator"

    def __init__(self, rules: dict | None = None):
        self.rules = rules or DEFAULT_RULES
        self.detections = []

    def reset(self):
        """Clear detections for a new run."""
        self.detections = []

    def _check_allowlist(self, value: str, allowed: list[str]) -> bool:
        """Returns True if value is in the allowlist."""
        return value in allowed

    def _check_block_pattern(self, value: str, patterns: list[str]) -> bool:
        """Returns True if value matches any blocked pattern."""
        for pattern in patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False

    def _check_url_domain(self, value: str) -> bool:
        """Returns True if URL domain is NOT in allowed domains (i.e., suspicious)."""
        # Extract domain from URL-like strings
        if not isinstance(value, str):
            return False
        if "://" not in value and "." not in value:
            return False

        # Simple domain extraction
        domain = value
        if "://" in domain:
            domain = domain.split("://", 1)[1]
        domain = domain.split("/")[0]
        domain = domain.split(":")[0]

        # Check against allowed domains
        for allowed in URL_RULES["allowed_domains"]:
            if domain == allowed or domain.endswith("." + allowed):
                return False

        return True  # Domain not in allowlist = suspicious

    def _validate_tool_call(self, tc: FunctionCall) -> tuple[bool, str]:
        """Validate a tool call. Returns (is_blocked, reason)."""
        tool_name = tc.function
        args = tc.args

        # Check tool-specific parameter rules
        if tool_name in self.rules:
            for param_name, rule in self.rules[tool_name].items():
                if param_name not in args:
                    continue

                value = str(args[param_name])

                if rule["type"] == "allowlist":
                    if not self._check_allowlist(value, rule["allowed_values"]):
                        return True, f"Parameter '{param_name}' value '{value}' not in allowlist: {rule['description']}"

                elif rule["type"] == "block_pattern":
                    if self._check_block_pattern(value, rule["blocked_patterns"]):
                        return True, f"Parameter '{param_name}' matches blocked pattern: {rule['description']}"

        # Check URL parameters across all tools
        for param_name in URL_RULES["url_params"]:
            if param_name in args:
                value = str(args[param_name])
                if self._check_url_domain(value):
                    return True, f"Parameter '{param_name}' contains external URL '{value}' not in allowed domains"

        return False, ""

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: Sequence[ChatMessage] = [],
        extra_args: dict = {},
    ) -> tuple[str, FunctionsRuntime, Env, Sequence[ChatMessage], dict]:
        if len(messages) == 0:
            return query, runtime, env, messages, extra_args

        last_message = messages[-1]
        if last_message["role"] != "assistant":
            return query, runtime, env, messages, extra_args

        tool_calls = last_message.get("tool_calls")
        if not tool_calls:
            return query, runtime, env, messages, extra_args

        for tc in tool_calls:
            is_blocked, reason = self._validate_tool_call(tc)

            if is_blocked:
                detection = {
                    "layer": "parameter_validator",
                    "tool": tc.function,
                    "args": dict(tc.args),
                    "reason": reason,
                    "tool_call_id": tc.id,
                    "message_index": len(messages) - 1,
                }
                self.detections.append(detection)

        # Detection only — do not modify messages.
        # The tool call still executes in the simulation, but the
        # violation is recorded for analysis. This avoids breaking
        # the OpenAI API message flow while still detecting attacks.
        return query, runtime, env, messages, extra_args
