#!/usr/bin/env python
"""
   Copyright 2021 CodeShop B.V.

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
import io
from uuid import UUID

from construct import Container
from pymp4.parser import Box
from pymp4.parser import find_samples_fragmented

log = logging.getLogger(__name__)


class SegmentTests(unittest.TestCase):
    
    def test_parse_video_samples(self): 
       infile = open( '3.cmfv','rb')
       moov_box = []
       moof_box  = []
       for i in range(5):
          t = Box.parse_stream(infile)
          if(t["type"] == b"moov"):
              moov_box = t 
          if(t["type"] == b"moof"):
              moof_box = t 
       res = find_samples_fragmented(moov_box, moof_box, 1)
       self.assertEqual(res[0]["decode_time"], 12288) 
       self.assertEqual(res[1]["decode_time"], 12800)
       self.assertEqual(res[2]["decode_time"], 13312)
       self.assertEqual(res[0]["offset_mdat"], 8) 
       self.assertEqual(res[1]["offset_mdat"], 2223)
       self.assertEqual(res[2]["offset_mdat"], 2400)
#     def test_tenc_parse(self):
#         self.assertEqual(
#             Box.parse(b'\x00\x00\x00 tenc\x00\x00\x00\x00\x00\x00\x01\x083{\x96C!\xb6CU\x9eY>\xcc\xb4l~\xf7'),
#             Container(offset=0)
#             (type=b"tenc")
#             (version=0)
#             (flags=0)
#             (is_encrypted=1)
#             (iv_size=8)
#             (key_ID=UUID('337b9643-21b6-4355-9e59-3eccb46c7ef7'))
#             (end=32)
#         )

#     def test_tenc_build(self):
#         self.assertEqual(
#             Box.build(dict(
#                 type=b"tenc",
#                 key_ID=UUID('337b9643-21b6-4355-9e59-3eccb46c7ef7'),
#                 iv_size=8,
#                 is_encrypted=1)),
#            b'\x00\x00\x00 tenc\x00\x00\x00\x00\x00\x00\x01\x083{\x96C!\xb6CU\x9eY>\xcc\xb4l~\xf7')
