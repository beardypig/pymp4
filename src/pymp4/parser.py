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
from construct import *
import construct.core
from construct.lib import *

log = logging.getLogger(__name__)


class PrefixedIncludingSize(Subconstruct):
    __slots__ = ["name", "lengthfield", "subcon"]

    def __init__(self, lengthfield, subcon):
        super(PrefixedIncludingSize, self).__init__(subcon)
        self.lengthfield = lengthfield

    def _parse(self, stream, context, path):
        try:
            lengthfield_size = self.lengthfield.sizeof()
            length = self.lengthfield._parse(stream, context, path)
        except SizeofError:
            offset_start = stream.tell()
            length = self.lengthfield._parse(stream, context, path)
            lengthfield_size = stream.tell() - offset_start

        stream2 = BoundBytesIO(stream, length - lengthfield_size)
        obj = self.subcon._parse(stream2, context, path)
        return obj

    def _build(self, obj, stream, context, path):
        try:
            # needs to be both fixed size, seekable and tellable (third not checked)
            self.lengthfield.sizeof()
            if not stream.seekable:
                raise SizeofError
            offset_start = stream.tell()
            self.lengthfield._build(0, stream, context, path)
            self.subcon._build(obj, stream, context, path)
            offset_end = stream.tell()
            stream.seek(offset_start)
            self.lengthfield._build(offset_end - offset_start, stream, context, path)
            stream.seek(offset_end)
        except SizeofError:
            data = self.subcon.build(obj, context)
            sl, p_sl = 0, 0
            dlen = len(data)
            # do..while
            i = 0
            while True:
                i += 1
                p_sl = sl
                sl = len(self.lengthfield.build(dlen + sl))
                if p_sl == sl: break

                self.lengthfield._build(dlen + sl, stream, context, path)
            else:
                self.lengthfield._build(len(data), stream, context, path)
            construct.core._write_stream(stream, len(data), data)

    def _sizeof(self, context, path):
        return self.lengthfield._sizeof(context, path) + self.subcon._sizeof(context, path)


# Header box

FileTypeBox = Struct(
    "type" / Const(b"ftyp"),
    "major_brand" / String(4),
    "minor_version" / Int32ub,
    "compatible_brands" / GreedyRange(String(4)),
)

SegmentTypeBox = Struct(
    "type" / Const(b"styp"),
    "major_brand" / String(4),
    "minor_version" / Int32ub,
    "compatible_brands" / GreedyRange(String(4)),
)

# Catch all boxes

RawBox = Struct(
    "type" / String(4, padchar=b" ", paddir="right"),
    "data" / GreedyBytes
)

FreeBox = Struct(
    "type" / Const(b"free"),
    "data" / GreedyBytes
)

SkipBox = Struct(
    "type" / Const(b"skip"),
    "data" / GreedyBytes
)

# Movie boxes, contained in a moov Box

MovieHeaderBox = Struct(
    "type" / Const(b"mvhd"),
    "version" / Int8ub,
    "flags" / Int24ub,
    Embedded(Switch(this.version, {
        1: Struct(
            "creation_time" / Int64ub,
            "modification_time" / Int64ub,
            "timescale" / Int32ub,
            "duration" / Int64ub,
        ),
        0: Struct(
            "creation_time" / Int32ub,
            "modification_time" / Int32ub,
            "timescale" / Int32ub,
            "duration" / Int32ub,
        ),
    })),
    "rate" / Int32sb,
    "volume" / Int16sb,
    # below could be just Padding(10) but why not
    Const(Int16ub, 0),
    Const(Int32ub, 0),
    Const(Int32ub, 0),
    "matrix" / Int32sb[9],
    "pre_defined" / Int32ub[6],
    "next_track_ID" / Int32ub,
)

# Track boxes, contained in trak box

TrackHeaderBox = Struct(
    "type" / Const(b"tkhd"),
    "version" / Int8ub,
    "flags" / Int24ub,
    Embedded(Switch(this.version, {
        1: Struct(
            "creation_time" / Int64ub,
            "modification_time" / Int64ub,
            "track_ID" / Int32ub,
            Padding(4),
            "duration" / Int64ub,
        ),
        0: Struct(
            "creation_time" / Int32ub,
            "modification_time" / Int32ub,
            "track_ID" / Int32ub,
            Padding(4),
            "duration" / Int32ub,
        ),
    })),
    Padding(8),
    "layer" / Int16sb,
    "alternate_group" / Int16sb,
    "volume" / Int16sb,
    Padding(2),
    "matrix" / Array(9, Int32sb),
    "width" / Int32ub,
    "height" / Int32ub
)


# Boxes contained by Media Box

