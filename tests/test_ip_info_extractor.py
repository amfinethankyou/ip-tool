import unittest
from unittest.mock import patch

import ip_info_extractor as tool


class IpInfoExtractorTests(unittest.TestCase):
    def test_validate_ip(self):
        self.assertTrue(tool.validate_ip("8.8.8.8"))
        self.assertTrue(tool.validate_ip("2001:4860:4860::8888"))
        self.assertFalse(tool.validate_ip("999.999.999.999"))
        self.assertFalse(tool.validate_ip("not-an-ip"))

    def test_split_valid_invalid_deduplicates(self):
        valid, invalid = tool.split_valid_invalid(
            ["8.8.8.8", "bad", "8.8.8.8", "1.1.1.1", "bad"]
        )
        self.assertEqual(valid, ["8.8.8.8", "1.1.1.1"])
        self.assertEqual(invalid, ["bad"])

    def test_normalize_flags(self):
        data = {"mobile": True, "proxy": False, "hosting": True}
        normalized = tool.normalize_flags(data)
        self.assertEqual(normalized["mobile"], "Yes")
        self.assertEqual(normalized["proxy"], "No")
        self.assertEqual(normalized["hosting"], "Yes")

    @patch("ip_info_extractor.reverse_dns", return_value="dns.example")
    def test_add_reverse_dns(self, _mock_reverse):
        results = [{"query": "8.8.8.8"}, {"query": "1.1.1.1"}]
        tool.add_reverse_dns(results)
        self.assertEqual(results[0]["rdns"], "dns.example")
        self.assertEqual(results[1]["rdns"], "dns.example")


if __name__ == "__main__":
    unittest.main()
