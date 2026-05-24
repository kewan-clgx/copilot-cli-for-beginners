import sys
from datetime import datetime
from typing import List

from books import Book, BookCollection

MAX_YEAR = datetime.now().year + 1
MIN_YEAR = 1000


def show_books(books: List[Book]) -> None:
    """Display books in a user-friendly format."""
    if not books:
        print("No books found.")
        return

    print("\nYour Book Collection:\n")

    for index, book in enumerate(books, start=1):
        status = "✓" if book.read else " "
        print(f"{index}. [{status}] {book.title} by {book.author} ({book.year})")

    print()


def handle_list(collection: BookCollection) -> None:
    books = collection.list_books()
    show_books(books)


def handle_add(collection: BookCollection) -> None:
    print("\nAdd a New Book\n")

    title = input("Title: ").strip()
    if not title:
        print("\nError: Title is required.\n")
        return

    author = input("Author: ").strip()
    if not author:
        print("\nError: Author is required.\n")
        return

    year_str = input("Year: ").strip()

    try:
        year = int(year_str) if year_str else 0
        if year != 0 and not (MIN_YEAR <= year <= MAX_YEAR):
            print(f"\nError: Year must be between {MIN_YEAR} and {MAX_YEAR}.\n")
            return
        collection.add_book(title, author, year)
        print("\nBook added successfully.\n")
    except ValueError as e:
        print(f"\nError: {e}\n")


def handle_remove(collection: BookCollection) -> None:
    print("\nRemove a Book\n")

    title = input("Enter the title of the book to remove: ").strip()
    if not title:
        print("\nError: Title is required.\n")
        return

    removed = collection.remove_book(title)
    if removed:
        print("\nBook removed successfully.\n")
    else:
        print("\nBook not found.\n")


def handle_find(collection: BookCollection) -> None:
    print("\nSearch Books\n")

    query = input("Search term (title or author): ").strip()
    if not query:
        print("\nError: Search term is required.\n")
        return

    books = collection.search_books(query)
    show_books(books)


def handle_read(collection: BookCollection) -> None:
    print("\nMark a Book as Read\n")

    title = input("Enter the title of the book: ").strip()
    if not title:
        print("\nError: Title is required.\n")
        return

    if collection.mark_as_read(title):
        print(f"\n'{title}' marked as read.\n")
    else:
        print("\nBook not found.\n")


def handle_stats(collection: BookCollection) -> None:
    stats = collection.get_statistics()

    print("\nCollection Statistics:\n")
    print(f"  Total books:      {stats['total_books']}")
    print(f"  Books read:       {stats['books_read']}")
    print(f"  Books unread:     {stats['books_unread']}")
    print(f"  Percent read:     {stats['percent_read']}%")
    print(f"  Unique authors:   {stats['unique_authors']}")

    if stats["newest_book"]:
        b = stats["newest_book"]
        print(f"  Newest book:      {b.title} by {b.author} ({b.year})")

    if stats["oldest_book"]:
        b = stats["oldest_book"]
        print(f"  Oldest book:      {b.title} by {b.author} ({b.year})")

    print()


def show_help() -> None:
    print("""
Book Collection Helper

Commands:
  list     - Show all books
  add      - Add a new book
  remove   - Remove a book by title
  find     - Search books by title or author
  read     - Mark a book as read
  stats    - Show collection statistics
  help     - Show this help message
""")


def main(collection: BookCollection | None = None) -> None:
    if collection is None:
        collection = BookCollection()

    if len(sys.argv) < 2:
        show_help()
        return

    command = sys.argv[1].lower()

    if command == "list":
        handle_list(collection)
    elif command == "add":
        handle_add(collection)
    elif command == "remove":
        handle_remove(collection)
    elif command == "find":
        handle_find(collection)
    elif command == "read":
        handle_read(collection)
    elif command == "stats":
        handle_stats(collection)
    elif command == "help":
        show_help()
    else:
        print("Unknown command.\n")
        show_help()


if __name__ == "__main__":
    main()
