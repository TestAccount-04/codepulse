"""Tests for language parsers (Python, JS, TS, Java) with Tree-sitter."""

from codepulse.core.models import RelationshipType, SymbolType
from codepulse.core.repository_scanner.java_parser import JavaParser
from codepulse.core.repository_scanner.javascript_parser import JavaScriptParser
from codepulse.core.repository_scanner.python_parser import PythonParser
from codepulse.core.repository_scanner.typescript_parser import TypeScriptParser


def test_python_parser():
    parser = PythonParser()
    code = b"""
import os
from datetime import datetime

class AuthService(BaseAuth):
    \"\"\"Service managing user authentication.\"\"\"

    def __init__(self, secret: str):
        self.secret = secret

    def authenticate_user(self, token: str) -> bool:
        \"\"\"Validates the given JWT token.\"\"\"
        if not self.validate_token(token):
            return False
        return True

    def validate_token(self, token: str) -> bool:
        return len(token) > 10

def helper_calc(x: int) -> int:
    return x * 2
"""
    result = parser.parse_code("auth/service.py", code)
    assert len(result.errors) == 0

    sym_names = {s.name: s for s in result.symbols}
    assert "AuthService" in sym_names
    assert sym_names["AuthService"].symbol_type == SymbolType.CLASS
    assert sym_names["AuthService"].docstring == "Service managing user authentication."

    assert "authenticate_user" in sym_names
    auth_method = sym_names["authenticate_user"]
    assert auth_method.symbol_type == SymbolType.METHOD
    assert auth_method.parent_symbol_id == sym_names["AuthService"].id
    assert "def authenticate_user" in (auth_method.signature or "")

    assert "helper_calc" in sym_names
    assert sym_names["helper_calc"].symbol_type == SymbolType.FUNCTION

    # Check relationships
    rels = result.relationships
    inherits_rels = [r for r in rels if r.relationship_type == RelationshipType.INHERITS]
    assert len(inherits_rels) == 1
    assert inherits_rels[0].target_id == "BaseAuth"

    contains_rels = [r for r in rels if r.relationship_type == RelationshipType.CONTAINS]
    assert len(contains_rels) >= 4  # File->Class, Class->init, Class->auth, Class->val, File->helper

    call_rels = [r for r in rels if r.relationship_type == RelationshipType.CALLS]
    call_targets = {r.target_id for r in call_rels}
    assert any("validate_token" in t for t in call_targets)


def test_javascript_parser():
    parser = JavaScriptParser()
    code = b"""
import { formatName } from './utils';

class OrderManager extends BaseManager {
    processOrder(orderId) {
        return sendNotification(orderId);
    }
}

const sumItems = (a, b) => a + b;

function calculateTax(amount) {
    return amount * 0.1;
}
"""
    result = parser.parse_code("src/order.js", code)
    assert len(result.errors) == 0

    sym_names = {s.name: s for s in result.symbols}
    assert "OrderManager" in sym_names
    assert sym_names["OrderManager"].symbol_type == SymbolType.CLASS

    assert "processOrder" in sym_names
    assert sym_names["processOrder"].symbol_type == SymbolType.METHOD

    assert "sumItems" in sym_names
    assert sym_names["sumItems"].symbol_type == SymbolType.FUNCTION

    assert "calculateTax" in sym_names
    assert sym_names["calculateTax"].symbol_type == SymbolType.FUNCTION

    inherits_rels = [r for r in result.relationships if r.relationship_type == RelationshipType.INHERITS]
    assert len(inherits_rels) == 1
    assert "BaseManager" in inherits_rels[0].target_id


def test_typescript_parser():
    parser = TypeScriptParser()
    code = b"""
import axios from 'axios';

export interface UserProfile {
    id: string;
    email: string;
}

export class UserService {
    async fetchUser(id: string): Promise<UserProfile> {
        return axios.get(`/users/${id}`);
    }
}
"""
    result = parser.parse_code("src/user.ts", code)
    assert len(result.errors) == 0

    sym_names = {s.name: s for s in result.symbols}
    assert "UserProfile" in sym_names
    assert sym_names["UserProfile"].symbol_type == SymbolType.INTERFACE

    assert "UserService" in sym_names
    assert sym_names["UserService"].symbol_type == SymbolType.CLASS

    assert "fetchUser" in sym_names
    assert sym_names["fetchUser"].symbol_type == SymbolType.METHOD


def test_java_parser():
    parser = JavaParser()
    code = b"""
package com.codepulse.test;

import java.util.List;

public class PaymentProcessor extends BaseProcessor implements IPayment {
    private final String apiKey;

    public PaymentProcessor(String apiKey) {
        this.apiKey = apiKey;
    }

    public boolean executePayment(double amount) {
        logTransaction(amount);
        return true;
    }
}
"""
    result = parser.parse_code("src/PaymentProcessor.java", code)
    assert len(result.errors) == 0

    classes = [s for s in result.symbols if s.symbol_type == SymbolType.CLASS]
    assert any(c.name == "PaymentProcessor" for c in classes)

    methods = [s for s in result.symbols if s.symbol_type == SymbolType.METHOD]
    assert any(m.name == "executePayment" for m in methods)

    inherits_rels = [r for r in result.relationships if r.relationship_type == RelationshipType.INHERITS]
    assert len(inherits_rels) >= 2  # extends BaseProcessor, implements IPayment
