import unittest
from clipboard_history import History


class HistoryTests(unittest.TestCase):
    def test_memory_only_dedup_limit_and_unicode(self):
        h = History()
        for n in range(60):
            h.add(str(n))
        self.assertEqual(len(h.items), 50)
        h.add("中文\ntext")
        h.add("中文\ntext")
        self.assertEqual(h.items.count("中文\ntext"), 1)
        self.assertEqual(h.items[0], "中文\ntext")
        self.assertEqual(History().items, [])


if __name__ == "__main__":
    unittest.main()
