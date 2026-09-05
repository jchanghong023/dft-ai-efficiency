"""Create page-local section search evidence from already-rendered HTML."""
from html.parser import HTMLParser
import re


class Sections(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.items = []
        self.current = None
        self.heading = False
        self.heading_parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if re.fullmatch(r"h[1-6]", tag) and attrs.get("id"):
            self.current = {"id": attrs["id"], "title": "", "parts": []}
            self.items.append(self.current)
            self.heading, self.heading_parts = True, []

    def handle_endtag(self, tag):
        if self.heading and re.fullmatch(r"h[1-6]", tag):
            self.current["title"] = " ".join(self.heading_parts).strip()
            self.heading = False

    def handle_data(self, data):
        if self.current is not None:
            self.current["parts"].append(data)
        if self.heading:
            self.heading_parts.append(data)


def section_index(body):
    parser = Sections()
    parser.feed(body)
    return [{"id": item["id"], "title": item["title"],
             "text": re.sub(r"\s+", " ", " ".join(item["parts"])).strip()}
            for item in parser.items]
