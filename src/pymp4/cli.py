#!/usr/bin/env python
from __future__ import print_function
import io
import logging
import argparse

from parser import Box
from construct import setglobalfullprinting
from summary import Summary

log = logging.getLogger(__name__)
setglobalfullprinting(True)


def dump(input_file):
    with open(input_file, 'rb') as fd:
        fd.seek(0, io.SEEK_END)
        eof = fd.tell()
        fd.seek(0)

        boxes = []
        while fd.tell() < eof:
            box = Box.parse_stream(fd)
            boxes.append(box)
            #print(box)

    summary = Summary (input_file, boxes)
    print(summary.data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dump all the boxes from an MP4 file")
    parser.add_argument(
        "input_file",
        type=str,
        metavar="FILE",
        help="Path to the MP4 file to open",
    )

    args = parser.parse_args()
    dump(args.input_file)