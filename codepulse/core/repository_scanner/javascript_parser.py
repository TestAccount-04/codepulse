"""Tree-sitter based AST parser for JavaScript source files."""

from __future__ import annotations

from typing import List, Optional
from tree_sitter import Language, Node, Parser
import tree_sitter_javascript as tsjs

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


class JavaScriptParser(BaseLanguageParser):
    def __init__(self) -> None:
        self.language = Language(tsjs.language())
        self.parser = Parser(self.language)

    @property
    def language_name(self) -> str:
        return "javascript"

    @property
    def file_extensions(self) -> List[str]:
        return [".js", ".jsx", ".mjs", ".cjs"]

    def parse_code(self, file_path: str, code_bytes: bytes, repo_id: str = "default") -> ParseResult:
        clean_path = file_path.replace("\\", "/")
        file_info = self.build_file_info(clean_path, code_bytes)
        symbols: List[Symbol] = []
        relationships: List[Relationship] = []
        errors: List[str] = []

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
            errors.append(f"Tree-sitter JS parse error: {str(e)}")
            return ParseResult(file_info=file_info, symbols=symbols, relationships=relationships, errors=errors)

        self._traverse_node(
            tree.root_node,
            code_bytes,
            clean_path,
            repo_id,
            file_symbol,
            symbols,
            relationships,
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
            if child.type == "class_declaration":
                self._handle_class(child, code_bytes, clean_path, repo_id, parent_symbol, symbols, relationships)
            elif child.type == "function_declaration":
                self._handle_function(child, code_bytes, clean_path, repo_id, parent_symbol, symbols, relationships)
            elif child.type in ("lexical_declaration", "variable_declaration"):
                self._handle_variable_declaration(child, code_bytes, clean_path, repo_id, parent_symbol, symbols, relationships)
            elif child.type == "import_statement":
                self._handle_import(child, code_bytes, clean_path, parent_symbol, relationships)
            else:
                self._traverse_node(child, code_bytes, clean_path, repo_id, parent_symbol, symbols, relationships)

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
            content_hash=self.compute_symbol_hash(node.text),
        )
        symbols.append(class_symbol)
        relationships.append(
            Relationship(
                source_id=parent_symbol.id,
                target_id=class_id,
                relationship_type=RelationshipType.CONTAINS,
            )
        )

        # Check inheritance
        for child in node.children:
            if child.type == "class_heritage":
                base_text = self._node_text(child, code_bytes).replace("extends", "").strip()
                if base_text:
                    relationships.append(
                        Relationship(
                            source_id=class_id,
                            target_id=base_text,
                            relationship_type=RelationshipType.INHERITS,
                            metadata={"base_class": base_text},
                        )
                    )
            elif child.type == "class_body":
                for member in child.children:
                    if member.type == "method_definition":
                        self._handle_method(
                            member, code_bytes, clean_path, repo_id, class_symbol, symbols, relationships
                        )

    def _handle_method(
        self,
        node: Node,
        code_bytes: bytes,
        clean_path: str,
        repo_id: str,
        parent_class: Symbol,
        symbols: List[Symbol],
        relationships: List[Relationship],
    ) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        method_name = self._node_text(name_node, code_bytes)
        method_id = Symbol.build_id(clean_path, method_name, SymbolType.METHOD, parent_class.name)

        params_node = node.child_by_field_name("parameters")
        params_text = self._node_text(params_node, code_bytes) if params_node else "()"
        signature = f"{method_name}{params_text}"

        method_symbol = Symbol(
            id=method_id,
            repo_id=repo_id,
            file_path=clean_path,
            name=method_name,
            symbol_type=SymbolType.METHOD,
            parent_symbol_id=parent_class.id,
            start_line=node.start_point.row + 1,
            end_line=node.end_point.row + 1,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
            signature=signature,
            content_hash=self.compute_symbol_hash(node.text),
        )
        symbols.append(method_symbol)
        relationships.append(
            Relationship(
                source_id=parent_class.id,
                target_id=method_id,
                relationship_type=RelationshipType.CONTAINS,
            )
        )
        self._extract_calls(node, code_bytes, method_id, relationships)

    def _handle_function(
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
        func_name = self._node_text(name_node, code_bytes)
        func_id = Symbol.build_id(clean_path, func_name, SymbolType.FUNCTION)

        params_node = node.child_by_field_name("parameters")
        params_text = self._node_text(params_node, code_bytes) if params_node else "()"
        signature = f"function {func_name}{params_text}"

        func_symbol = Symbol(
            id=func_id,
            repo_id=repo_id,
            file_path=clean_path,
            name=func_name,
            symbol_type=SymbolType.FUNCTION,
            parent_symbol_id=parent_symbol.id,
            start_line=node.start_point.row + 1,
            end_line=node.end_point.row + 1,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
            signature=signature,
            content_hash=self.compute_symbol_hash(node.text),
        )
        symbols.append(func_symbol)
        relationships.append(
            Relationship(
                source_id=parent_symbol.id,
                target_id=func_id,
                relationship_type=RelationshipType.CONTAINS,
            )
        )
        self._extract_calls(node, code_bytes, func_id, relationships)

    def _handle_variable_declaration(
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
            if child.type == "variable_declarator":
                name_node = child.child_by_field_name("name")
                value_node = child.child_by_field_name("value")
                if name_node and value_node and value_node.type in ("arrow_function", "function"):
                    func_name = self._node_text(name_node, code_bytes)
                    func_id = Symbol.build_id(clean_path, func_name, SymbolType.FUNCTION)

                    params_node = value_node.child_by_field_name("parameters")
                    params_text = self._node_text(params_node, code_bytes) if params_node else "()"
                    signature = f"const {func_name} = {params_text} => ..."

                    func_symbol = Symbol(
                        id=func_id,
                        repo_id=repo_id,
                        file_path=clean_path,
                        name=func_name,
                        symbol_type=SymbolType.FUNCTION,
                        parent_symbol_id=parent_symbol.id,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        start_byte=child.start_byte,
                        end_byte=child.end_byte,
                        signature=signature,
                        content_hash=self.compute_symbol_hash(child.text),
                    )
                    symbols.append(func_symbol)
                    relationships.append(
                        Relationship(
                            source_id=parent_symbol.id,
                            target_id=func_id,
                            relationship_type=RelationshipType.CONTAINS,
                        )
                    )
                    self._extract_calls(value_node, code_bytes, func_id, relationships)

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
            if curr.type == "call_expression":
                fn_child = curr.child_by_field_name("function")
                if fn_child:
                    callee_name = self._node_text(fn_child, code_bytes)
                    calls.append(callee_name)
            for child in curr.children:
                if child.type not in ("function_declaration", "arrow_function", "function"):
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
    def _node_text(node: Node, code_bytes: bytes) -> str:
        return code_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")
