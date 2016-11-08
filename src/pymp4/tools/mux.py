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
import io
from collections import defaultdict
from operator import itemgetter
from construct import Container
from pymp4.exceptions import BoxNotFound

from pymp4.parser import Box
from pymp4.util import BoxUtil

log = logging.getLogger(__name__)


class MP4Muxer(object):
    def __init__(self, output):
        self.moov = None
        self.ftyp = False
        self.streams = set()

        # map of track -> moof/mdat list
        self.moovs = {}
        self.movie_data = defaultdict(lambda: defaultdict(list))

        # map stream0:track0 to out:track0
        #     stream1:track0 to out:track1
        self.track_map = {1: {1: 1},
                          2: {1: 2}}

        self.output = output
        self.shadow_output = io.BytesIO()

    def flush(self):
        self.output.write(self.shadow_output.getvalue())
        if hasattr(self.output, "flush"):
            self.output.flush()
        self.shadow_output = io.BytesIO()

    @property
    def output_tracks(self):
        otids = []
        for sid in self.track_map:
            for tid in self.track_map[sid]:
                otids.append(self.track_map[sid][tid])

        return sorted(otids)

    def output_track_map(self, ostream):
        """
        Get the input mapping for a particular output stream
        :param ostream:
        :return:
        """
        for sid in self.track_map:
            for tid in self.track_map[sid]:
                if self.track_map[sid][tid] == ostream:
                    return sid, tid

    def add_header(self, stream, sid=0):
        """
        A header should consist of at least a ftyp and a moov box
        :param stream: buffer that contains a stream of MP4 data
        :param sid: ID for the stream
        """
        log.debug("Reading header...")
        while True:
            box = Box.parse_stream(stream)

            if box.type == b"ftyp" and not self.ftyp:
                log.info("Writing out copy of ftyp box")
                self.ftyp = True
                Box.build_stream(box, self.shadow_output)

            elif box.type == b"moov":
                self.moovs[sid] = box
                # stop after moov box
                return
            else:
                log.debug("Discarding box: {}".format(box.type))
                #Box.build_stream(box, self.output)

    def finalise_header(self):
        """
        Write the header data to a buffer
        """
        # Should only need to write out the ftyp and the moov boxes
        final_trak = []
        final_trex = []

        for otid in self.output_tracks:
            # get the input stream id and track id for a given output track
            sid, tid = self.output_track_map(otid)
            log.info("To build output track:{} requires stream{}:track{}".format(otid, sid, tid))
            moov = self.moovs[sid]

            # find the trak boxes with the desired track id
            traks = []
            for trak in BoxUtil.find(moov, b"trak"):
                if BoxUtil.first(trak, b"tkhd").track_ID == tid:
                    traks.append(trak)

            if len(traks) == 1:
                for trak in traks:
                    BoxUtil.first(trak, b"tkhd").track_ID = otid
                    final_trak.append(trak)
            else:
                raise Exception("Found {} trak boxes in the moov box for stream: {}".format(len(traks), sid))

            # from this stream, extract the tracks that are wanted
            mvhd = BoxUtil.first(moov, b"mvhd")
            iods = BoxUtil.first(moov, b"iods")
            # look in the moov box and filter out the trak boxes that match the desired track id
            try:
                mvex = BoxUtil.first(moov, b"mvex")
                # remap trex.track_ID from input tid to output tid
                trexes = filter(lambda t: t.track_ID == tid, BoxUtil.find(mvex, b"trex"))
                if len(trexes) == 1:
                    for trex in trexes:
                        trex.track_ID = otid
                        final_trex.append(trex)
                else:
                    raise Exception("Found {} trex boxes in the mvex box for stream: {}".format(len(trexes), sid))
            except BoxNotFound:
                # create an appropriate trex box
                final_trex.append(
                    dict(type=b"trex", track_ID=otid)
                )

        mvhd.next_track_ID = len(self.output_tracks) + 1

        # write out the header with the tracks for each stream combined
        Box.build_stream(dict(
            type=b"moov",
            children=[
                mvhd,
                iods,
                dict(type=b"mvex",
                     children=[
                         dict(type=b"mehd", version=0, flags=0, fragment_duration=0)
                     ] + final_trex),
            ] + final_trak
        ), self.shadow_output)

        self.flush()

    def add_content(self, stream, sid=0):
        """
        Content should consist of pairs of moof and mdat boxes
        :param stream: stream to read the boxes from
        :param sid: the input stream that this content is associated with
        """
        while True:
            try:
                box = Box.parse_stream(stream)
            except:
                # TODO: use a specific exception
                return
            if box.type == b"sidx":
                sidx = box
                self.sidx = sidx
                moof_offset = 0
                for ref in sidx.references:
                    log.debug("moof_offset = 0x{:x}".format(moof_offset))

                    # parse the moof, mdat pair
                    moof = Box.parse_stream(stream)
                    mdat = Box.parse_stream(stream)

                    if moof.type != b"moof":
                        raise Exception("Expected moof box, found {0}".format(moof.type))
                    if mdat.type != b"mdat":
                        raise Exception("Expected mdat box, found {0}".format(mdat.type))

                    seq = moof.children[0].sequence_number
                    self.movie_data[seq][sid].append((moof, mdat))

                    moof_offset += ref.referenced_size
                # seek to the next segment
                stream.seek(sidx.end + moof_offset)
                return


    def finalise_content(self):
        """
        Write this boxes in this order
            moof, mdat
        """
        movie_data = sorted(self.movie_data.items(), key=itemgetter(0))
        self.movie_data.clear()

        for seq, stream_dat in movie_data:
            for otid in self.output_tracks:
                # get the input stream id and track id for a given output track
                sid, tid = self.output_track_map(otid)

                if len(stream_dat[sid]) == 0:
                    log.warning("No data found for sequence_number={} in stream{}".format(seq, sid))

                # take a moof/mdat pair from the current stream
                while len(stream_dat[sid]):
                    moof, mdat = stream_dat[sid].pop(0)

                    # Update the track ID in moof->traf->tfhd
                    traf_i = BoxUtil.index(moof, b"traf")
                    # skip tracks we don't want
                    if moof.children[traf_i].children[0].track_ID == tid:
                        moof.children[traf_i].children[0].track_ID = otid

                        log.debug("writing sequence_number: {} (stream{}:track{})".format(seq, sid, tid))
                        # combine the multiple mdat boxes
                        self.shadow_output.write(Box.build(moof))
                        self.shadow_output.write(Box.build(mdat))

        self.flush()
