"""Tree-sitter based AST parser for Python source files."""

from __future__ import annotations

from typing import List, Optional, Tuple
from tree_sitter import Language, Node, Parser
import tree_sitter_python as tspython

from codepulse.core.models import (
    ChangeStatus,
    FileInfo,
    ParseResult,
    Relationship,
    RelationshipType,
    Symbol,
    SymbolType,
)
from codepulse.core.repository_scanner.parser_base import BaseLanguageParser


class PythonParser(BaseLanguageParser):
    def __init__(self) -> None:
        self.language = Language(tspython.language())
        self.parser = Parser(self.language)

    @property
    def language_name(self) -> str:
        return "python"

    @property
    def file_extensions(self) -> List[str]:
        return [".py"]

    def parse_code(self, file_path: str, code_bytes: bytes, repo_id: str = "default") -> ParseResult:
        clean_path = file_path.replace("\\", "/")
        file_info = self.build_file_info(clean_path, code_bytes)
        symbols: List[Symbol] = []
        relationships: List[Relationship] = []
        errors: List[str] = []

        # Create root File symbol
        file_symbol_id = f"{clean_path}::file::{clean_path}"
        file_symbol = Symbol(
            id=file_symbol_id,
            repo_id=repo_id,
            file_path=clean_path,
            name=clean_path,
            symbol_type=SymbolType.FILE,
            parent_symbol_id=None,
            start_line=1,
            end_line=len(code_bytes.splitlines()) or 1,
            start_byte=0,
            end_byte=len(code_bytes),
            content_hash=file_info.sha256,
        )
        symbols.append(file_symbol)

        try:
            tree = self.parser.parse(code_bytes)
        except Exception as e:
            errors.append(f"Tree-sitter parse error: {str(e)}")
            return ParseResult(file_info=file_info, symbols=symbols, relationships=relationships, errors=errors)

        root = tree.root_node
        self._traverse_node(
            node=root,
            code_bytes=code_bytes,
            clean_path=clean_path,
            repo_id=repo_id,
            parent_symbol=file_symbol,
            symbols=symbols,
            relationships=relationships,
        )

        return ParseResult(
            file_info=file_info,
            symbols=symbols,
            relationships=relationships,
            errors=errors,
        )

    def _traverse_node(
        self,
        node: Node,
        code_bytes: bytes,
        clean_path: str,
        repo_id: str,
        parent_symbol: Symbol,
        symbols: List[Symbol],
        relationships: List[Relationship],
    ) -> None:
        for child in node.children:
            if child.type == "class_definition":
                self._handle_class(
                    child, code_bytes, clean_path, repo_id, parent_symbol, symbols, relationships
                )
            elif child.type == "function_definition":
                self._handle_function(
                    child, code_bytes, clean_path, repo_id, parent_symbol, symbols, relationships
                )
            elif child.type in ("import_statement", "import_from_statement"):
                self._handle_import(child, code_bytes, clean_path, parent_symbol, relationships)
            else:
                self._traverse_node(
                    child, code_bytes, clean_path, repo_id, parent_symbol, symbols, relationships
                )

    def _handle_class(
        self,
        node: Node,
        code_bytes: bytes,
        clean_path: str,
        repo_id: str,
        parent_symbol: Symbol,
        symbols: List[Symbol],
        relationships: List[Relationship],
    ) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        class_name = self._node_text(name_node, code_bytes)
        class_id = Symbol.build_id(clean_path, class_name, SymbolType.CLASS)

        # Docstring extraction
        docstring = self._extract_docstring(node, code_bytes)
        body_node = node.child_by_field_name("body")
        content_hash = self.compute_symbol_hash(node.text)

        class_symbol = Symbol(
            id=class_id,
            repo_id=repo_id,
            file_path=clean_path,
            name=class_name,
            symbol_type=SymbolType.CLASS,
            parent_symbol_id=parent_symbol.id,
            start_line=node.start_point.row + 1,
            end_line=node.end_point.row + 1,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
            signature=f"class {class_name}",
            docstring=docstring,
            content_hash=content_hash,
        )
        symbols.append(class_symbol)

        # File CONTAINS Class
        relationships.append(
            Relationship(
                source_id=parent_symbol.id,
                target_id=class_id,
                relationship_type=RelationshipType.CONTAINS,
            )
        )

        # Superclasses (INHERITS)
        superclasses_node = node.child_by_field_name("superclasses")
        if superclasses_node:
            for sc in superclasses_node.children:
                if sc.type in ("identifier", "attribute"):
                    sc_name = self._node_text(sc, code_bytes)
                    relationships.append(
                        Relationship(
                            source_id=class_id,
                            target_id=sc_name,
                            relationship_type=RelationshipType.INHERITS,
                            metadata={"base_class": sc_name},
                        )
                    )

        # Methods inside class body
        if body_node:
            for child in body_node.children:
                if child.type == "function_definition":
                    self._handle_function(
                        child,
                        code_bytes,
                        clean_path,
                        repo_id,
                        parent_symbol=class_symbol,
                        symbols=symbols,
                        relationships=relationships,
                        is_method=True,
                    )
                else:
                    self._traverse_node(
                        child, code_bytes, clean_path, repo_id, class_symbol, symbols, relationships
                    )

    def _handle_function(
        self,
        node: Node,
        code_bytes: bytes,
        clean_path: str,
        repo_id: str,
        parent_symbol: Symbol,
        symbols: List[Symbol],
        relationships: List[Relationship],
        is_method: bool = False,
    ) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        func_name = self._node_text(name_node, code_bytes)
        sym_type = SymbolType.METHOD if is_method else SymbolType.FUNCTION
        parent_prefix = parent_symbol.name if is_method else None
        func_id = Symbol.build_id(clean_path, func_name, sym_type, parent_prefix)

        # Extract signature
        params_node = node.child_by_field_name("parameters")
        params_text = self._node_text(params_node, code_bytes) if params_node else "()"
        return_type_node = node.child_by_field_name("return_type")
        return_text = f" -> {self._node_text(return_type_node, code_bytes)}" if return_type_node else ""
        signature = f"def {func_name}{params_text}{return_text}"

        docstring = self._extract_docstring(node, code_bytes)
        content_hash = self.compute_symbol_hash(node.text)

        func_symbol = Symbol(
            id=func_id,
            repo_id=repo_id,
            file_path=clean_path,
            name=func_name,
            symbol_type=sym_type,
            parent_symbol_id=parent_symbol.id,
            start_line=node.start_point.row + 1,
            end_line=node.end_point.row + 1,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
            signature=signature,
            docstring=docstring,
            content_hash=content_hash,
        )
        symbols.append(func_symbol)

        # Parent CONTAINS Function/Method
        relationships.append(
            Relationship(
                source_id=parent_symbol.id,
                target_id=func_id,
                relationship_type=RelationshipType.CONTAINS,
            )
        )

        # Extract function call invocations within this function's body
        self._extract_calls(node, code_bytes, func_id, relationships)

    def _handle_import(
        self,
        node: Node,
        code_bytes: bytes,
        clean_path: str,
        parent_symbol: Symbol,
        relationships: List[Relationship],
    ) -> None:
        import_text = self._node_text(node, code_bytes).strip()
        relationships.append(
            Relationship(
                source_id=parent_symbol.id,
                target_id=import_text,
                relationship_type=RelationshipType.IMPORTS,
                metadata={"raw_import": import_text},
            )
        )

    def _extract_calls(
        self,
        node: Node,
        code_bytes: bytes,
        caller_id: str,
        relationships: List[Relationship],
    ) -> None:
        calls = []
        stack = [node]
        while stack:
            curr = stack.pop()
            if curr.type == "call":
                func_child = curr.child_by_field_name("function")
                if func_child:
                    callee_name = self._node_text(func_child, code_bytes)
                    calls.append(callee_name)
                    if "." in callee_name:
                        calls.append(callee_name.split(".")[-1])
            for child in curr.children:
                # Do not re-enter nested function definitions to avoid attributing nested calls to parent
                if child.type != "function_definition":
                    stack.append(child)

        for callee in set(calls):
            relationships.append(
                Relationship(
                    source_id=caller_id,
                    target_id=callee,
                    relationship_type=RelationshipType.CALLS,
                    metadata={"callee_expression": callee},
                )
            )

    @staticmethod
    def _extract_docstring(node: Node, code_bytes: bytes) -> Optional[str]:
        body_node = node.child_by_field_name("body")
        if not body_node or not body_node.children:
            return None
        first_child = body_node.children[0]
        if first_child.type == "expression_statement":
            expr = first_child.children[0] if first_child.children else None
            if expr and expr.type == "string":
                text = expr.text.decode("utf-8", errors="replace").strip("\"'")
                return text.strip()
        return None

    @staticmethod
    def _node_text(node: Node, code_bytes: bytes) -> str:
        return code_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")
