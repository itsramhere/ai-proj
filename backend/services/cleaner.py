import re

def clean_markdown_notes(content: str) -> str:
    """
    Cleans markdown notes by stripping outer code fences (e.g. ```markdown ... ```)
    that LLMs frequently wrap their responses in, preventing the entire note
    from being rendered as a giant monolithic code block.
    """
    if not content:
        return ""

    text = content.strip()

    # Pattern: starts with ```markdown or ```md or ```
    match = re.match(r"^```(?:markdown|md)?\s*\n([\s\S]*?)(?:\n```\s*(?:## Charts[\s\S]*|\s*$)|\Z)", text)
    if match:
        body = match.group(1).rstrip()
        # Check if there is an appended ## Charts section after the closing fence
        charts_idx = text.find("## Charts")
        if charts_idx != -1 and charts_idx > match.start(1):
            charts_part = text[charts_idx:].strip()
            # If the body still has trailing ``` before charts, strip it
            body = re.sub(r"\n```\s*$", "", body)
            return f"{body}\n\n{charts_part}".strip()
        else:
            # Strip any trailing closing fence
            body = re.sub(r"\n```\s*$", "", body)
            return body.strip()

    # Fallback check for lone leading fence
    if re.match(r"^```(?:markdown|md)?\s*\n", text):
        text = re.sub(r"^```(?:markdown|md)?\s*\n", "", text)
        # Remove matching closing fence before ## Charts
        text = re.sub(r"\n```\s*\n(## Charts)", r"\n\n\1", text)
        text = re.sub(r"\n```\s*$", "", text)

    return text.strip()


def sanitize_mermaid(diagram: str) -> str:
    """
    Ensures Mermaid diagram code has valid syntax.
    Quotes node labels into safe id["label"] format, strips internal double quotes,
    fixes unbalanced brackets, and removes markdown code fences.
    """
    if not diagram:
        return ""

    # Strip code fences
    d = diagram.strip()
    d = re.sub(r"^```(?:mermaid)?\s*", "", d)
    d = re.sub(r"\s*```$", "", d)
    d = d.strip()

    if not d:
        return ""

    lines = d.splitlines()
    cleaned_lines = []

    has_header = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if re.match(r"^(graph|flowchart|sequenceDiagram|classDiagram|stateDiagram|erDiagram|journey|gantt|pie)\b", stripped):
            cleaned_lines.append(stripped)
            has_header = True
            continue

        # Convert node declarations:
        # e.g., A(Label) -> A["Label"], A[Label] -> A["Label"]
        # Handle lines with arrows: Node1 --> Node2, etc.
        # We split by arrows or delimiters: -->, ---, -.->, ==>, etc.
        arrow_pattern = r"(\s*(?:-->|---|-.->|==>|--\s*[^-\n]+\s*-->)\s*)"
        parts = re.split(arrow_pattern, stripped)

        transformed_parts = []
        for part in parts:
            if re.match(arrow_pattern, part):
                transformed_parts.append(part)
                continue

            token = part.strip()
            if not token:
                continue

            # Check if token matches node with label: e.g. E(text) or E[text] or E{text}
            node_match = re.match(r"^([a-zA-Z0-9_]+)\s*[\(\[\{]([\s\S]*)[\)\]\}]$", token)
            if node_match:
                node_id = node_match.group(1)
                label = node_match.group(2).strip()
                # Clean label: strip outer quotes if any, convert inner quotes to single quotes
                label = label.strip("\"'")
                label = label.replace('"', "'")
                # Remove any leftover unpaired parentheses
                open_cnt = label.count("(")
                close_cnt = label.count(")")
                if open_cnt > close_cnt:
                    label += ")" * (open_cnt - close_cnt)
                elif close_cnt > open_cnt:
                    label = "(" * (close_cnt - open_cnt) + label

                transformed_parts.append(f'{node_id}["{label}"]')
            else:
                # Token might be just node_id, or has malformed unclosed parenthesis like:
                # L(Gpu Tnternc vRAM External F ... (fighls 3)
                malformed = re.match(r"^([a-zA-Z0-9_]+)\s*[\(\[\{]([\s\S]+)$", token)
                if malformed:
                    node_id = malformed.group(1)
                    label = malformed.group(2).strip()
                    label = label.strip("\"'()[]{}")
                    label = label.replace('"', "'")
                    transformed_parts.append(f'{node_id}["{label}"]')
                else:
                    transformed_parts.append(token)

        cleaned_line = "".join(transformed_parts)
        cleaned_lines.append("    " + cleaned_line.strip())

    if not has_header:
        cleaned_lines.insert(0, "flowchart TD")

    return "\n".join(cleaned_lines)
