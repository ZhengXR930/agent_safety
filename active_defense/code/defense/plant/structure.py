"""Deterministic observation traversal and rewrite validation."""
import json


def _leaves(value):
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        yield from _leaves(dump())
        return
    if isinstance(value, dict):
        for child in value.values():
            yield from _leaves(child)
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            yield from _leaves(child)
    elif value is not None:
        yield value


def _contains(value, token: str, *, exact: bool) -> bool:
    return any(leaf == token or (
        not exact and isinstance(leaf, str) and token in leaf)
        for leaf in _leaves(value))


def _token_locations(value, token: str, path=""):
    """Return exact JSON-pointer leaves that contain one deployed token."""
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        yield from _token_locations(dump(), token, path)
        return
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _token_locations(
                child, token, path + "/" + _pointer_part(key))
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            yield from _token_locations(child, token, path + "/" + str(index))
    elif isinstance(value, str) and token in value:
        yield path


def _plain(value):
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        return dump(mode="json")
    if isinstance(value, dict):
        return {key: _plain(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(child) for child in value]
    return value


def _pointer_part(value) -> str:
    return str(value).replace("~", "~0").replace("/", "~1")


def _changed_leaf(before, after, path=""):
    if isinstance(before, dict) and isinstance(after, dict):
        for key in before:
            changed = _changed_leaf(before[key], after[key], path + "/" + _pointer_part(key))
            if changed is not None:
                return changed
        return None
    if isinstance(before, list) and isinstance(after, list):
        for index, (left, right) in enumerate(zip(before, after)):
            changed = _changed_leaf(left, right, path + "/" + str(index))
            if changed is not None:
                return changed
        return None
    return None if before == after else (path, before, after)


def _markerize_operand(operand: str, token: str) -> str:
    """Insert a nonce without deleting any original byte or delimiter."""
    marker = "://"
    index = operand.find(marker)
    insertion = index + len(marker) if index >= 0 else 0
    return operand[:insertion] + token + operand[insertion:]


def _unique_operand_span(value, operand: str, path=""):
    """Locate one exact string occurrence without retaining its raw value."""
    matches = []

    def visit(node, pointer):
        if isinstance(node, dict):
            for key, child in node.items():
                visit(child, pointer + "/" + _pointer_part(key))
        elif isinstance(node, list):
            for index, child in enumerate(node):
                visit(child, pointer + "/" + str(index))
        elif isinstance(node, str):
            start = 0
            while True:
                position = node.find(operand, start)
                if position < 0:
                    break
                matches.append((pointer, position, position + len(operand)))
                start = position + max(1, len(operand))

    visit(value, path)
    return matches[0] if len(matches) == 1 else None


def _replace_span(value, locator: str, start: int, end: int, replacement: str,
                  path=""):
    """Replace one previously validated string span in a same-version value."""
    if isinstance(value, dict):
        return {key: _replace_span(
            child, locator, start, end, replacement,
            path + "/" + _pointer_part(key))
            for key, child in value.items()}
    if isinstance(value, list):
        return [_replace_span(
            child, locator, start, end, replacement, path + "/" + str(index))
            for index, child in enumerate(value)]
    if path != locator or not isinstance(value, str):
        return value
    if start < 0 or end < start or end > len(value):
        raise ValueError("cached PLANT span is outside the current value")
    return value[:start] + replacement + value[end:]


def _operand_at_span(value, locator: str, start: int, end: int, path=""):
    if isinstance(value, dict):
        found = [
            result for key, child in value.items()
            if (result := _operand_at_span(
                child, locator, start, end,
                path + "/" + _pointer_part(key))) is not None]
        return found[0] if len(found) == 1 else None
    if isinstance(value, list):
        found = [
            result for index, child in enumerate(value)
            if (result := _operand_at_span(
                child, locator, start, end,
                path + "/" + str(index))) is not None]
        return found[0] if len(found) == 1 else None
    if path != locator or not isinstance(value, str):
        return None
    if start < 0 or end <= start or end > len(value):
        return None
    return value[start:end]


def _punctuation_skeleton(value: str) -> str:
    return "".join(character for character in str(value)
                   if not character.isalnum())


def _preserves_string_role(operand: str, replacement: str, token: str) -> bool:
    """Require the same delimiter/whitespace shell after removing the nonce."""
    if not all(isinstance(item, str) for item in (operand, replacement, token)):
        return False
    if not token or replacement.count(token) != 1:
        return False
    if "://" in operand:
        operand_scheme = operand.partition("://")[0]
        replacement_scheme = replacement.partition("://")[0]
        if replacement_scheme != operand_scheme:
            return False
    return (_punctuation_skeleton(operand) ==
            _punctuation_skeleton(replacement.replace(token, "", 1)))


def _replace_unique_operand(value, operand: str, replacement: str):
    """Replace one exact string span only when it occurs once in the tree."""
    matches = 0

    def visit(node):
        nonlocal matches
        if isinstance(node, dict):
            return {key: visit(child) for key, child in node.items()}
        if isinstance(node, list):
            return [visit(child) for child in node]
        if isinstance(node, str):
            count = node.count(operand)
            matches += count
            return node.replace(operand, replacement, 1) if count else node
        return node

    edited = visit(value)
    return edited if matches == 1 else None


def _changes_atomic_collection_member(before, after, parent_is_collection=False) -> bool:
    if isinstance(before, dict) and isinstance(after, dict):
        return any(_changes_atomic_collection_member(before[key], after[key], False)
                   for key in before if before[key] != after[key])
    if isinstance(before, list) and isinstance(after, list):
        return any(_changes_atomic_collection_member(left, right, True)
                   for left, right in zip(before, after) if left != right)
    return bool(parent_is_collection and before != after)


def _valid_rewrite(before, after, token: str) -> tuple[bool, int]:
    """Accept string-leaf edits only; preserve the complete structural skeleton."""
    if isinstance(before, dict):
        if not isinstance(after, dict) or list(before) != list(after):
            return False, 0
        checks = [_valid_rewrite(before[key], after[key], token) for key in before]
    elif isinstance(before, list):
        if not isinstance(after, list) or len(before) != len(after):
            return False, 0
        checks = [_valid_rewrite(left, right, token) for left, right in zip(before, after)]
    elif isinstance(before, str):
        if before == after:
            return True, 0
        if not isinstance(after, str):
            return False, 0
        try:
            before_json, after_json = json.loads(before), json.loads(after)
        except (json.JSONDecodeError, TypeError):
            return token in after, 1
        return _valid_rewrite(before_json, after_json, token)
    else:
        return before == after, 0
    return all(ok for ok, _ in checks), sum(changes for _, changes in checks)


def _restore(template, value):
    validate = getattr(type(template), "model_validate", None)
    if callable(validate):
        return validate(value)
    if isinstance(template, dict):
        return {key: _restore(template[key], value[key]) for key in template}
    if isinstance(template, tuple):
        return tuple(_restore(item, child) for item, child in zip(template, value))
    if isinstance(template, list):
        return [_restore(item, child) for item, child in zip(template, value)]
    return value


def replace_observation(observation, payload):
    """Install a validated, shape-preserving observation produced by placement."""
    if isinstance(observation, str):
        return payload if isinstance(payload, str) else json.dumps(
            payload, ensure_ascii=False, default=str)
    try:
        return _restore(observation, payload)
    except (KeyError, TypeError, ValueError):
        return observation
