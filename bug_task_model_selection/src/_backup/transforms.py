from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Protocol


class Obfuscator(Protocol):
    def obfuscate(self, code: str) -> tuple[str, dict[str, Any]]: ...


@dataclass(frozen=True)
class IdentifierHashObfuscator:
    # Light-weight deterministic obfuscation with zero external deps.
    # Designed as a drop-in that can later be replaced by a parser-based obfuscator.

    def obfuscate(self, code: str) -> tuple[str, dict[str, Any]]:
        import re

        keywords = {
            "abstract",
            "assert",
            "boolean",
            "break",
            "byte",
            "case",
            "catch",
            "char",
            "class",
            "const",
            "continue",
            "default",
            "do",
            "double",
            "else",
            "enum",
            "extends",
            "final",
            "finally",
            "float",
            "for",
            "goto",
            "if",
            "implements",
            "import",
            "instanceof",
            "int",
            "interface",
            "long",
            "native",
            "new",
            "package",
            "private",
            "protected",
            "public",
            "return",
            "short",
            "static",
            "strictfp",
            "super",
            "switch",
            "synchronized",
            "this",
            "throw",
            "throws",
            "transient",
            "try",
            "void",
            "volatile",
            "while",
            "true",
            "false",
            "null",
        }

        ident_re = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
        mapping: dict[str, str] = {}

        def repl(m: re.Match[str]) -> str:
            tok = m.group(0)
            if tok in keywords:
                return tok
            if tok not in mapping:
                h = hashlib.sha1(tok.encode("utf-8")).hexdigest()[:8]
                mapping[tok] = f"ID_{h}"
            return mapping[tok]

        obf = ident_re.sub(repl, code)
        return obf, {"type": "identifier_hash", "mapping_size": len(mapping)}


def mixed_code_variant(code: str) -> tuple[str, dict[str, Any]]:
    header = "// MIXED_VIEW\n"
    return header + code, {"type": "prepend_header", "header": "// MIXED_VIEW"}
