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
from pymp4.exceptions import BoxNotFound
from pymp4.parser import Box
from pymp4.util import BoxUtil

log = logging.getLogger(__name__)


class BoxTests(unittest.TestCase):
    box_data = Container(type=b"demo")(children=[
            Container(type=b"a   ")(id=1),
            Container(type=b"b   ")(id=2),
            Container(type=b"c   ")(children=[
                Container(type=b"a   ")(id=3),
                Container(type=b"b   ")(id=4),
            ]),
        ])

    def test_find(self):
        self.assertListEqual(
            list(BoxUtil.find(self.box_data, "b   ")),
            [Container(type=b"b   ")(id=2), Container(type=b"b   ")(id=4)]
        )

    def test_find_empty(self):
        self.assertListEqual(
            list(BoxUtil.find(self.box_data, "f   ")),
            []
        )

    def test_first(self):
        self.assertEqual(
            BoxUtil.first(self.box_data, "b   "),
            Container(type=b"b   ")(id=2)
        )

    def test_first_missing(self):
        self.assertRaises(
            BoxNotFound,
            BoxUtil.first, self.box_data, "f   ",
        )
