"""Tests for the book_app CLI handlers."""

import sys
from unittest.mock import patch

import pytest

from book_app import (
    handle_add,
    handle_find,
    handle_list,
    handle_read,
    handle_remove,
    main,
    show_books,
    MAX_YEAR,
    MIN_YEAR,
)
from books import Book, BookCollection


@pytest.fixture
def collection(tmp_path, monkeypatch):
    """Create a BookCollection that uses a temporary data file."""
    monkeypatch.setattr("books.DATA_FILE", str(tmp_path / "data.json"))
    col = BookCollection()
    col.add_book("Dune", "Frank Herbert", 1965)
    col.add_book("Neuromancer", "William Gibson", 1984)
    return col


class TestShowBooks:
    def test_shows_books(self, collection, capsys):
        show_books(collection.list_books())
        output = capsys.readouterr().out
        assert "Dune" in output
        assert "Frank Herbert" in output
        assert "1965" in output

    def test_empty_list(self, capsys):
        show_books([])
        output = capsys.readouterr().out
        assert "No books found." in output


class TestHandleList:
    def test_lists_all_books(self, collection, capsys):
        handle_list(collection)
        output = capsys.readouterr().out
        assert "Dune" in output
        assert "Neuromancer" in output


class TestHandleAdd:
    def test_add_valid_book(self, collection, capsys):
        with patch("builtins.input", side_effect=["The Hobbit", "Tolkien", "1937"]):
            handle_add(collection)
        output = capsys.readouterr().out
        assert "Book added successfully" in output
        assert len(collection.list_books()) == 3

    def test_add_empty_title(self, collection, capsys):
        with patch("builtins.input", side_effect=[""]):
            handle_add(collection)
        output = capsys.readouterr().out
        assert "Title is required" in output
        assert len(collection.list_books()) == 2

    def test_add_empty_author(self, collection, capsys):
        with patch("builtins.input", side_effect=["Title", ""]):
            handle_add(collection)
        output = capsys.readouterr().out
        assert "Author is required" in output
        assert len(collection.list_books()) == 2

    def test_add_invalid_year(self, collection, capsys):
        with patch("builtins.input", side_effect=["Title", "Author", "abc"]):
            handle_add(collection)
        output = capsys.readouterr().out
        assert "Error" in output
        assert len(collection.list_books()) == 2

    def test_add_year_out_of_range(self, collection, capsys):
        with patch("builtins.input", side_effect=["Title", "Author", "500"]):
            handle_add(collection)
        output = capsys.readouterr().out
        assert f"between {MIN_YEAR} and {MAX_YEAR}" in output
        assert len(collection.list_books()) == 2

    def test_add_empty_year_defaults_to_zero(self, collection, capsys):
        with patch("builtins.input", side_effect=["Title", "Author", ""]):
            handle_add(collection)
        output = capsys.readouterr().out
        assert "Book added successfully" in output
        added = collection.find_book_by_title("Title")
        assert added.year == 0


class TestHandleRemove:
    def test_remove_existing_book(self, collection, capsys):
        with patch("builtins.input", return_value="Dune"):
            handle_remove(collection)
        output = capsys.readouterr().out
        assert "removed successfully" in output
        assert len(collection.list_books()) == 1

    def test_remove_nonexistent_book(self, collection, capsys):
        with patch("builtins.input", return_value="Unknown"):
            handle_remove(collection)
        output = capsys.readouterr().out
        assert "not found" in output
        assert len(collection.list_books()) == 2

    def test_remove_empty_title(self, collection, capsys):
        with patch("builtins.input", return_value=""):
            handle_remove(collection)
        output = capsys.readouterr().out
        assert "Title is required" in output


class TestHandleFind:
    def test_find_existing_author(self, collection, capsys):
        with patch("builtins.input", return_value="Frank Herbert"):
            handle_find(collection)
        output = capsys.readouterr().out
        assert "Dune" in output

    def test_find_no_results(self, collection, capsys):
        with patch("builtins.input", return_value="Unknown Author"):
            handle_find(collection)
        output = capsys.readouterr().out
        assert "No books found." in output

    def test_find_empty_author(self, collection, capsys):
        with patch("builtins.input", return_value=""):
            handle_find(collection)
        output = capsys.readouterr().out
        assert "Search term is required" in output


class TestHandleRead:
    def test_mark_existing_book_as_read(self, collection, capsys):
        with patch("builtins.input", return_value="Dune"):
            handle_read(collection)
        output = capsys.readouterr().out
        assert "marked as read" in output
        book = collection.find_book_by_title("Dune")
        assert book.read is True

    def test_mark_nonexistent_book(self, collection, capsys):
        with patch("builtins.input", return_value="Unknown Book"):
            handle_read(collection)
        output = capsys.readouterr().out
        assert "not found" in output

    def test_mark_empty_title(self, collection, capsys):
        with patch("builtins.input", return_value=""):
            handle_read(collection)
        output = capsys.readouterr().out
        assert "Title is required" in output


class TestMain:
    def test_no_args_shows_help(self, collection, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["book_app.py"])
        main(collection)
        output = capsys.readouterr().out
        assert "Commands:" in output

    def test_unknown_command(self, collection, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["book_app.py", "invalid"])
        main(collection)
        output = capsys.readouterr().out
        assert "Unknown command" in output

    def test_list_command(self, collection, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["book_app.py", "list"])
        main(collection)
        output = capsys.readouterr().out
        assert "Dune" in output
