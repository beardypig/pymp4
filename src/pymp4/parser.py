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
from uuid import UUID

from construct import *
import construct.core
from construct.lib import *

# Enum is a construct class. Will clash with python's Enum
from enum import Enum as PythonEnum

log = logging.getLogger(__name__)

UNITY_MATRIX = [0x10000, 0, 0, 0, 0x10000, 0, 0, 0, 0x40000000]

class BoxType(PythonEnum):
    """
    This Enum class contains all the possible types supported by this parser
    for the "Box" structure, which represents the foundation of how an MP4
    is represented.
    """
    FTYP = b"ftyp"
    STYP = b"styp"
    MVHD = b"mvhd"
    MOOV = b"moov"
    MOOF = b"moof"
    MFHD = b"mfhd"
    TFDT = b"tfdt"
    TRUN = b"trun"
    TFHD = b"tfhd"
    TRAF = b"traf"
    MVEX = b"mvex"
    MEHD = b"mehd"
    TREX = b"trex"
    TRAK = b"trak"
    MDIA = b"mdia"
    TKHD = b"tkhd"
    ELST = b"elst"
    EDTS = b"edts"
    MDAT = b"mdat"
    FREE = b"free"
    SKIP = b"skip"
    MDHD = b"mdhd"
    HDLR = b"hdlr"
    MINF = b"minf"
    VMHD = b"vmhd"
    DINF = b"dinf"
    DREF = b"dref"
    STBL = b"stbl"
    STSD = b"stsd"
    STSZ = b"stsz"
    STZ2 = b"stz2"
    STTS = b"stts"
    STSS = b"stss"
    STSC = b"stsc"
    STCO = b"stco"
    CO64 = b"co64"
    CTTS = b"ctts"
    SMHD = b"smhd"
    SIDX = b"sidx"
    SAIZ = b"saiz"
    SAIO = b"saio"
    BTRT = b"btrt"
    META = b"meta"
    IPRO = b"ipro"
    PITM = b"pitm"
    PRFT = b"prft"
    # dash # dash
    TENC = b"tenc"
    PSSH = b"pssh"
    SENC = b"senc"
    SINF = b"sinf"
    FRMA = b"frma"
    SCHM = b"schm"
    SCHI = b"schi"
    # piff # piff
    UUID = b"uuid"
    # HDS b # HDS b
    ABST = b'abst'
    ASRT = b'asrt'
    AFRT = b'afrt'
    ELNG = b'elng'
    # Event Message Track
    EMSG = b"emsg"
    EMBE = b"embe"
    EMEB = b"emeb"
    EMIB = b"emib"
    EVTE = b"evte"
    URIM = b"urim"
    URI_ = b"uri "
    URI = b"uri"
    URII = b"uriI"

    ## timed text subtitle
    VTTC = b"vttC"
    VLAB = b"vlab"
    STHD = b'sthd'
    NMHD = b'nmhd'

    ##VTT internal
    VTTc = b'vttc' 
    VSID = b'vsid'
    CTIM = b'ctim'
    IDEN = b'iden'
    STTG = b'sttg'
    PAY1 = b'pay1'
    VTTE = b'vtte'
    VTTA = b'vtta' 
    
ContainerBoxLazy = LazyBound(lambda ctx: ContainerBox)    

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


# MetaDataSampleEntry

URIBox = Struct(
    "type" / Const(b'uri '),
    "version" / Default(Int8ub, 0),
    "flags" / Default(Int24ub, 0),
    "theURI" / CString()
)


URIInitBox = Struct(
    "type" / Const(b"uriI"),
    "version" / Default(Int8ub, 0),
    "flags" / Default(Int24ub, 0),
    "uri_initialization_data" / GreedyBytes
)

EditBox = Struct(
    "type" / Const(b"edts"),
    "children" / LazyBound(lambda _: GreedyRange(Box))
)

EventMessageSampleEntry = Struct(
    "children" / LazyBound(lambda _: GreedyRange(Box))
)

URIMetaSampleEntry = Struct(
    "children" / LazyBound(lambda _: GreedyRange(Box))
)

XMLSubtitleSampleEntry = Struct(
    "namespace" / CString(encoding="utf8")
    ##"theURI" / CString(encoding="utf8")
)

WebVTTConfigurationBox = Struct(
    "type" / Const(b'vttC'),
    "config" / Default(GreedyBytes, b"")
)

WebVTTSourceLabelBox = Struct(
    "type" / Const(b'vlab') ,
    "source_label" / Default(GreedyBytes, b"")
)

WVTTSampleEntry = Struct(
    "children" / LazyBound(lambda _: GreedyRange(Box))
)

URIMetaSampleEntry = Struct(
    "children" / LazyBound(lambda _: GreedyRange(Box))
)

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

# Catch find boxes

RawBox = Struct(
    "type" / String(4, padchar=b" ", paddir="right"),
    "data" / Default(GreedyBytes, b"")
)

FreeBox = Struct(
    "type" / Const(b"free"),
    "data" / GreedyBytes
)

SkipBox = Struct(
    "type" / Const(b"skip"),
    "data" / GreedyBytes
)

NullMediaHeaderBox = Struct(
    "type" / Const(b"nmhd"),
    "version" / Default(Int8ub, 0),
    "flags" / Default(Int24ub, 0)
)

SubtitleMediaHeaderBox = Struct(
    "type" / Const(b"sthd"),
    "version" / Default(Int8ub, 0),
    "flags" / Default(Int24ub, 0)
)

# Movie boxes, contained in a moov Box

