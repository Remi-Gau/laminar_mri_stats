from dashboard import parse_authors


def test_parse_authors():
    authors = "Pfaffenrot, Viktor, 0000-0002-3404-5018; Koopmans, Peter J."
    assert parse_authors(authors) == ["Pfaffenrot, Viktor", "Koopmans, Peter J."]