class ISO6392TLanguageCode(Adapter):
    def _decode(self, obj, context):
        return ''.join(map(lambda c: chr(c + 0x60), obj))

    def _encode(self, obj, context):
        return map(lambda c: ord(c) - 0x60, obj)


MediaHeaderBox = Struct(
    "type" / Const(b"mdhd"),
    "version" / Int8ub,
    "flags" / Const(Int24ub, 0),
    "creation_time" / IfThenElse(this.version == 1, Int64ub, Int32ub),
    "modification_time" / IfThenElse(this.version == 1, Int64ub, Int32ub),
    "timescale" / IfThenElse(this.version == 1, Int64ub, Int32ub),
    "duration" / IfThenElse(this.version == 1, Int64ub, Int32ub),
    Embedded(BitStruct(
        Padding(1),
        "language" / ISO6392TLanguageCode(BitsInteger(5)[3]),
    )),
    Padding(2, pattern=b"\x00"),
)

HandlerReferenceBox = Struct(
    "type" / Const(b"hdlr"),
    "version" / Const(Int8ub, 0),
    "flags" / Const(Int24ub, 0),
    Padding(4, pattern=b"\x00"),
    "handler_type" / String(4),
    Padding(12, pattern=b"\x00"),  # Int32ub[3]
    "name" / CString(encoding="utf8")
)

# Boxes contained by Media Info Box

VideoMediaHeaderBox = Struct(
    "type" / Const(b"vmhd"),
    "version" / Default(Int8ub, 0),
    "flags" / Const(Int24ub, 1),
    "graphics_mode" / Default(Int16ub, 0),
    "opcolor" / Struct(
        "red" / Int16ub,
        "green" / Int16ub,
        "blue" / Int16ub,
    ),
)

DataEntryUrlBox = PrefixedIncludingSize(Int32ub, Struct(
    "type" / Const(b"url "),
    "version" / Const(Int8ub, 0),
    "flags" / BitStruct(
        Padding(23), "self_contained" / Rebuild(Flag, ~this._.location)
    ),
    "location" / If(~this.flags.self_contained, CString(encoding="utf8")),
))

DataEntryUrnBox = PrefixedIncludingSize(Int32ub, Struct(
    "type" / Const(b"urn "),
    "version" / Const(Int8ub, 0),
    "flags" / BitStruct(
        Padding(23), "self_contained" / Rebuild(Flag, ~(this._.name & this._.location))
    ),
    "name" / If(this.flags == 0, CString(encoding="utf8")),
    "location" / If(this.flags == 0, CString(encoding="utf8")),
))

DataReferenceBox = Struct(
    "type" / Const(b"dref"),
    "version" / Const(Int8ub, 0),
    "flags" / Int24ub,
    "data_entries" / PrefixedArray(Int32ub, Select(DataEntryUrnBox, DataEntryUrlBox)),
)

# Sample Table boxes (stbl)

SampleEntryBox = PrefixedIncludingSize(Int32ub, Struct(
    "format" / String(4, padchar=b" ", paddir="right"),
    Padding(6, pattern=b"\x00"),
    "data_reference_index" / Int16ub,
    "data" / GreedyBytes
))

BitRateBox = Struct(
    "type" / Const(b"btrt"),
    "bufferSizeDB" / Int32ub,
    "maxBitrate" / Int32ub,
    "avgBirate" / Int32ub,
)

SampleDescriptionBox = Struct(
    "type" / Const(b"stsd"),
    "version" / Int8ub,
    "flags" / Const(Int24ub, 0),
    "entries" / PrefixedArray(Int32ub, SampleEntryBox)
)

SampleSizeBox = Struct(
    "type" / Const(b"stsz"),
    "version" / Int8ub,
    "flags" / Const(Int24ub, 0),
    "sample_size" / Int32ub,
    "sample_count" / Int32ub,
    "entry_sizes" / If(this.sample_size == 0, Array(this.sample_count, Int32ub))
)

SampleSizeBox2 = Struct(
    "type" / Const(b"stz2"),
    "version" / Int8ub,
    "flags" / Const(Int24ub, 0),
    Padding(3, pattern=b"\x00"),
    "field_size" / Int8ub,
    "sample_count" / Int24ub,
    "entries" / Array(this.sample_count, Struct(
        "entry_size" / LazyBound(lambda ctx: globals()["Int%dub" % ctx.field_size])
    ))
)

SampleDegradationPriorityBox = Struct(
    "type" / Const(b"stdp"),
    "version" / Const(Int8ub, 0),
    "flags" / Const(Int24ub, 0),
)

TimeToSampleBox = Struct(
    "type" / Const(b"stts"),
    "version" / Const(Int8ub, 0),
    "flags" / Const(Int24ub, 0),
    "entries" / PrefixedArray(Int32ub, Struct(
        "sample_count" / Int32ub,
        "sample_delta" / Int32ub,
    ))
)

