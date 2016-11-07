#!/usr/bin/env python
"""
   Copyright 2016 beardypig

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
import logging
import unittest

from construct import Container
from pymp4.parser import Box

log = logging.getLogger(__name__)


class BoxTests(unittest.TestCase):
    def test_ftyp_parse(self):
        self.assertEqual(
            Box.parse(b'\x00\x00\x00\x18ftypiso5\x00\x00\x00\x01iso5avc1'),
            Container(offset=0)
            (type=b"ftyp")
            (major_brand=b"iso5")
            (minor_version=1)
            (compatible_brands=[b"iso5", b"avc1"])
            (end=24)
        )

    def test_ftyp_build(self):
        self.assertEqual(
            Box.build(dict(
                type=b"ftyp",
                major_brand=b"iso5",
                minor_version=1,
                compatible_brands=[b"iso5", b"avc1"])),
            b'\x00\x00\x00\x18ftypiso5\x00\x00\x00\x01iso5avc1')
