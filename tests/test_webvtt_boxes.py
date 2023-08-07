#!/usr/bin/env python
import logging
import unittest

from construct import Container
from pymp4.parser import Box

log = logging.getLogger(__name__)


class BoxTests(unittest.TestCase):
    def test_iden_parse(self):
        self.assertEqual(
            Box.parse(b'\x00\x00\x00\x27iden2 - this is the second subtitle'),
            Container(
                offset=0,
                type="iden",
                data=Container(
                    cue_id="2 - this is the second subtitle"
                ),
                end=39
            )
        )

    def test_iden_build(self):
        self.assertEqual(
            Box.build(dict(
                type="iden",
                data=dict(
                    cue_id="1 - first subtitle"
                ))),
            b'\x00\x00\x00\x1aiden1 - first subtitle')

    def test_sttg_parse(self):
        self.assertEqual(
            Box.parse(b'\x00\x00\x003sttgline:10% position:50% size:48% align:center'),
            Container(
                offset=0,
                type="sttg",
                data=Container(
                    settings="line:10% position:50% size:48% align:center"
                ),
                end=51
            )
        )

    def test_sttg_build(self):
        self.assertEqual(
            Box.build(dict(
                type="sttg",
                data=dict(
                    settings="line:75% position:20% size:2em align:right"
                ))),
            b'\x00\x00\x002sttgline:75% position:20% size:2em align:right')

    def test_payl_parse(self):
        self.assertEqual(
            Box.parse(b'\x00\x00\x00\x13payl[chuckling]'),
            Container(
                offset=0,
                type="payl",
                data=Container(
                    cue_text="[chuckling]"
                ),
                end=19
            )
        )

    def test_payl_build(self):
        self.assertEqual(
            Box.build(dict(
                type="payl",
                data=dict(
                    cue_text="I have a bad feeling about- [boom]"
                ))),
            b'\x00\x00\x00*paylI have a bad feeling about- [boom]')

    def test_vttC_parse(self):
        self.assertEqual(
            Box.parse(b'\x00\x00\x00\x0evttCWEBVTT'),
            Container(
                offset=0,
                type="vttC",
                data=Container(
                    config="WEBVTT"
                ),
                end=14
            )
        )

    def test_vttC_build(self):
        self.assertEqual(
            Box.build(dict(
                type="vttC",
                data=dict(
                    config="WEBVTT with a text header\n\nSTYLE\n::cue {\ncolor: red;\n}"
                ))),
            b'\x00\x00\x00>vttCWEBVTT with a text header\n\nSTYLE\n::cue {\ncolor: red;\n}')

    def test_vlab_parse(self):
        self.assertEqual(
            Box.parse(b'\x00\x00\x00\x14vlabsource_label'),
            Container(
                offset=0,
                type="vlab",
                data=Container(
                    label="source_label"
                ),
                end=20
            )
        )

    def test_vlab_build(self):
        self.assertEqual(
            Box.build(dict(
                type="vlab",
                data=dict(
                    label="1234 \n test_label \n\n"
                ))),
            b'\x00\x00\x00\x1cvlab1234 \n test_label \n\n')