SyncSampleBox = Struct(
    "type" / Const(b"stss"),
    "version" / Const(Int8ub, 0),
    "flags" / Const(Int24ub, 0),
    "entries" / PrefixedArray(Int32ub, Struct(
        "sample_number" / Int32ub,
    ))
)

SampleToChunkBox = Struct(
    "type" / Const(b"stsc"),
    "version" / Const(Int8ub, 0),
    "flags" / Const(Int24ub, 0),
    "entries" / PrefixedArray(Int32ub, Struct(
        "first_chunk" / Int32ub,
        "samples_per_chunk" / Int32ub,
        "sample_description_index" / Int32ub,
    ))
)

ChunkOffsetBox = Struct(
    "type" / Const(b"stco"),
    "version" / Const(Int8ub, 0),
    "flags" / Const(Int24ub, 0),
    "entries" / PrefixedArray(Int32ub, Struct(
        "chunk_offset" / Int32ub,
    ))
)

ChunkLargeOffsetBox = Struct(
    "type" / Const(b"co64"),
    "version" / Const(Int8ub, 0),
    "flags" / Const(Int24ub, 0),
    "entries" / PrefixedArray(Int32ub, Struct(
        "chunk_offset" / Int64ub,
    ))
)

# Movie Fragment boxes, contained in moof box

MovieFragmentHeaderBox = Struct(
    "type" / Const(b"mfhd"),
    "version" / Const(Int8ub, 0),
    "flags" / Const(Int24ub, 0),
    "sequence_number" / Int32ub
)

TrackFragmentBaseMediaDecodeTimeBox = Struct(
    "type" / Const(b"tfdt"),
    "version" / Int8ub,
    "flags" / Const(Int24ub, 0),
    "baseMediaDecodeTime" / Switch(this.version, {1: Int64ub, 0: Int32ub})
)

TrackSampleFlags = BitStruct(
    Padding(4),
    #"is_leading" / BitsInteger(2),
    #"sample_depends_on" / BitsInteger(2),
    #"sample_is_depended_on" / BitsInteger(2),
    #"sample_has_redundancy" / BitsInteger(2),
    "is_leading" / Enum(BitsInteger(2), UNKNOWN=0, LEADINGDEP=1, NOTLEADING=2, LEADINGNODEP=3, default=0),
    "sample_depends_on" / Enum(BitsInteger(2), UNKNOWN=0, DEPENDS=1, NOTDEPENDS=2, RESERVED=3, default=0),
    "sample_is_depended_on" / Enum(BitsInteger(2), UNKNOWN=0, NOTDISPOSABLE=1, DISPOSABLE=2, RESERVED=3, default=0),
    "sample_has_redundancy" / Enum(BitsInteger(2), UNKNOWN=0, REDUNDANT=1, NOTREDUNDANT=2, RESERVED=3, default=0),
    "sample_padding_value" / BitsInteger(3),
    "sample_is_non_sync_sample" / Flag,
    "sample_degradation_priority" / BitsInteger(16),
)

TrackRunBox = Struct(
    "type" / Const(b"trun"),
    "version" / Int8ub,
    "flags" / BitStruct(
        Padding(12),
        "sample_composition_time_offsets_present" / Flag,
        "sample_flags_present" / Flag,
        "sample_size_present" / Flag,
        "sample_duration_present" / Flag,
        Padding(5),
        "first_sample_flags_present" / Flag,
        Padding(1),
        "data_offset_present" / Flag,
    ),
    "sample_count" / Int32ub,
    "data_offset" / If(this.flags.data_offset_present, Int32sb),
    "first_sample_flags" / If(this.flags.first_sample_flags_present, Int32ub),
    "sample_info" / Array(this.sample_count, Struct(
        "sample_duration" / If(this._.flags.sample_duration_present, Int32ub),
        "sample_size" / If(this._.flags.sample_size_present, Int32ub),
        "sample_flags" / If(this._.flags.sample_flags_present, TrackSampleFlags),
        "sample_composition_time_offsets" / If(
            this._.flags.sample_composition_time_offsets_present,
            IfThenElse(this._.version == 0, Int32ub, Int32sb)
        ),
    ))
)

