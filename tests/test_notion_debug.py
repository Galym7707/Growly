from scripts.debug_notion_root import object_title


def test_extracts_page_title() -> None:
    item = {
        "object": "page",
        "properties": {
            "Name": {
                "type": "title",
                "title": [{"plain_text": "Growly Root"}],
            }
        },
    }
    assert object_title(item) == "Growly Root"


def test_extracts_database_title() -> None:
    item = {
        "object": "database",
        "title": [{"plain_text": "Content Calendar"}],
    }
    assert object_title(item) == "Content Calendar"
