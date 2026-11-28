import unittest

from emwat_linux.http_capture import extract_http_body


class HttpBodyExtractionTests(unittest.TestCase):
    def test_extracts_exact_content_length_body(self):
        body = b"<response-word>YWJj</response-word>"
        stream = b"HTTP/1.1 200 OK\r\nContent-Length: " + str(len(body)).encode() + b"\r\nContent-Type: application/xml\r\n\r\n" + body
        result = extract_http_body(stream)
        self.assertTrue(result.body_complete)
        self.assertEqual(result.body, body)
        self.assertEqual(result.content_length, len(body))

    def test_gap_inside_body_makes_extraction_partial(self):
        body = b"abcdef"
        header = b"HTTP/1.1 200 OK\r\nContent-Length: 6\r\n\r\n"
        result = extract_http_body(header + body, [(len(header) + 2, len(header) + 4)])
        self.assertFalse(result.body_complete)
        self.assertEqual(result.body, body)
        self.assertEqual(result.body_gap_ranges, ((2, 4),))

    def test_missing_content_length_bytes_are_not_marked_complete(self):
        stream = b"HTTP/1.1 200 OK\r\nContent-Length: 8\r\n\r\nabc"
        result = extract_http_body(stream)
        self.assertFalse(result.body_complete)
        self.assertEqual(result.body, b"abc")
        self.assertIn("Content-Length body truncated", result.errors)

    def test_chunked_body_is_preserved_with_transfer_framing(self):
        body = b"3\r\nabc\r\n2\r\nde\r\n0\r\n\r\n"
        stream = b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n" + body
        result = extract_http_body(stream)
        self.assertTrue(result.body_complete)
        self.assertEqual(result.body, body)
        self.assertEqual(result.transfer_encoding, "chunked")

    def test_header_gap_prevents_exact_body_claim(self):
        stream = b"HTTP/1.1 200 OK\r\nContent-Length: 3\r\n\r\nabc"
        result = extract_http_body(stream, [(4, 5)])
        self.assertFalse(result.header_complete)
        self.assertFalse(result.body_complete)

    def test_conflicting_content_lengths_are_rejected(self):
        stream = b"HTTP/1.1 200 OK\r\nContent-Length: 3\r\nContent-Length: 4\r\n\r\nabc"
        result = extract_http_body(stream)
        self.assertFalse(result.body_complete)
        self.assertIn("conflicting Content-Length headers", result.errors)


if __name__ == "__main__":
    unittest.main()