TrackFragmentHeaderBox = Struct(
    "type" / Const(b"tfhd"),
    "version" / Int8ub,
    "flags" / BitStruct(
        Padding(6),
        "default_base_is_moof" / Flag,
        "duration_is_empty" / Flag,
        Padding(10),
        "default_sample_flags_present" / Flag,
        "default_sample_size_present" / Flag,
        "default_sample_duration_present" / Flag,
        Padding(1),
        "sample_description_index_present" / Flag,
        "base_data_offset_present" / Flag,
    ),
    "track_ID" / Int32ub,
    "base_data_offset" / If(this.flags.base_data_offset_present, Int64ub),
    "sample_description_index" / If(this.flags.sample_description_index_present, Int32ub),
    "default_sample_duration" / If(this.flags.default_sample_duration_present, Int32ub),
    "default_sample_size" / If(this.flags.default_sample_size_present, Int32ub),
    "default_sample_flags" / If(this.flags.default_sample_flags_present, TrackSampleFlags),
)

MovieExtendsHeaderBox = Struct(
    "type" / Const(b"mehd"),
    "version" / Default(Int8ub, 0),
    "flags" / Const(Int24ub, 0),
    "fragment_duration" / IfThenElse(this.version == 1,
                                     Default(Int64ub, 0),
                                     Default(Int32ub, 0))
)

TrackExtendsBox = Struct(
    "type" / Const(b"trex"),
    "version" / Const(Int8ub, 0),
    "flags" / Const(Int24ub, 0),
    "track_ID" / Int32ub,
    "default_sample_description_index" / Int32ub,
    "default_sample_duration" / Int32ub,
    "default_sample_size" / Int32ub,
    "default_sample_flags" / TrackSampleFlags,
)

SegmentIndexBox = Struct(
    "type" / Const(b"sidx"),
    "version" / Int8ub,
    "flags" / Const(Int24ub, 0),
    "reference_ID" / Int32ub,
    "timescale" / Int32ub,
    "earliest_presentation_time" / IfThenElse(this.version == 0, Int32ub, Int64ub),
    "first_offset" / IfThenElse(this.version == 0, Int32ub, Int64ub),
    Padding(2),
    "reference_count" / Int16ub,
    "references" / Array(this.reference_count, BitStruct(
        "reference_type" / Enum(BitsInteger(1), INDEX=1, MEDIA=0),
        "referenced_size" / BitsInteger(31),
        "segment_duration" / BitsInteger(32),
        "starts_with_SAP" / Flag,
        "SAP_type" / BitsInteger(3),
        "SAP_delta_time" / BitsInteger(28),
    ))
)

# Movie data box

MovieDataBox = Struct(
    "type" / Const(b"mdat"),
    "data" / GreedyBytes
)

# Media Info Box

SoundMediaHeaderBox = Struct(
    "type" / Const(b"smhd"),
    "version" / Const(Int8ub, 0),
    "flags" / Const(Int24ub, 0),
    "balance" / Default(Int16sb, 0),
    Padding(2, pattern=b"\x00")
)

ContainerBoxLazy = LazyBound(lambda ctx: ContainerBox)

Box = PrefixedIncludingSize(Int32ub, Struct(
    "type" / Peek(String(4, padchar=b" ", paddir="right")),
    Embedded(Switch(this.type, {
        b"ftyp": FileTypeBox,
        b"styp": SegmentTypeBox,
        b"mvhd": MovieHeaderBox,
        b"moov": ContainerBoxLazy,
        b"moof": ContainerBoxLazy,
        b"mfhd": MovieFragmentHeaderBox,
        b"tfdt": TrackFragmentBaseMediaDecodeTimeBox,
        b"trun": TrackRunBox,
        b"tfhd": TrackFragmentHeaderBox,
        b"traf": ContainerBoxLazy,
        b"mvex": ContainerBoxLazy,
        b"mehd": MovieExtendsHeaderBox,
        b"trex": TrackExtendsBox,
        b"trak": ContainerBoxLazy,
        b"mdia": ContainerBoxLazy,
        b"tkhd": TrackHeaderBox,
        b"mdat": MovieDataBox,
        b"free": FreeBox,
        b"skip": SkipBox,
        b"mdhd": MediaHeaderBox,
        b"hdlr": HandlerReferenceBox,
        b"minf": ContainerBoxLazy,
        b"vmhd": VideoMediaHeaderBox,
        b"dinf": ContainerBoxLazy,
        b"dref": DataReferenceBox,
        b"stbl": ContainerBoxLazy,
        b"stsd": SampleDescriptionBox,
        b"stsz": SampleSizeBox,
        b"stz2": SampleSizeBox2,
        b"stts": TimeToSampleBox,
        b"stss": SyncSampleBox,
        b"stsc": SampleToChunkBox,
        b"stco": ChunkOffsetBox,
        b"co64": ChunkLargeOffsetBox,
        b"smhd": SoundMediaHeaderBox,
        b"sidx": SegmentIndexBox
    }, default=RawBox)),
))

ContainerBox = Struct(
    "type" / String(4, padchar=b" ", paddir="right"),
    "children" / GreedyRange(Box),
)

MP4 = GreedyRange(Box)
