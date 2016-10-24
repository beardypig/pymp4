#!/usr/bin/env python
import logging
import unittest

from construct import Container
from pymp4.parser import Box

log = logging.getLogger(__name__)


class BoxTests(unittest.TestCase):
    def test_ftyp_parse(self):
        self.assertEqual(
            Box.parse(b'\x00\x00\x00\x18ftypiso5\x00\x00\x00\x01iso5avc1'),
            Container(type=b"ftyp")(major_brand=b"iso5")(minor_version=1)(compatible_brands=[b"iso5", b"avc1"])
        )

    def test_ftyp_build(self):
        self.assertEqual(
            Box.build(dict(
                type=b"ftyp",
                major_brand=b"iso5",
                minor_version=1,
                compatible_brands=[b"iso5", b"avc1"])),
            b'\x00\x00\x00\x18ftypiso5\x00\x00\x00\x01iso5avc1')
