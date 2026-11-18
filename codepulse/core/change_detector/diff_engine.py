"""Symbol-level diffing engine for fine-grained AST modification analysis."""

from __future__ import annotations

import difflib
from typing import Dict, List, Optional, Set, Tuple

from codepulse.core.models import (
    ChangeStatus,
    Symbol,
    SymbolDiff,
    SymbolType,
)


class DiffEngine:
    @staticmethod
    def compute_text_diff(
        old_text: str,
        new_text: str,
        from_name: str = "before",
        to_name: str = "after",
    ) -> str:
        """Computes a standard unified diff string between two text snippets."""
        old_lines = old_text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=from_name,
            tofile=to_name,
            lineterm="",
        )
        return "".join(diff)

    @classmethod
    def compare_symbols(
        cls,
        old_symbols: List[Symbol],
        new_symbols: List[Symbol],
        file_path: str,
        old_code_bytes: Optional[bytes] = None,
        new_code_bytes: Optional[bytes] = None,
    ) -> List[SymbolDiff]:
        """Compares prior and current symbols of a file and produces symbol-level diffs."""
        old_by_id: Dict[str, Symbol] = {s.id: s for s in old_symbols if s.symbol_type != SymbolType.FILE}
        new_by_id: Dict[str, Symbol] = {s.id: s for s in new_symbols if s.symbol_type != SymbolType.FILE}

        # Index old symbols by content hash for rename detection
        old_by_hash: Dict[str, Symbol] = {
            s.content_hash: s for s in old_by_id.values() if s.content_hash
        }

        diffs: List[SymbolDiff] = []
        matched_old_ids: Set[str] = set()

        old_lines = old_code_bytes.decode("utf-8", errors="replace").splitlines() if old_code_bytes else []
        new_lines = new_code_bytes.decode("utf-8", errors="replace").splitlines() if new_code_bytes else []

        for new_id, new_sym in new_by_id.items():
            if new_id in old_by_id:
                old_sym = old_by_id[new_id]
                matched_old_ids.add(old_id := new_id)

                if old_sym.content_hash == new_sym.content_hash:
                    # Symbol is completely identical
                    diffs.append(
                        SymbolDiff(
                            symbol_id=new_id,
                            symbol_name=new_sym.name,
                            symbol_type=new_sym.symbol_type,
                            file_path=file_path,
                            status=ChangeStatus.UNCHANGED,
                            old_signature=old_sym.signature,
                            new_signature=new_sym.signature,
                            old_start_line=old_sym.start_line,
                            new_start_line=new_sym.start_line,
                        )
                    )
                else:
                    # Symbol was modified!
                    diff_text = cls._extract_snippet_diff(
                        old_sym, new_sym, old_lines, new_lines
                    )
                    diffs.append(
                        SymbolDiff(
                            symbol_id=new_id,
                            symbol_name=new_sym.name,
                            symbol_type=new_sym.symbol_type,
                            file_path=file_path,
                            status=ChangeStatus.MODIFIED,
                            diff_text=diff_text,
                            old_signature=old_sym.signature,
                            new_signature=new_sym.signature,
                            old_start_line=old_sym.start_line,
                            new_start_line=new_sym.start_line,
                        )
                    )
            else:
                # Check for possible rename (same content hash as a deleted symbol)
                if new_sym.content_hash and new_sym.content_hash in old_by_hash:
                    candidate = old_by_hash[new_sym.content_hash]
                    if candidate.id not in new_by_id:
                        matched_old_ids.add(candidate.id)
                        diffs.append(
                            SymbolDiff(
                                symbol_id=new_id,
                                symbol_name=new_sym.name,
                                symbol_type=new_sym.symbol_type,
                                file_path=file_path,
                                status=ChangeStatus.RENAMED,
                                diff_text=f"Renamed from {candidate.name} to {new_sym.name}",
                                old_signature=candidate.signature,
                                new_signature=new_sym.signature,
                                old_start_line=candidate.start_line,
                                new_start_line=new_sym.start_line,
                            )
                        )
                        continue

                # Brand new symbol added
                diff_text = ""
                if new_lines and 1 <= new_sym.start_line <= len(new_lines):
                    snippet = "\n".join(new_lines[new_sym.start_line - 1 : new_sym.end_line])
                    diff_text = f"+ {snippet}"

                diffs.append(
                    SymbolDiff(
                        symbol_id=new_id,
                        symbol_name=new_sym.name,
                        symbol_type=new_sym.symbol_type,
                        file_path=file_path,
                        status=ChangeStatus.ADDED,
                        diff_text=diff_text,
                        new_signature=new_sym.signature,
                        new_start_line=new_sym.start_line,
                    )
                )

        # Process deleted symbols
        for old_id, old_sym in old_by_id.items():
            if old_id not in matched_old_ids:
                diff_text = ""
                if old_lines and 1 <= old_sym.start_line <= len(old_lines):
                    snippet = "\n".join(old_lines[old_sym.start_line - 1 : old_sym.end_line])
                    diff_text = f"- {snippet}"

                diffs.append(
                    SymbolDiff(
                        symbol_id=old_id,
                        symbol_name=old_sym.name,
                        symbol_type=old_sym.symbol_type,
                        file_path=file_path,
                        status=ChangeStatus.DELETED,
                        diff_text=diff_text,
                        old_signature=old_sym.signature,
                        old_start_line=old_sym.start_line,
                    )
                )

        return diffs

    @classmethod
    def _extract_snippet_diff(
        cls,
        old_sym: Symbol,
        new_sym: Symbol,
        old_lines: List[str],
        new_lines: List[str],
    ) -> str:
        old_snip = (
            "\n".join(old_lines[old_sym.start_line - 1 : old_sym.end_line])
            if old_lines and 1 <= old_sym.start_line <= len(old_lines)
            else ""
        )
        new_snip = (
            "\n".join(new_lines[new_sym.start_line - 1 : new_sym.end_line])
            if new_lines and 1 <= new_sym.start_line <= len(new_lines)
            else ""
        )
        return cls.compute_text_diff(
            old_snip,
            new_snip,
            from_name=f"{old_sym.name} (v1)",
            to_name=f"{new_sym.name} (v2)",
        )
