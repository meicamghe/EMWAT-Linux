import unittest

from emwat_linux.bridge import BridgeRequest, BridgeResponse
from emwat_linux.dispatcher import XMLMethodDispatcher


class XMLMethodDispatcherTests(unittest.TestCase):
    def setUp(self):
        self.request = BridgeRequest(
            path="/",
            query="invoke=123",
            content_type="text/plain;charset=UTF-8",
            origin="https://office.example",
            body=(
                b'<emwat version="1.0"><method class="EditWordDocument">'
                b'<param name="wordConfig">opaque</param></method></emwat>'
            ),
        )

    def test_unknown_method_is_not_dynamically_loaded(self):
        dispatcher = XMLMethodDispatcher()
        response = dispatcher(self.request)
        self.assertEqual(response.status, 501)
        self.assertEqual(response.body, b"method_not_implemented")

    def test_registered_method_receives_parsed_call_and_request(self):
        dispatcher = XMLMethodDispatcher()
        seen = []

        def handle(call, request):
            seen.append((call, request))
            return BridgeResponse(b"known-response", content_type="text/plain")

        dispatcher.register("EditWordDocument", handle)
        response = dispatcher(self.request)
        self.assertEqual(response.status, 200)
        self.assertEqual(response.body, b"known-response")
        self.assertEqual(seen[0][0].params["wordConfig"], "opaque")
        self.assertIs(seen[0][1], self.request)

    def test_malformed_xml_is_rejected(self):
        dispatcher = XMLMethodDispatcher()
        request = BridgeRequest("/", "", "", None, b"<broken")
        response = dispatcher(request)
        self.assertEqual(response.status, 400)
        self.assertEqual(response.body, b"invalid_emwat_request")

    def test_invalid_dispatch_request_objects_are_rejected(self):
        dispatcher = XMLMethodDispatcher()
        for request in (
            None,
            object(),
            BridgeRequest("/", "", "", None, "not-bytes"),
        ):
            with self.subTest(request=request):
                response = dispatcher(request)
                self.assertEqual(response.status, 400)
                self.assertEqual(response.body, b"invalid_emwat_request")

    def test_handler_failure_is_sanitized(self):
        dispatcher = XMLMethodDispatcher()
        dispatcher.register("EditWordDocument", lambda *_: (_ for _ in ()).throw(RuntimeError()))
        response = dispatcher(self.request)
        self.assertEqual(response.status, 500)
        self.assertEqual(response.body, b"internal_method_error")

    def test_duplicate_registration_is_rejected(self):
        dispatcher = XMLMethodDispatcher()
        handler = lambda *_: BridgeResponse(b"")
        dispatcher.register("EditWordDocument", handler)
        with self.assertRaises(ValueError):
            dispatcher.register("EditWordDocument", handler)

    def test_payload_limit_requires_positive_builtin_integer(self):
        for value in (True, False, 1.5, 16.0, "16", 0, -1, None):
            with self.subTest(value=value), self.assertRaisesRegex(
                ValueError, "max_payload_bytes must be a positive integer"
            ):
                XMLMethodDispatcher(max_payload_bytes=value)

    def test_registration_rejects_non_text_or_blank_class_names(self):
        for value in (None, 7, b"EditWordDocument", "", " EditWordDocument", "EditWordDocument "):
            with self.subTest(value=value), self.assertRaisesRegex(
                ValueError, "invalid method class name"
            ):
                XMLMethodDispatcher().register(value, lambda *_: BridgeResponse(b""))

    def test_registration_rejects_non_callable_handler(self):
        for handler in (None, 7, "callable"):
            with self.subTest(handler=handler), self.assertRaisesRegex(
                ValueError, "method handler must be callable"
            ):
                XMLMethodDispatcher().register("EditWordDocument", handler)


if __name__ == "__main__":
    unittest.main()
