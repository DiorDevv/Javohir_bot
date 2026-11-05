from __future__ import annotations

import pytest

from bot.utils.validators import check_text, validate_full_name


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Aliyev Vali", "Aliyev Vali"),
        ("  O'ktam   G'ulomov  ", "O'ktam G'ulomov"),
        ("Ahmedova Gulnoza Botir qizi", "Ahmedova Gulnoza Botir qizi"),
        ("Алиев Вали", "Алиев Вали"),
        ("Rahimova-Karimova Dilnoza", "Rahimova-Karimova Dilnoza"),
        ("Oʻralov Shoʻxrat", "Oʻralov Shoʻxrat"),
    ],
)
def test_valid_names(raw: str, expected: str) -> None:
    assert validate_full_name(raw) == expected


@pytest.mark.parametrize("raw", ["", "Vali", "Vali 123", "Vali_ Aliyev", "Vali @aliyev", "- -", None])
def test_invalid_names(raw: str | None) -> None:
    assert validate_full_name(raw) is None


def test_check_text() -> None:
    assert check_text("  salom ", 10).value == "salom"
    assert check_text("   ", 10).error == "empty"
    assert check_text("x" * 11, 10).error == "too_long"
