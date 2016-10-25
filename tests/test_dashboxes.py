#!/usr/bin/env python
import logging
import unittest

from construct import Container
from pymp4.parser import Box

log = logging.getLogger(__name__)


class BoxTests(unittest.TestCase):
    def test_tenc_parse(self):
        self.assertEqual(
            Box.parse(b'\x00\x00\x00\x18tenc\xba\x11\xd1\x1eg\xa1C\x0c\x88\xcd\xae\x8a4U\xcaK'),
            Container(type=b"tenc")(key_id="ba11d11e67a1430c88cdae8a3455ca4b")
        )

    def test_tenc_build(self):
        self.assertEqual(
            Box.build(dict(
                type=b"tenc",
                key_id="ba11d11e67a1430c88cdae8a3455ca4b")),
            b'\x00\x00\x00\x18tenc\xba\x11\xd1\x1eg\xa1C\x0c\x88\xcd\xae\x8a4U\xcaK')
