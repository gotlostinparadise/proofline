import unittest
from html.parser import HTMLParser

from scripts.html_report import render_html_document


class _TagCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.start_tags = []

    def handle_starttag(self, tag, attrs):
        self.start_tags.append((tag, dict(attrs)))


class HtmlArtifactTests(unittest.TestCase):
    def test_render_html_document_escapes_content_and_marks_report_kind(self):
        output = render_html_document(
            title="Status <unsafe>",
            heading="CIPH Run Status",
            report_kind="status",
            summary_items=[("Objective", "Escape <script>alert(1)</script>")],
            sections=[
                {
                    "id": "summary",
                    "title": "Summary",
                    "items": ["Lint: PASS", "Manifest: PASS"],
                }
            ],
        )

        parser = _TagCollector()
        parser.feed(output)

        self.assertTrue(output.startswith("<!doctype html>"))
        self.assertIn("Status &lt;unsafe&gt;", output)
        self.assertIn("Escape &lt;script&gt;alert(1)&lt;/script&gt;", output)
        self.assertIn(("body", {"data-proofline-report": "status"}), parser.start_tags)
        self.assertIn(("section", {"id": "summary", "data-proofline-section": "summary"}), parser.start_tags)


if __name__ == "__main__":
    unittest.main()
