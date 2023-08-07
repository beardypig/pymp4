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
from uuid import UUID

from construct import Container
from pymp4.parser import Box

log = logging.getLogger(__name__)


class BoxTests(unittest.TestCase):
    def test_tenc_parse(self):
        self.assertEqual(
            Box.parse(b'\x00\x00\x00 tenc\x00\x00\x00\x00\x00\x00\x01\x083{\x96C!\xb6CU\x9eY>\xcc\xb4l~\xf7'),
            Container(
                offset=0,
                type="tenc",
                data=Container(
                    version=0,
                    flags=0,
                    _reserved=0,
                    default_byte_blocks=0,
                    is_encrypted=1,
                    iv_size=8,
                    key_ID=UUID('337b9643-21b6-4355-9e59-3eccb46c7ef7'),
                    constant_iv=None
                ),
                end=32
            )
        )

    def test_tenc_build(self):
        self.assertEqual(
            Box.build(dict(
                type="tenc",
                data=dict(
                    key_ID=UUID('337b9643-21b6-4355-9e59-3eccb46c7ef7'),
                    iv_size=8,
                    is_encrypted=1
                )
            )),
            b'\x00\x00\x00 tenc\x00\x00\x00\x00\x00\x00\x01\x083{\x96C!\xb6CU\x9eY>\xcc\xb4l~\xf7')