MovieHeaderBox = Struct(
    "type" / Const(b"mvhd"),
    "version" / Default(Int8ub, 0),
    "flags" / Default(Int24ub, 0),
    Embedded(Switch(this.version, {
        1: Struct(
            "creation_time" / Default(Int64ub, 0),
            "modification_time" / Default(Int64ub, 0),
            "timescale" / Default(Int32ub, 10000000),
            "duration" / Int64ub
        ),
        0: Struct(
            "creation_time" / Default(Int32ub, 0),
            "modification_time" / Default(Int32ub, 0),
            "timescale" / Default(Int32ub, 10000000),
            "duration" / Int32ub,
        ),
    })),
    "rate" / Default(Int32sb, 65536),
    "volume" / Default(Int16sb, 256),
    # below could be just Padding(10) but why not
    Const(Int16ub, 0),
    Const(Int32ub, 0),
    Const(Int32ub, 0),
    "matrix" / Default(Int32sb[9], UNITY_MATRIX),
    "pre_defined" / Default(Int32ub[6], [0] * 6),
    "next_track_ID" / Default(Int32ub, 0xffffffff)
)

# Track boxes, contained in trak box

TrackHeaderBox = Struct(
    "type" / Const(b"tkhd"),
    "version" / Default(Int8ub, 0),
    "flags" / Default(Int24ub, 1),
    Embedded(Switch(this.version, {
        1: Struct(
            "creation_time" / Default(Int64ub, 0),
            "modification_time" / Default(Int64ub, 0),
            "track_ID" / Default(Int32ub, 1),
            Padding(4),
            "duration" / Default(Int64ub, 0),
        ),
        0: Struct(
            "creation_time" / Default(Int32ub, 0),
            "modification_time" / Default(Int32ub, 0),
            "track_ID" / Default(Int32ub, 1),
            Padding(4),
            "duration" / Default(Int32ub, 0),
        ),
    })),
    Padding(8),
    "layer" / Default(Int16sb, 0),
    "alternate_group" / Default(Int16sb, 0),
    "volume" / Default(Int16sb, 0),
    Padding(2),
    "matrix" / Default(Array(9, Int32sb), UNITY_MATRIX),
    "width" / Default(Int32ub, 0),
    "height" / Default(Int32ub, 0),
)

HDSSegmentBox = Struct(
    "type" / Const(b"abst"),
    "version" / Default(Int8ub, 0),
    "flags" / Default(Int24ub, 0),
    "info_version" / Int32ub,
    EmbeddedBitStruct(
        Padding(1),
        "profile" / Flag,
        "live" / Flag,
        "update" / Flag,
        Padding(4)
    ),
    "time_scale" / Int32ub,
    "current_media_time" / Int64ub,
    "smpte_time_code_offset" / Int64ub,
    "movie_identifier" / CString(),
    "server_entry_table" / PrefixedArray(Int8ub, CString()),
    "quality_entry_table" / PrefixedArray(Int8ub, CString()),
    "drm_data" / CString(),
    "metadata" / CString(),
    "segment_run_table" / PrefixedArray(Int8ub, LazyBound(lambda x: Box)),
    "fragment_run_table" / PrefixedArray(Int8ub, LazyBound(lambda x: Box))
)

HDSSegmentRunBox = Struct(
    "type" / Const(b"asrt"),
    "version" / Default(Int8ub, 0),
    "flags" / Default(Int24ub, 0),
    "quality_entry_table" / PrefixedArray(Int8ub, CString()),
    "segment_run_enteries" / PrefixedArray(Int32ub, Struct(
        "first_segment" / Int32ub,
        "fragments_per_segment" / Int32ub
    ))
)

HDSFragmentRunBox = Struct(
    "type" / Const(b"afrt"),
    "version" / Default(Int8ub, 0),
    "flags" / BitStruct(
        Padding(23),
        "update" / Flag
    ),
    "time_scale" / Int32ub,
    "quality_entry_table" / PrefixedArray(Int8ub, CString()),
    "fragment_run_enteries" / PrefixedArray(Int32ub, Struct(
        "first_fragment" / Int32ub,
        "first_fragment_timestamp" / Int64ub,
        "fragment_duration" / Int32ub,
        "discontinuity" / If(this.fragment_duration == 0, Int8ub)
    ))
)

EditListBox = Struct(
    "type" / Const(b"elst"),
    "version" / Default(Int8ub, 0),
    "flags" / Const(Int24ub, 0),
    Embedded(Switch(this.version, {
        0: Struct( "entries" / PrefixedArray(Int32ub, Struct(
        "edit_duration" / Int32ub,
        "media_time" / Int32sb,
        "media_rate_integer" /  Int16sb,
        "media_rate_fraction" / Int16sb,
        ))),
        1: Struct( "entries" / PrefixedArray(Int32ub, Struct(
        "edit_duration" / Int64ub,
        "media_time" / Int64ub,
        "media_rate_integer" /  Int16sb,
        "media_rate_fraction" / Int16sb,
        ))
        ),
    })),
 
)

CompositionOffsetBox = Struct(
    "type" / Const(b"ctts"),
    "version" / Default(Int8ub, 0),
    "flags" / Const(Int24ub, 0),
    Embedded(Switch(this.version, {
        0: Struct( "entries" / PrefixedArray(Int32ub, Struct(
        "sample_count" / Int32ub,
        "sampe_offest" / Int32ub,
        ))),
        1: Struct( "entries" / PrefixedArray(Int32ub, Struct(
        "sample_count" / Int32ub,
        "sample_offset" / Int32sb,
        ))
        ),
    })),
    "media_rate_integer" / Int16sb,
    "media_rate_fraction" / Int16sb,
)

    

# Boxes contained by Media Box

class ISO6392TLanguageCode(Adapter):
    def _decode(self, obj, context):
        """
        Get the python representation of the obj
        """
        return b''.join(map(int2byte, [c + 0x60 for c in bytearray(obj)])).decode("utf8")

    def _encode(self, obj, context):
        """
        Get the bytes representation of the obj
        """
        return [c - 0x60 for c in bytearray(obj.encode("utf8"))]


MediaHeaderBox = Struct(
    "type" / Const(b"mdhd"),
    "version" / Default(Int8ub, 0),
    "flags" / Const(Int24ub, 0),
    "creation_time" / IfThenElse(this.version == 1, Int64ub, Int32ub),
    "modification_time" / IfThenElse(this.version == 1, Int64ub, Int32ub),
    "timescale" / Int32ub,
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
        "red" / Default(Int16ub, 0),
        "green" / Default(Int16ub, 0),
        "blue" / Default(Int16ub, 0),
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
    "flags" / Default(Int24ub, 0),
    "data_entries" / PrefixedArray(Int32ub, Select(DataEntryUrnBox, DataEntryUrlBox)),
)

