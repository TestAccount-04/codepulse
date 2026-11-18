"""Tests for DiffEngine symbol-level change detection."""

from codepulse.core.change_detector.diff_engine import DiffEngine
from codepulse.core.models import ChangeStatus, Symbol, SymbolType


def test_symbol_level_modification_isolation():
    """Verify modifying method A leaves method B UNCHANGED."""
    sym_a_old = Symbol(
        id="app.py::function::calc_total",
        file_path="app.py",
        name="calc_total",
        symbol_type=SymbolType.FUNCTION,
        start_line=1,
        end_line=3,
        content_hash="old_hash_a",
    )
    sym_b_old = Symbol(
        id="app.py::function::print_receipt",
        file_path="app.py",
        name="print_receipt",
        symbol_type=SymbolType.FUNCTION,
        start_line=5,
        end_line=7,
        content_hash="same_hash_b",
    )

    # New version: calc_total is modified, print_receipt is identical
    sym_a_new = Symbol(
        id="app.py::function::calc_total",
        file_path="app.py",
        name="calc_total",
        symbol_type=SymbolType.FUNCTION,
        start_line=1,
        end_line=4,
        content_hash="new_hash_a",
    )
    sym_b_new = Symbol(
        id="app.py::function::print_receipt",
        file_path="app.py",
        name="print_receipt",
        symbol_type=SymbolType.FUNCTION,
        start_line=6,
        end_line=8,
        content_hash="same_hash_b",
    )

    old_code = b"def calc_total():\n    return 10\n\ndef print_receipt():\n    pass\n"
    new_code = b"def calc_total():\n    # updated\n    return 20\n\ndef print_receipt():\n    pass\n"

    diffs = DiffEngine.compare_symbols(
        old_symbols=[sym_a_old, sym_b_old],
        new_symbols=[sym_a_new, sym_b_new],
        file_path="app.py",
        old_code_bytes=old_code,
        new_code_bytes=new_code,
    )

    diff_map = {d.symbol_name: d for d in diffs}
    assert diff_map["calc_total"].status == ChangeStatus.MODIFIED
    assert diff_map["print_receipt"].status == ChangeStatus.UNCHANGED
    assert diff_map["calc_total"].diff_text is not None


def test_symbol_addition_and_deletion():
    old_sym = Symbol(
        id="service.py::function::deprecated_fn",
        file_path="service.py",
        name="deprecated_fn",
        symbol_type=SymbolType.FUNCTION,
        start_line=1,
        end_line=3,
        content_hash="hash_dep",
    )

    new_sym = Symbol(
        id="service.py::function::brand_new_fn",
        file_path="service.py",
        name="brand_new_fn",
        symbol_type=SymbolType.FUNCTION,
        start_line=1,
        end_line=3,
        content_hash="hash_brand_new",
    )

    diffs = DiffEngine.compare_symbols(
        old_symbols=[old_sym],
        new_symbols=[new_sym],
        file_path="service.py",
    )

    diff_map = {d.symbol_name: d for d in diffs}
    assert diff_map["deprecated_fn"].status == ChangeStatus.DELETED
    assert diff_map["brand_new_fn"].status == ChangeStatus.ADDED


def test_symbol_rename_detection():
    old_sym = Symbol(
        id="math.py::function::old_calc",
        file_path="math.py",
        name="old_calc",
        symbol_type=SymbolType.FUNCTION,
        start_line=1,
        end_line=3,
        content_hash="identical_hash_123",
    )

    new_sym = Symbol(
        id="math.py::function::new_calc",
        file_path="math.py",
        name="new_calc",
        symbol_type=SymbolType.FUNCTION,
        start_line=1,
        end_line=3,
        content_hash="identical_hash_123",
    )

    diffs = DiffEngine.compare_symbols(
        old_symbols=[old_sym],
        new_symbols=[new_sym],
        file_path="math.py",
    )

    assert len(diffs) == 1
    assert diffs[0].status == ChangeStatus.RENAMED
    assert diffs[0].symbol_name == "new_calc"