# Sample Table boxes (stbl)

MP4ASampleEntryBox = Struct(
    "version" / Default(Int16ub, 0),
    "revision" / Const(Int16ub, 0),
    "vendor" / Const(Int32ub, 0),
    "channels" / Default(Int16ub, 2),
    "bits_per_sample" / Default(Int16ub, 16),
    "compression_id" / Default(Int16sb, 0),
    "packet_size" / Const(Int16ub, 0),
    "sampling_rate" / Int16ub,
    Padding(2)
)


class MaskedInteger(Adapter):
    def _decode(self, obj, context):
        return obj & 0x1F

    def _encode(self, obj, context):
        return obj & 0x1F


AAVC = Struct(
    "version" / Const(Int8ub, 1),
    "profile" / Int8ub,
    "compatibility" / Int8ub,
    "level" / Int8ub,
    EmbeddedBitStruct(
        Padding(6, pattern=b'\x01'),
        "nal_unit_length_field" / Default(BitsInteger(2), 3),
    ),
    "sps" / Default(PrefixedArray(MaskedInteger(Int8ub), PascalString(Int16ub)), []),
    "pps" / Default(PrefixedArray(Int8ub, PascalString(Int16ub)), [])
)

HVCC = Struct(
    EmbeddedBitStruct(
        "version" / Const(BitsInteger(8), 1),
        "profile_space" / BitsInteger(2),
        "general_tier_flag" / BitsInteger(1),
        "general_profile" / BitsInteger(5),
        "general_profile_compatibility_flags" / BitsInteger(32),
        "general_constraint_indicator_flags" / BitsInteger(48),
        "general_level" / BitsInteger(8),
        Padding(4, pattern=b'\xff'),
        "min_spatial_segmentation" / BitsInteger(12),
        Padding(6, pattern=b'\xff'),
        "parallelism_type" / BitsInteger(2),
        Padding(6, pattern=b'\xff'),
        "chroma_format" / BitsInteger(2),
        Padding(5, pattern=b'\xff'),
        "luma_bit_depth" / BitsInteger(3),
        Padding(5, pattern=b'\xff'),
        "chroma_bit_depth" / BitsInteger(3),
        "average_frame_rate" / BitsInteger(16),
        "constant_frame_rate" / BitsInteger(2),
        "num_temporal_layers" / BitsInteger(3),
        "temporal_id_nested" / BitsInteger(1),
        "nalu_length_size" / BitsInteger(2),
    ),
    # TODO: parse NALUs
    "raw_bytes" / GreedyBytes
)

AVC1SampleEntryBox = Struct(
    "version" / Default(Int16ub, 0),
    "revision" / Const(Int16ub, 0),
    "vendor" / Default(String(4, padchar=b" "), b"brdy"),
    "temporal_quality" / Default(Int32ub, 0),
    "spatial_quality" / Default(Int32ub, 0),
    "width" / Int16ub,
    "height" / Int16ub,
    "horizontal_resolution" / Default(Int16ub, 72),  # TODO: actually a fixed point decimal
    Padding(2),
    "vertical_resolution" / Default(Int16ub, 72),  # TODO: actually a fixed point decimal
    Padding(2),
    "data_size" / Const(Int32ub, 0),
    "frame_count" / Default(Int16ub, 1),
    "compressor_name" / Default(String(32, padchar=b" "), ""),
    "depth" / Default(Int16ub, 24),
    "color_table_id" / Default(Int16sb, -1),
    "avc_data" / PrefixedIncludingSize(Int32ub, Struct(
    "type" / String(4, padchar=b" ", paddir="right"),
        Embedded(Switch(this.type, {
            b"avcC": AAVC,
            b"hvcC": HVCC,
        }, Struct("data" / GreedyBytes)))
    )),
    "sample_info" / LazyBound(lambda _: GreedyRange(Box))
)

SampleEntryBox = PrefixedIncludingSize(Int32ub, Struct(
    "format" / String(4, padchar=b" ", paddir="right"),
    Padding(6, pattern=b"\x00"),
    "data_reference_index" / Default(Int16ub, 1),
    Embedded(Switch(this.format, {
        b"ec-3": MP4ASampleEntryBox,
        b"mp4a": MP4ASampleEntryBox,
        b"enca": MP4ASampleEntryBox,
        b"avc1": AVC1SampleEntryBox,
        b"encv": AVC1SampleEntryBox,
        b"evte": EventMessageSampleEntry,
        b"urim": URIMetaSampleEntry, 
        b"stpp": XMLSubtitleSampleEntry, 
        b"wvtt": WVTTSampleEntry,
    }, Struct("data" / GreedyBytes)))
))



BitRateBox = Struct(
    "type" / Const(b"btrt"),
    "bufferSizeDB" / Int32ub,
    "maxBitrate" / Int32ub,
    "avgBirate" / Int32ub,
)

SampleDescriptionBox = Struct(
    "type" / Const(b"stsd"),
    "version" / Default(Int8ub, 0),
    "flags" / Const(Int24ub, 0),
    "entries" / PrefixedArray(Int32ub, SampleEntryBox)
)

ExtendedLanguageTag = Struct(
    "type" / Const(b"elng"),
    "version" / Default(Int8ub, 0),
    "flags" / Const(Int24ub, 0),
    "extended_language" / CString(encoding="utf8")
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
    "entries" / Default(PrefixedArray(Int32ub, Struct(
        "sample_count" / Int32ub,
        "sample_delta" / Int32ub,
    )), [])
)

SyncSampleBox = Struct(
    "type" / Const(b"stss"),
    "version" / Const(Int8ub, 0),
    "flags" / Const(Int24ub, 0),
    "entries" / Default(PrefixedArray(Int32ub, Struct(
        "sample_number" / Int32ub,
    )), [])
)

SampleToChunkBox = Struct(
    "type" / Const(b"stsc"),
    "version" / Const(Int8ub, 0),
    "flags" / Const(Int24ub, 0),
    "entries" / Default(PrefixedArray(Int32ub, Struct(
        "first_chunk" / Int32ub,
        "samples_per_chunk" / Int32ub,
        "sample_description_index" / Int32ub,
    )), [])
)

ChunkOffsetBox = Struct(
    "type" / Const(b"stco"),
    "version" / Const(Int8ub, 0),
    "flags" / Const(Int24ub, 0),
    "entries" / Default(PrefixedArray(Int32ub, Struct(
        "chunk_offset" / Int32ub,
    )), [])
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

MetaBox = Struct(
    "type" / Const(b"meta"),
    "version" / Const(Int8ub, 0),
     Padding(3, pattern=b"\x00"),
    "children" / LazyBound(lambda _: GreedyRange(Box))
)

PrimaryItemBox = Struct(
    "type" / Const(b"pitm"),
    "version" / Default(Int8ub, 0),
    "flags" / Const(Int24ub, 0),
    Embedded(Switch(this.version, {
        0: Struct("item_ID" / Int16ub),
        1: Struct("item_ID" / Int32ub),
    })),
)

ItemProtectionBox = Struct(
    "type" / Const(b"ipro"),
    "version" / Const(Int8ub, 0),
    "flags" / Const(Int24ub, 0),
    "protection_count" / Int16ub,
    "protection_information" / LazyBound(lambda _: GreedyRange(Box))
)

ProducerReferenceTimeBox = Struct(
    "type" / Const(b"prft"),
    "version" / Default(Int8ub, 0),
    Padding(3, pattern=b"\x00"),
    "reference_track_ID" / Int32ub, 
    "ntp_timestamp" / Int64ub,
    Embedded(Switch(this.version, {
        0: Struct( "media_time" / Int32ub),
        1: Struct( "media_time" / Int64ub),
    })),
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
    "is_leading" / Default(Enum(BitsInteger(2), UNKNOWN=0, LEADINGDEP=1, NOTLEADING=2, LEADINGNODEP=3, default=0), 0),
    "sample_depends_on" / Default(Enum(BitsInteger(2), UNKNOWN=0, DEPENDS=1, NOTDEPENDS=2, RESERVED=3, default=0), 0),
    "sample_is_depended_on" / Default(Enum(BitsInteger(2), UNKNOWN=0, NOTDISPOSABLE=1, DISPOSABLE=2, RESERVED=3, default=0), 0),
    "sample_has_redundancy" / Default(Enum(BitsInteger(2), UNKNOWN=0, REDUNDANT=1, NOTREDUNDANT=2, RESERVED=3, default=0), 0),
    "sample_padding_value" / Default(BitsInteger(3), 0),
    "sample_is_non_sync_sample" / Default(Flag, False),
    "sample_degradation_priority" / Default(BitsInteger(16), 0),
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
    "data_offset" / Default(If(this.flags.data_offset_present, Int32sb), None),
    "first_sample_flags" / Default(If(this.flags.first_sample_flags_present, Int32ub), None),
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
    "base_data_offset" / Default(If(this.flags.base_data_offset_present, Int64ub), None),
    "sample_description_index" / Default(If(this.flags.sample_description_index_present, Int32ub), None),
    "default_sample_duration" / Default(If(this.flags.default_sample_duration_present, Int32ub), None),
    "default_sample_size" / Default(If(this.flags.default_sample_size_present, Int32ub), None),
    "default_sample_flags" / Default(If(this.flags.default_sample_flags_present, TrackSampleFlags), None),
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
    "default_sample_description_index" / Default(Int32ub, 1),
    "default_sample_duration" / Default(Int32ub, 0),
    "default_sample_size" / Default(Int32ub, 0),
    "default_sample_flags" / Default(TrackSampleFlags, Container()),
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

SampleAuxiliaryInformationSizesBox = Struct(
    "type" / Const(b"saiz"),
    "version" / Const(Int8ub, 0),
    "flags" / BitStruct(
        Padding(23),
        "has_aux_info_type" / Flag,
    ),
    # Optional fields
    "aux_info_type" / Default(If(this.flags.has_aux_info_type, Int32ub), None),
    "aux_info_type_parameter" / Default(If(this.flags.has_aux_info_type, Int32ub), None),
    "default_sample_info_size" / Int8ub,
    "sample_count" / Int32ub,
    # only if sample default_sample_info_size is 0
    "sample_info_sizes" / If(this.default_sample_info_size == 0,
                             Array(this.sample_count, Int8ub))
)

SampleAuxiliaryInformationOffsetsBox = Struct(
    "type" / Const(b"saio"),
    "version" / Int8ub,
    "flags" / BitStruct(
        Padding(23),
        "has_aux_info_type" / Flag,
    ),
    # Optional fields
    "aux_info_type" / Default(If(this.flags.has_aux_info_type, Int32ub), None),
    "aux_info_type_parameter" / Default(If(this.flags.has_aux_info_type, Int32ub), None),
    # Short offsets in version 0, long in version 1
    "offsets" / PrefixedArray(Int32ub, Switch(this.version, {0: Int32ub, 1: Int64ub}))
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
    "reserved" / Const(Int16ub, 0)
)


# DASH Boxes

class UUIDBytes(Adapter):
    def _decode(self, obj, context):
        return UUID(bytes=obj)

    def _encode(self, obj, context):
        return obj.bytes

# event message boxes
EventMessageInstanceBox = Struct(
    "type" / Const(b"emib"),
    "version" / Default(Int8ub, 0),
    "flags" / Const(Int24ub, 0),
    "reserved" / Default(Int32ub, 0),
    "presentation_time_delta" / Int64sb,
    "duration" / Int32ub,
    "id" / Int32ub,
    "scheme_id_uri" / CString(),
    "value" / CString(), 
    "message_data" / GreedyBytes,
)
    

DASHEventMessageBox = Struct(
    "type" / Const(b"emsg"),
    "version" / Default(Int8ub, 0),
    "flags" / Const(Int24ub, 0),
    Embedded(Switch(this.version, {
        0: Struct(
            "scheme_id_uri" /  CString(),
            "value" /  CString(), 
            "timescale" / Default(Int32ub, 0),
            "presentation_time_delta" / Default(Int32ub, 0),
            "event_duration" / Int32ub,
            "id" / Int32ub,
        ),
        1: Struct(
            "timescale" / Default(Int32ub, 0),
            "presentation_time" / Default(Int64ub, 0),
            "event_duration" / Int32ub,
            "id" / Int32ub,
            "scheme_id_uri" /  CString(),
            "value" /  CString(), 
        ),
    })),
    "message_data" / GreedyBytes, 
)



EventMessageEmptyBox = Struct(
     "type" / Const(b"emeb")
)

EventMessageBoxEmptyCue = Struct(
     "type" / Const(b"embe")
)

# pssh boxes
ProtectionSystemHeaderBox = Struct(
    "type" / If(this._.type != b"uuid", Const(b"pssh")),
    "version" / Rebuild(Int8ub, lambda ctx: 1 if (hasattr(ctx, "key_IDs") and ctx.key_IDs) else 0),
    "flags" / Const(Int24ub, 0),
    "system_ID" / UUIDBytes(Bytes(16)),
    "key_IDs" / Default(If(this.version == 1,
                           PrefixedArray(Int32ub, UUIDBytes(Bytes(16)))),
                        None),
    "init_data" / Prefixed(Int32ub, GreedyBytes)
)

TrackEncryptionBox = Struct(
    "type" / If(this._.type != b"uuid", Const(b"tenc")),
    "version" / Default(Int8ub, 0),
    "flags" / Default(Int24ub, 0),
    "_reserved0" / Const(Int8ub, 0),
    "_reserved1" / Const(Int8ub, 0),
    "is_encrypted" / Int8ub,
    "iv_size" / Int8ub,
    "key_ID" / UUIDBytes(Bytes(16)),
    "constant_iv" / Default(If(this.is_encrypted and this.iv_size == 0,
                               PrefixedArray(Int8ub, Byte),
                               ),
                            None)

)

SampleEncryptionBox = Struct(
    "type" / If(this._.type != b"uuid", Const(b"senc")),
    "version" / Const(Int8ub, 0),
    "flags" / BitStruct(
        Padding(22),
        "has_subsample_encryption_info" / Flag,
        Padding(1)
    ),
    "sample_encryption_info" / PrefixedArray(Int32ub, Struct(
        "iv" / Bytes(8),
        # include the sub sample encryption information
        "subsample_encryption_info" / Default(If(this.flags.has_subsample_encryption_info, PrefixedArray(Int16ub, Struct(
            "clear_bytes" / Int16ub,
            "cipher_bytes" / Int32ub
        ))), None)
    ))
)

OriginalFormatBox = Struct(
    "type" / Const(b"frma"),
    "original_format" / Default(String(4), b"avc1")
)

SchemeTypeBox = Struct(
    "type" / Const(b"schm"),
    "version" / Default(Int8ub, 0),
    "flags" / Default(Int24ub, 0),
    "scheme_type" / Default(String(4), b"cenc"),
    "scheme_version" / Default(Int32ub, 0x00010000),
    "schema_uri" / Default(If(this.flags & 1 == 1, CString(encoding="utf8")), None)
)

ProtectionSchemeInformationBox = Struct(
    "type" / Const(b"sinf"),
    # TODO: define which children are required 'schm', 'schi' and 'tenc'
    "children" / LazyBound(lambda _: GreedyRange(Box))
)

# PIFF boxes

UUIDBox = Struct(
    "type" / Const(b"uuid"),
    "extended_type" / UUIDBytes(Bytes(16)),
    "data" / Switch(this.extended_type, {
        UUID("A2394F52-5A9B-4F14-A244-6C427C648DF4"): SampleEncryptionBox,
        UUID("D08A4F18-10F3-4A82-B6C8-32D8ABA183D3"): ProtectionSystemHeaderBox,
        UUID("8974DBCE-7BE7-4C51-84F9-7148F9882554"): TrackEncryptionBox
    }, GreedyBytes)
)




### webVTT Cue boxes (only for use in samples, this is not for use in ISO-BMFF)
VTTCueBox = Struct(
    "type" / Const(b'vttc'),
    "children" / LazyBound(lambda _: GreedyRange(Box))
)

CueSourceIDBox = Struct( 
    "type" / Const(b'vsid'), 
    "source_ID" / Int32sb 
)

CueTimeBox = Struct(
     "type"  / Const(b'ctim'),
     "cue_current_time" / Default(GreedyBytes, b"")
)

CueIDBox = Struct(
   "type" / Const(b'iden'),
   "cue_id"/ Default(GreedyBytes, b"")
)

CueSettingsBox = Struct(
     "type"/ Const(b'sttg'),
     "settings"/ Default(GreedyBytes, b"")
)

CuePayLoadBox = Struct(
     "type"/ Const(b'pay1'),
     "cue_text"/  Default(GreedyBytes, b"")
)

VTTEmptyCueBox = Struct(
     "type" / Const(b'vtte') 
)

VTTAdditionalTextBox = Struct(
     "type" / Const(b'vtta'), 
     "cue_additional_text" / Default(GreedyBytes, b"")
)


class TellMinusSizeOf(Subconstruct):
    def __init__(self, subcon):
        super(TellMinusSizeOf, self).__init__(subcon)
        self.flagbuildnone = True

    def _parse(self, stream, context, path):
        return stream.tell() - self.subcon.sizeof(context)

    def _build(self, obj, stream, context, path):
        return b""

    def sizeof(self, context=None, **kw):
        return 0


Box = PrefixedIncludingSize(Int32ub, Struct(
    "offset" / TellMinusSizeOf(Int32ub),
    "type" / Peek(String(4, padchar=b" ", paddir="right")),
    Embedded(Switch(this.type, {
        BoxType.FTYP.value: FileTypeBox,
        BoxType.STYP.value: SegmentTypeBox,
        BoxType.MVHD.value: MovieHeaderBox,
        BoxType.MOOV.value: ContainerBoxLazy,
        BoxType.MOOF.value: ContainerBoxLazy,
        BoxType.MFHD.value: MovieFragmentHeaderBox,
        BoxType.TFDT.value: TrackFragmentBaseMediaDecodeTimeBox,
        BoxType.TRUN.value: TrackRunBox,
        BoxType.EDTS.value: EditBox,
        BoxType.ELST.value: EditListBox,
        BoxType.TFHD.value: TrackFragmentHeaderBox,
        BoxType.TRAF.value: ContainerBoxLazy,
        BoxType.MVEX.value: ContainerBoxLazy,
        BoxType.MEHD.value: MovieExtendsHeaderBox,
        BoxType.TREX.value: TrackExtendsBox,
        BoxType.TRAK.value: ContainerBoxLazy,
        BoxType.MDIA.value: ContainerBoxLazy,
        BoxType.TKHD.value: TrackHeaderBox,
        BoxType.MDAT.value: MovieDataBox,
        BoxType.FREE.value: FreeBox,
        BoxType.SKIP.value: SkipBox,
        BoxType.MDHD.value: MediaHeaderBox,
        BoxType.HDLR.value: HandlerReferenceBox,
        BoxType.MINF.value: ContainerBoxLazy,
        BoxType.VMHD.value: VideoMediaHeaderBox,
        BoxType.DINF.value: ContainerBoxLazy,
        BoxType.DREF.value: DataReferenceBox,
        BoxType.STBL.value: ContainerBoxLazy,
        BoxType.STSD.value: SampleDescriptionBox,
        BoxType.STSZ.value: SampleSizeBox,
        BoxType.STZ2.value: SampleSizeBox2,
        BoxType.STTS.value: TimeToSampleBox,
        BoxType.STSS.value: SyncSampleBox,
        BoxType.STSC.value: SampleToChunkBox,
        BoxType.STCO.value: ChunkOffsetBox,
        BoxType.CTTS.value: CompositionOffsetBox, 
        BoxType.CO64.value: ChunkLargeOffsetBox,
        BoxType.SMHD.value: SoundMediaHeaderBox,
        BoxType.SIDX.value: SegmentIndexBox,
        BoxType.SAIZ.value: SampleAuxiliaryInformationSizesBox,
        BoxType.SAIO.value: SampleAuxiliaryInformationOffsetsBox,
        BoxType.BTRT.value: BitRateBox,

        # Meta boxes (for completeness)
        BoxType.META.value: MetaBox,
        BoxType.PITM.value: PrimaryItemBox,
        BoxType.IPRO.value: ItemProtectionBox,
        BoxType.PRFT.value: ProducerReferenceTimeBox,
        # dash
        BoxType.TENC.value: TrackEncryptionBox,
        BoxType.PSSH.value: ProtectionSystemHeaderBox,
        BoxType.SENC.value: SampleEncryptionBox,
        BoxType.SINF.value: ProtectionSchemeInformationBox,
        BoxType.FRMA.value: OriginalFormatBox,
        BoxType.SCHM.value: SchemeTypeBox,
        BoxType.SCHI.value: ContainerBoxLazy,
        # piff
        BoxType.UUID.value: UUIDBox,
        # HDS boxes
        BoxType.ABST.value: HDSSegmentBox,
        BoxType.ASRT.value: HDSSegmentRunBox,
        BoxType.AFRT.value: HDSFragmentRunBox,
        # event track 
        BoxType.EMSG.value: DASHEventMessageBox,
        BoxType.EMBE.value: EventMessageBoxEmptyCue,
        BoxType.EMEB.value: EventMessageEmptyBox, 
        BoxType.EMIB.value: EventMessageInstanceBox,
        BoxType.URIM.value: URIMetaSampleEntry,
        BoxType.EVTE.value: EventMessageSampleEntry,
        BoxType.URI_.value: URIBox, 
        BoxType.URI.value: URIBox, 
        BoxType.URII.value: URIInitBox,

        # subtitle 
        BoxType.NMHD.value: NullMediaHeaderBox, 
        BoxType.STHD.value: SubtitleMediaHeaderBox,
        BoxType.VTTC.value: WebVTTConfigurationBox,
        BoxType.VLAB.value: WebVTTSourceLabelBox, 

        # VTT internal
        BoxType.VTTc.value : VTTCueBox,
        BoxType.VSID.value : CueSourceIDBox, 
        BoxType.CTIM.value : CueTimeBox,
        BoxType.IDEN.value : CueIDBox,
        BoxType.STTG.value : CueSettingsBox,
        BoxType.PAY1.value : CuePayLoadBox,
        BoxType.VTTE.value : VTTEmptyCueBox,
        BoxType.VTTA.value : VTTAdditionalTextBox
    }, default=RawBox)),
    "end" / Tell
))

ContainerBox = Struct(
    "type" / String(4, padchar=b" ", paddir="right"),
    "children" / GreedyRange(Box)
)

MP4 = GreedyRange(Box)

BoxClass = type(Box)


# simple helper for recursive box search
def find_child_box_by_type(parent_box, box_type):
    res = None
    if (parent_box["type"] == box_type):
        return parent_box
    else:
        if "children" in parent_box:
            for child_box in parent_box["children"]:
                res = find_child_box_by_type(child_box, box_type)
                if (res != None):
                    return res
        else:
            return None



# find samples in case of progressive mp4
def find_samples_progressive(trak_box):
    
    sample_count = 0
    samples = []

    # edit list and sample table 
    stbl = find_child_box_by_type(trak_box, b"stbl")
    elst = find_child_box_by_type(trak_box, b"elst")

    if stbl != None:
        # children of sample table
        stts = find_child_box_by_type(stbl, b"stts")
        ctts = find_child_box_by_type(stbl, b"ctts")
        stsz = find_child_box_by_type(stbl, b"stsz")
        stsc = find_child_box_by_type(stbl, b"stsc")
        stco = find_child_box_by_type(stbl, b"stco")
        st64 = find_child_box_by_type(stbl, b"co64")
        
        # find number of samples
        if "sample_count" in stsz:
            sample_count = stsz["sample_count"]
            #print ("number of samples is", sample_count)

        current_time = 0

        for a in stts.entries:
            for z in range(a["sample_count"]):
                current_time = current_time + a["sample_delta"]
                samples.append( { 'decode_time': current_time } )
        
        ctts_sample = 0
        if ctts != None: 
            for entry in ctts["entries"]:
                for i in entry["sample_count"]: 
                    samples[ctts_sample]["composition_time"] = samples[ctts_sample]["decode_time"] + entry["sample_offset"]
                    ctts_sample+=1

        # edit lists only partially supported
        if elst != None:
            edit_offset = 0

            ## shifts composition to media presentation timeline
            if len(elst["entries"]) > 2: 
                print ("error current version of validator only supports up to two edit list entries")
                return None
        
            ## 1 entry empty
            if(len(elst["entries"]) == 1):
                if( elst["entries"][0]["media_time"] == -1):
                    print("error the last edit is an empty edit, not supported in this version of verify")
                    return None

                ## single edit assume it is a naive shift
                edit_offset = - elst["entries"][0]["media_time"]
        
            ## two edits, only support with first edit being the emtpy edit
            if(len(elst["entries"]) == 2):
                ## single edit
                if( -1 == elst["entries"][0]["media_time"]):
                    edit_offset  = \
                         elst["entries"][0]["edit_duration"] - elst["entries"][1]["media_time"]
            
            for k in range(samples):
                if "composition_time" in sample[k]:
                    sample[k]["presentation_time"] = sample[k]["composition_time"] + edit_offset
                else:
                    sample[k]["decode_time"] = sample[k]["composition_time"] + edit_offset

        if stsz["sample_size"] == 0:
            for a in range(stsz.sample_count):
                 samples[a]["size"] = stsz["entry_sizes"][a]
        else:
            for a in range(stsz.entry_count):
                 samples[a]["size"] = stsz["sample_size"]

        current_sample = 0
        current_chunk = stsc.entries[0]["first_chunk"]
        i = 0

        while current_sample < sample_count:
            for j in range(stsc.entries[i]["samples_per_chunk"]):
                if(current_sample < len(samples)):
                    samples[current_sample]["chunk"] = current_chunk
                    current_sample += 1       
            current_chunk += 1
            if (i < (len(stsc.entries) - 1)):
                if stsc.entries[i + 1]["first_chunk"] == current_chunk:
                    i = i + 1
        
        st = None
        if (stco != None):
            st = stco 
        elif (st64 != None):
            st = st64

        if (st != None):
            for sample in samples:
                #print ("sample nr and lenght of entries", sample["chunk"] - 1 , len(st["entries"]) )
                sample["chunk_offset"] = st["entries"][sample["chunk"] - 1]["chunk_offset"]
        
        sample_size = 0

        for i in range(len(samples)):
            samples[i]["offset"] =  samples[i]["chunk_offset"] + sample_size 
            sample_size += samples[i]["size"]
            if (i < len(samples) -1):
                if (samples[i]["chunk_offset"] != samples[i+1]["chunk_offset"]):
                    sample_size = 0

        return samples
    else:
        return None 

###################################################################################
#     find sample times and offsets in case of fragmented/segmented mp4
#                           limitations 
#                   edit list only 1 or 2 entries
#              single traf box only per movie fragment
#                    only default base is moof
# ################################################################################# 
def find_samples_fragmented(movie_box, movie_fragment_box, supress_flags=False):
     
    if movie_fragment_box == None: 
        print("no movie fragment box given")
        return None

    if movie_box == None: 
        print("error no movie box given")
        return None
    
    mvhd = find_child_box_by_type(movie_box, b"mvhd")
    if mvhd == None :
        print("error moviebox does not containe movieheaderbox")
        return

    movie_fragment_size = movie_fragment_box["end"] - movie_fragment_box["offset"]
    movie_timescale = mvhd["timescale"]

    ## find trak and trex
    mvex = find_child_box_by_type(movie_box, b"mvex")  
    trex_boxes = []
    trak_boxes = []

    if(mvex != None):
        for child in mvex["children"]: 
           if child == None:
               print("none")
           
           if child["type"] == b"trex":
               trex_boxes.append(child)
    
    for child2 in movie_box["children"]: 
        if child2 != None:
            if child2["type"] == b"trak":
                trak_boxes.append(child2)

    
    ## get information from trak boxes
    track_infos = []

    for trak in trak_boxes:
        
        # use trakheader and mdhd to find id and timescales
        track_info = dict()

        mdhd = find_child_box_by_type(trak, b"mdhd")
        tkhd = find_child_box_by_type(trak, b"tkhd")
        elst = find_child_box_by_type(trak, b"elst")
        
        if tkhd != None: 
           track_info["track_ID"] = tkhd["track_ID"]

        if mdhd != None: 
           track_info["timescale"] =  mdhd["timescale"]
        
        track_info["edit_composition_offset"] = 0 ## default edit composition
        if elst != None:

            ## shifts composition to media presentation timeline
            if len(elst["entries"]) > 2: 
                print ("error current version of verify only supports up to two edit list entries")
                return
        
            ## 1 entry empty
            if(len(elst["entries"]) == 1):
                if( elst["entries"][0]["media_time"] == -1):
                    print("error the last edit is an empty edit, not supported in this version of verify")

            ## single edit assume it is a naive shift
            track_info["edit_composition_offset"] = - elst["entries"][0]["media_time"]
        
            ## two edits, only support with first edit being the emtpy edit
            if(len(elst["entries"]) == 2):
                ## single edit
                if( -1 == elst["entries"][0]["media_time"]):
                    track_info["edit_composition_offset"] = \
                         elst["entries"][0]["edit_duration"] - elst["entries"][1]["media_time"]
        
        track_infos.append(track_info)


    traf_boxes = [] 

    for traf_box in movie_fragment_box["children"]: 
        if traf_box["type"] == b"traf":
            traf_boxes.append(traf_box)
    
    if len(traf_boxes) == 0:
        print("error no traf box in movie fragment, current verify version only supports one or more")
        return None

    elif len(traf_boxes) > 1:
        print ("error only single traf box supported by current verify version, multiple traf boxes found")
        return None

    ## in this first version we only check the single traf box
    elif len(traf_boxes) == 1:
        
        ## find the track fragment header
        tfhd = find_child_box_by_type(traf_boxes[0], b"tfhd")
        
        if(tfhd == None):
            print("error no track fragment header ")
            return None

        tfdt = find_child_box_by_type(traf_boxes[0], b"tfdt")
        
        if(tfdt == None):
            print("error current verify version only supports fragments with tfdt box")
            return None

        ## duration is empty
        if(tfhd["flags"]["duration_is_empty"]):
            print("fragment duration is empty, returning empty list")
            return [] 
        
        ## default base is moof is currently only supported mode (iso 5 brand or higer), todo update for base data offsets
        elif( not(tfhd["flags"]["default_base_is_moof"] == 1)): 
            print("error this verify version only supports default base is moof == 1 and base-data-offset-present==0")
            return None 
        
        ## find the track if 
        track_id = tfhd["track_ID"]

        l_defs = dict(track_ID=0,default_sample_description_index=0 , \
        default_sample_duration=0 , default_sample_size=0, trex_found=0)
        
        for i in range(len(track_infos)):
            if "track_ID" in track_infos[i]:
                if track_id == track_infos[i]["track_ID"]:
                    l_defs["track_id_found"] = True
                    l_defs["timescale"] = track_infos[i]["timescale"] 
                    l_defs["track_ID"] = track_infos[i]["track_ID"] 
                    l_defs["edit_composition_offset"] = track_infos[i]["edit_composition_offset"] \
                        * track_infos[i]["timescale"] / movie_timescale
         
        if( "track_id_found" not in  l_defs):
            print("error track id not found")
            print(track_infos)
            return
         
        ## find the default values from trex (track defaults)
        for trex_box in trex_boxes:
            if(trex_box["track_ID"] == track_id):
                l_defs["trex_found"] = 1
                l_defs["default_sample_description_index"] = trex_box["default_sample_description_index"]
                l_defs["default_sample_duration"] = trex_box["default_sample_duration"]
                l_defs["default_sample_size"] = trex_box["default_sample_size"]
                l_defs["track_sample_flags"] = trex_box["default_sample_flags"] ## track sample flags 
             
        
        ##  overwrite by segment defaults from tfhd 
        if(tfhd["flags"]["sample_description_index_present"]):
            l_defs["default_sample_description_index"] = tfhd["sample_description_index"]
        if(tfhd["flags"]["default_sample_duration_present"]):
            l_defs["default_sample_duration"] = tfhd["default_sample_duration"]
        if(tfhd["flags"]["default_sample_size_present"]):
            l_defs["default_sample_size"] = tfhd = ["default_sample_size"]
        if(tfhd["flags"]["default_sample_flags_present"]):
            l_defs["track_sample_flags"] = tfhd["default_sample_flags"]
        if(tfhd["flags"]["base_data_offset_present"] == 1): 
             l_defs["data_offset"] = tfhd["base_data_offset"]
        else: 
             l_defs["data_offset"] = 0

        ##  initial values
        decode_time = tfdt["baseMediaDecodeTime"]
        offset_moof = l_defs["data_offset"]
        offset_mdat = l_defs["data_offset"] - movie_fragment_size
        
        ## find the trun box 
        trun = find_child_box_by_type(traf_boxes[0], b"trun")

        ## in current version having a trun box is mandatory
        if(trun == None):
            print("error this verify version only supports having a trun box in a media segment")
            return None 
        

        # parse trun for decode time, comp time , size , duration, flags, offset 
        
        sample_count = trun["sample_count"]
        print ("the number of samples is: ", sample_count)
        samples = []

        if trun["flags"]["data_offset_present"]:
            offset_mdat += trun["data_offset"] 
            offset_moof += trun["data_offset"]

        for i in range (sample_count):
            
            sample = dict( \
            decode_time=decode_time, \
            composition_time=decode_time, \
            presentation_time=decode_time + l_defs["edit_composition_offset"],  \
            duration=l_defs["default_sample_duration"], \
            size=l_defs["default_sample_size"], \
            offset_moof=offset_moof, \
            offset_mdat=offset_mdat,  \
            time_scale=l_defs["timescale"]) 
            if not(supress_flags):
                sample["flags"]=l_defs["track_sample_flags"]
            
            if trun["flags"]["sample_duration_present"]:
                sample["duration"]  = trun["sample_info"][i]["sample_duration"]
            if trun["flags"]["sample_size_present"]:
                sample["size"]  = trun["sample_info"][i]["sample_size"]
            if trun["flags"]["sample_composition_time_offsets_present"]:
                sample["composition_time"]  = decode_time + trun["sample_info"][i]["sample_composition_time_offsets"]
                sample["presentation_time"] = l_defs["edit_composition_offset"] + sample["composition_time"]
            if not(supress_flags):
               if trun["flags"]["sample_flags_present"]: 
                  sample["flags"] = trun["sample_info"][i]["sample_flags"]
               if i == 0 and trun["flags"]["first_sample_flags_present"] :
                  sample["flags"] =  trun["first_sample_flags"]
            
            samples.append(sample)

            decode_time += sample["duration"] 
            offset_mdat += sample["size"] 
            offset_moof += sample["size"]

        return samples 

    else: 
        print("error current version of verify only supports single trun box per track fragment box")
        return None