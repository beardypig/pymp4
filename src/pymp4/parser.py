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
from sys import maxsize

log = logging.getLogger(__name__)

UNITY_MATRIX = [0x10000, 0, 0, 0, 0x10000, 0, 0, 0, 0x40000000]

STRING_ENCODING = "utf8"

# Header box

FileTypeBox = Struct(
    "type" / Const("ftyp".encode(STRING_ENCODING)),
    "major_brand" / PaddedString(4, STRING_ENCODING),
    "minor_version" / Int32ub,
    "compatible_brands" / GreedyRange(PaddedString(4, STRING_ENCODING)),
)

SegmentTypeBox = Struct(
    "type" / Const("styp".encode(STRING_ENCODING)),
    "major_brand" / PaddedString(4, STRING_ENCODING),
    "minor_version" / Int32ub,
    "compatible_brands" / GreedyRange(PaddedString(4, STRING_ENCODING)),
)

# Catch find boxes

RawBox = Struct(
    "type" / PaddedString(4, STRING_ENCODING),
    "data" / Default(GreedyBytes, b"")
)

FreeBox = Struct(
    "type" / Const("free".encode(STRING_ENCODING)),
    "data" / GreedyBytes
)

SkipBox = Struct(
    "type" / Const("skip".encode(STRING_ENCODING)),
    "data" / GreedyBytes
)

# Movie boxes, contained in a moov Box

MovieHeaderBox = Struct(
    "type" / Const("mvhd".encode(STRING_ENCODING)),
    "version" / Default(Int8ub, 0),
    "flags" / Default(Int24ub, 0),
    Switch(this.version, {
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
    }),
    "rate" / Default(Int32sb, 65536),
    "volume" / Default(Int16sb, 256),
    # below could be just Padding(10) but why not
    Padding(10),
    "matrix" / Default(Int32sb[9], UNITY_MATRIX),
    "pre_defined" / Default(Int32ub[6], [0] * 6),
    "next_track_ID" / Default(Int32ub, 0xffffffff)
)

# Track boxes, contained in trak box

TrackHeaderBox = Struct(
    "type" / Const("tkhd".encode(STRING_ENCODING)),
    "version" / Default(Int8ub, 0),
    "flags" / Default(Int24ub, 1),
    Switch(this.version, {
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
    }),
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
    "type" / Const("abst".encode(STRING_ENCODING)),
    "version" / Default(Int8ub, 0),
    "flags" / Default(Int24ub, 0),
    "info_version" / Int32ub,
    BitStruct(
        Padding(1),
        "profile" / Flag,
        "live" / Flag,
        "update" / Flag,
        Padding(4)
    ),
    "time_scale" / Int32ub,
    "current_media_time" / Int64ub,
    "smpte_time_code_offset" / Int64ub,
    "movie_identifier" / CString(STRING_ENCODING),
    "server_entry_table" / PrefixedArray(Int8ub, CString(STRING_ENCODING)),
    "quality_entry_table" / PrefixedArray(Int8ub, CString(STRING_ENCODING)),
    "drm_data" / CString(STRING_ENCODING),
    "metadata" / CString(STRING_ENCODING),
    "segment_run_table" / PrefixedArray(Int8ub, LazyBound(lambda x: Box)),
    "fragment_run_table" / PrefixedArray(Int8ub, LazyBound(lambda x: Box))
)

HDSSegmentRunBox = Struct(
    "type" / Const("asrt".encode(STRING_ENCODING)),
    "version" / Default(Int8ub, 0),
    "flags" / Default(Int24ub, 0),
    "quality_entry_table" / PrefixedArray(Int8ub, CString(STRING_ENCODING)),
    "segment_run_enteries" / PrefixedArray(Int32ub, Struct(
        "first_segment" / Int32ub,
        "fragments_per_segment" / Int32ub
    ))
)

HDSFragmentRunBox = Struct(
    "type" / Const("afrt".encode(STRING_ENCODING)),
    "version" / Default(Int8ub, 0),
    "flags" / BitStruct(
        Padding(23),
        "update" / Flag
    ),
    "time_scale" / Int32ub,
    "quality_entry_table" / PrefixedArray(Int8ub, CString(STRING_ENCODING)),
    "fragment_run_enteries" / PrefixedArray(Int32ub, Struct(
        "first_fragment" / Int32ub,
        "first_fragment_timestamp" / Int64ub,
        "fragment_duration" / Int32ub,
        "discontinuity" / If(this.fragment_duration == 0, Int8ub)
    ))
)


# Boxes contained by Media Box

class ISO6392TLanguageCode(Adapter):
    def _decode(self, obj, context, path):
        """
        Get the python representation of the obj
        """
        return b''.join(map(int2byte, [c + 0x60 for c in bytearray(obj)])).decode(STRING_ENCODING)

    def _encode(self, obj, context, path):
        """
        Get the bytes representation of the obj
        """
        return [c - 0x60 for c in bytearray(obj.encode(STRING_ENCODING))]


MediaHeaderBox = Struct(
    "type" / Const("mdhd".encode(STRING_ENCODING)),
    "version" / Default(Int8ub, 0),
    "flags" / Const(0, Int24ub),
    "creation_time" / IfThenElse(this.version == 1, Int64ub, Int32ub),
    "modification_time" / IfThenElse(this.version == 1, Int64ub, Int32ub),
    "timescale" / Int32ub,
    "duration" / IfThenElse(this.version == 1, Int64ub, Int32ub),
    "language" / BitStruct(
        Padding(1),
        "code" / ISO6392TLanguageCode(BitsInteger(5)[3]),
    ),
    Padding(2, pattern=b"\x00"),
)

HandlerReferenceBox = Struct(
    "type" / Const("hdlr".encode(STRING_ENCODING)),
    "version" / Const(0, Int8ub),
    "flags" / Const(0, Int24ub),
    Padding(4, pattern=b"\x00"),
    "handler_type" / PaddedString(4, STRING_ENCODING),
    Padding(12, pattern=b"\x00"),  # Int32ub[3]
    "name" / CString(encoding=STRING_ENCODING)
)

# Boxes contained by Media Info Box

VideoMediaHeaderBox = Struct(
    "type" / Const("vmhd".encode(STRING_ENCODING)),
    "version" / Default(Int8ub, 0),
    "flags" / Const(1, Int24ub),
    "graphics_mode" / Default(Int16ub, 0),
    "opcolor" / Struct(
        "red" / Default(Int16ub, 0),
        "green" / Default(Int16ub, 0),
        "blue" / Default(Int16ub, 0),
    ),
)

DataEntryUrlBox = Prefixed(Int32ub, Struct(
    "type" / Const("url ".encode(STRING_ENCODING)),
    "version" / Const(0, Int8ub),
    "flags" / BitStruct(
        Padding(23), "self_contained" / Rebuild(Flag, ~this._.location)
    ),
    "location" / If(~this.flags.self_contained, CString(encoding=STRING_ENCODING)),
), includelength=True)

DataEntryUrnBox = Prefixed(Int32ub, Struct(
    "type" / Const("urn ".encode(STRING_ENCODING)),
    "version" / Const(0, Int8ub),
    "flags" / BitStruct(
        Padding(23), "self_contained" / Rebuild(Flag, ~(this._.name & this._.location))
    ),
    "name" / If(this.flags == 0, CString(encoding=STRING_ENCODING)),
    "location" / If(this.flags == 0, CString(encoding=STRING_ENCODING)),
), includelength=True)

DataReferenceBox = Struct(
    "type" / Const("dref".encode(STRING_ENCODING)),
    "version" / Const(0, Int8ub),
    "flags" / Default(Int24ub, 0),
    "data_entries" / PrefixedArray(Int32ub, Select(DataEntryUrnBox, DataEntryUrlBox)),
)

# Sample Table boxes (stbl)

MP4ASampleEntryBox = Struct(
    "version" / Default(Int16ub, 0),
    "revision" / Const(0, Int16ub),
    "vendor" / Const(0, Int32ub),
    "channels" / Default(Int16ub, 2),
    "bits_per_sample" / Default(Int16ub, 16),
    "compression_id" / Default(Int16sb, 0),
    "packet_size" / Const(0, Int16ub),
    "sampling_rate" / Int16ub,
    Padding(2)
)


class MaskedInteger(Adapter):
    def _decode(self, obj, context, path):
        return obj & 0x1F

    def _encode(self, obj, context, path):
        return obj & 0x1F


AAVC = Struct(
    "version" / Const(1, Int8ub),
    "profile" / Int8ub,
    "compatibility" / Int8ub,
    "level" / Int8ub,
    BitStruct(
        Padding(6, pattern=b'\x01'),
        "nal_unit_length_field" / Default(BitsInteger(2), 3),
    ),
    "sps" / Default(PrefixedArray(MaskedInteger(Int8ub), PascalString(Int16ub, STRING_ENCODING)), []),
    "pps" / Default(PrefixedArray(Int8ub, PascalString(Int16ub, STRING_ENCODING)), [])
)

HVCC = Struct(
    BitStruct(
        "version" / Const(1, BitsInteger(8)),
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
    "revision" / Const(0, Int16ub),
    "vendor" / Default(PaddedString(4, STRING_ENCODING), b"brdy"),
    "temporal_quality" / Default(Int32ub, 0),
    "spatial_quality" / Default(Int32ub, 0),
    "width" / Int16ub,
    "height" / Int16ub,
    "horizontal_resolution" / Default(Int16ub, 72),  # TODO: actually a fixed point decimal
    Padding(2),
    "vertical_resolution" / Default(Int16ub, 72),  # TODO: actually a fixed point decimal
    Padding(2),
    "data_size" / Const(0, Int32ub),
    "frame_count" / Default(Int16ub, 1),
    "compressor_name" / Default(PaddedString(32, STRING_ENCODING), ""),
    "depth" / Default(Int16ub, 24),
    "color_table_id" / Default(Int16sb, -1),
    "avc_data" / Prefixed(Int32ub, Struct(
    "type" / PaddedString(4, STRING_ENCODING),
        Switch(this.type, {
            u"avcC": AAVC,
            u"hvcC": HVCC,
        }, Struct("data" / GreedyBytes))
    ), includelength=True),
    "sample_info" / LazyBound(lambda _: GreedyRange(Box))
)

SampleEntryBox = Prefixed(Int32ub, Struct(
    "format" / PaddedString(4, STRING_ENCODING),
    Padding(6, pattern=b"\x00"),
    "data_reference_index" / Default(Int16ub, 1),
    "sample_entry_box" / Switch(this.format, {
        u"ec-3": MP4ASampleEntryBox,
        u"mp4a": MP4ASampleEntryBox,
        u"enca": MP4ASampleEntryBox,
        u"avc1": AVC1SampleEntryBox,
        u"encv": AVC1SampleEntryBox
    }, Struct("data" / GreedyBytes))
), includelength=True)

BitRateBox = Struct(
    "type" / Const("btrt".encode(STRING_ENCODING)),
    "bufferSizeDB" / Int32ub,
    "maxBitrate" / Int32ub,
    "avgBirate" / Int32ub,
)

SampleDescriptionBox = Struct(
    "type" / Const("stsd".encode(STRING_ENCODING)),
    "version" / Default(Int8ub, 0),
    "flags" / Const(0, Int24ub),
    "entries" / PrefixedArray(Int32ub, SampleEntryBox)
)

SampleSizeBox = Struct(
    "type" / Const("stsz".encode(STRING_ENCODING)),
    "version" / Int8ub,
    "flags" / Const(0, Int24ub),
    "sample_size" / Int32ub,
    "sample_count" / Int32ub,
    "entry_sizes" / If(this.sample_size == 0, Array(this.sample_count, Int32ub))
)

SampleSizeBox2 = Struct(
    "type" / Const("stz2".encode(STRING_ENCODING)),
    "version" / Int8ub,
    "flags" / Const(0, Int24ub),
    Padding(3, pattern=b"\x00"),
    "field_size" / Int8ub,
    "sample_count" / Int24ub,
    "entries" / Array(this.sample_count, Struct(
        "entry_size" / LazyBound(lambda ctx: globals()["Int%dub" % ctx.field_size])
    ))
)

SampleDegradationPriorityBox = Struct(
    "type" / Const("stdp".encode(STRING_ENCODING)),
    "version" / Const(0, Int8ub),
    "flags" / Const(0, Int24ub),
)

TimeToSampleBox = Struct(
    "type" / Const("stts".encode(STRING_ENCODING)),
    "version" / Const(0, Int8ub),
    "flags" / Const(0, Int24ub),
    "entries" / Default(PrefixedArray(Int32ub, Struct(
        "sample_count" / Int32ub,
        "sample_delta" / Int32ub,
    )), [])
)

SyncSampleBox = Struct(
    "type" / Const("stss".encode(STRING_ENCODING)),
    "version" / Const(0, Int8ub),
    "flags" / Const(0, Int24ub),
    "entries" / Default(PrefixedArray(Int32ub, Struct(
        "sample_number" / Int32ub,
    )), [])
)

SampleToChunkBox = Struct(
    "type" / Const("stsc".encode(STRING_ENCODING)),
    "version" / Const(0, Int8ub),
    "flags" / Const(0, Int24ub),
    "entries" / Default(PrefixedArray(Int32ub, Struct(
        "first_chunk" / Int32ub,
        "samples_per_chunk" / Int32ub,
        "sample_description_index" / Int32ub,
    )), [])
)

ChunkOffsetBox = Struct(
    "type" / Const("stco".encode(STRING_ENCODING)),
    "version" / Const(0, Int8ub),
    "flags" / Const(0, Int24ub),
    "entries" / Default(PrefixedArray(Int32ub, Struct(
        "chunk_offset" / Int32ub,
    )), [])
)

ChunkLargeOffsetBox = Struct(
    "type" / Const("co64".encode(STRING_ENCODING)),
    "version" / Const(0, Int8ub),
    "flags" / Const(0, Int24ub),
    "entries" / PrefixedArray(Int32ub, Struct(
        "chunk_offset" / Int64ub,
    ))
)

# Movie Fragment boxes, contained in moof box

MovieFragmentHeaderBox = Struct(
    "type" / Const("mfhd".encode(STRING_ENCODING)),
    "version" / Const(0, Int8ub),
    "flags" / Const(0, Int24ub),
    "sequence_number" / Int32ub
)

TrackFragmentBaseMediaDecodeTimeBox = Struct(
    "type" / Const("tfdt".encode(STRING_ENCODING)),
    "version" / Int8ub,
    "flags" / Const(0, Int24ub),
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
    "type" / Const("trun".encode(STRING_ENCODING)),
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
    "type" / Const("tfhd".encode(STRING_ENCODING)),
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
    "type" / Const("mehd".encode(STRING_ENCODING)),
    "version" / Default(Int8ub, 0),
    "flags" / Const(0, Int24ub),
    "fragment_duration" / IfThenElse(this.version == 1,
                                     Default(Int64ub, 0),
                                     Default(Int32ub, 0))
)

TrackExtendsBox = Struct(
    "type" / Const("trex".encode(STRING_ENCODING)),
    "version" / Const(0, Int8ub),
    "flags" / Const(0, Int24ub),
    "track_ID" / Int32ub,
    "default_sample_description_index" / Default(Int32ub, 1),
    "default_sample_duration" / Default(Int32ub, 0),
    "default_sample_size" / Default(Int32ub, 0),
    "default_sample_flags" / Default(TrackSampleFlags, None),
)

SegmentIndexBox = Struct(
    "type" / Const("sidx".encode(STRING_ENCODING)),
    "version" / Int8ub,
    "flags" / Const(0, Int24ub),
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
    "type" / Const("saiz".encode(STRING_ENCODING)),
    "version" / Const(0, Int8ub),
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
    "type" / Const("saio".encode(STRING_ENCODING)),
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
    "type" / Const("mdat".encode(STRING_ENCODING)),
    "data" / GreedyBytes
)

# Media Info Box

SoundMediaHeaderBox = Struct(
    "type" / Const("smhd".encode(STRING_ENCODING)),
    "version" / Const(0, Int8ub),
    "flags" / Const(0, Int24ub),
    "balance" / Default(Int16sb, 0),
    "reserved" / Const(0, Int16ub)
)


# DASH Boxes

class UUIDBytes(Adapter):
    def _decode(self, obj, context, path):
        return UUID(bytes=obj)

    def _encode(self, obj, context, path):
        return obj.bytes


ProtectionSystemHeaderBox = Struct(
    "type" / If(this._.type != u"uuid", Const("pssh".encode(STRING_ENCODING))),
    "version" / Rebuild(Int8ub, lambda ctx: 1 if (hasattr(ctx, "key_IDs") and ctx.key_IDs) else 0),
    "flags" / Const(0, Int24ub),
    "system_ID" / UUIDBytes(Bytes(16)),
    "key_IDs" / Default(If(this.version == 1,
                           PrefixedArray(Int32ub, UUIDBytes(Bytes(16)))),
                        None),
    "init_data" / Prefixed(Int32ub, GreedyBytes, includelength=True)
)

TrackEncryptionBox = Struct(
    "type" / If(this._.type != u"uuid", Const("tenc".encode(STRING_ENCODING))),
    "version" / Default(Int8ub, 0),
    "flags" / Default(Int24ub, 0),
    "_reserved0" / Const(0, Int8ub),
    "_reserved1" / Const(0, Int8ub),
    "is_encrypted" / Int8ub,
    "iv_size" / Int8ub,
    "key_ID" / UUIDBytes(Bytes(16)),
    "constant_iv" / Default(If(this.is_encrypted and this.iv_size == 0,
                               PrefixedArray(Int8ub, Byte),
                               ),
                            None)

)

SampleEncryptionBox = Struct(
    "type" / If(this._.type != u"uuid", Const("senc".encode(STRING_ENCODING))),
    "version" / Const(0, Int8ub),
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
    "type" / Const("frma".encode(STRING_ENCODING)),
    "original_format" / Default(PaddedString(4, STRING_ENCODING), b"avc1")
)

SchemeTypeBox = Struct(
    "type" / Const("schm".encode(STRING_ENCODING)),
    "version" / Default(Int8ub, 0),
    "flags" / Default(Int24ub, 0),
    "scheme_type" / Default(PaddedString(4, STRING_ENCODING), b"cenc"),
    "scheme_version" / Default(Int32ub, 0x00010000),
    "schema_uri" / Default(If(this.flags & 1 == 1, CString(STRING_ENCODING)), None)
)

ProtectionSchemeInformationBox = Struct(
    "type" / Const("sinf".encode(STRING_ENCODING)),
    # TODO: define which children are required 'schm', 'schi' and 'tenc'
    "children" / LazyBound(lambda _: GreedyRange(Box))
)

# PIFF boxes

UUIDBox = Struct(
    "type" / Const("uuid".encode(STRING_ENCODING)),
    "extended_type" / UUIDBytes(Bytes(16)),
    "data" / Switch(this.extended_type, {
        UUID("A2394F52-5A9B-4F14-A244-6C427C648DF4"): SampleEncryptionBox,
        UUID("D08A4F18-10F3-4A82-B6C8-32D8ABA183D3"): ProtectionSystemHeaderBox,
        UUID("8974DBCE-7BE7-4C51-84F9-7148F9882554"): TrackEncryptionBox
    }, GreedyBytes)
)

ContainerBoxLazy = LazyBound(lambda : ContainerBox)


class TellPlusSizeOf(Subconstruct):
    def __init__(self, subcon):
        super(TellPlusSizeOf, self).__init__(subcon)
        self.flagbuildnone = True

    def _parse(self, stream, context, path):
        return stream.tell() + self.subcon.sizeof(context=context)

    def _build(self, obj, stream, context, path):
        return b""

    def sizeof(self, context=None, **kw):
        return 0


Box = Prefixed(Int32ub, Struct(
    "offset" / Tell,
    "type" / Peek(PaddedString(4, STRING_ENCODING)),
    "box_body" / Switch(this.type, {
        u"ftyp": FileTypeBox,
        u"styp": SegmentTypeBox,
        u"mvhd": MovieHeaderBox,
        u"moov": ContainerBoxLazy,
        u"moof": ContainerBoxLazy,
        u"mfhd": MovieFragmentHeaderBox,
        u"tfdt": TrackFragmentBaseMediaDecodeTimeBox,
        u"trun": TrackRunBox,
        u"tfhd": TrackFragmentHeaderBox,
        u"traf": ContainerBoxLazy,
        u"mvex": ContainerBoxLazy,
        u"mehd": MovieExtendsHeaderBox,
        u"trex": TrackExtendsBox,
        u"trak": ContainerBoxLazy,
        u"mdia": ContainerBoxLazy,
        u"tkhd": TrackHeaderBox,
        u"mdat": MovieDataBox,
        u"free": FreeBox,
        u"skip": SkipBox,
        u"mdhd": MediaHeaderBox,
        u"hdlr": HandlerReferenceBox,
        u"minf": ContainerBoxLazy,
        u"vmhd": VideoMediaHeaderBox,
        u"dinf": ContainerBoxLazy,
        u"dref": DataReferenceBox,
        u"stbl": ContainerBoxLazy,
        u"stsd": SampleDescriptionBox,
        u"stsz": SampleSizeBox,
        u"stz2": SampleSizeBox2,
        u"stts": TimeToSampleBox,
        u"stss": SyncSampleBox,
        u"stsc": SampleToChunkBox,
        u"stco": ChunkOffsetBox,
        u"co64": ChunkLargeOffsetBox,
        u"smhd": SoundMediaHeaderBox,
        u"sidx": SegmentIndexBox,
        u"saiz": SampleAuxiliaryInformationSizesBox,
        u"saio": SampleAuxiliaryInformationOffsetsBox,
        u"btrt": BitRateBox,
        # dash
        u"tenc": TrackEncryptionBox,
        u"pssh": ProtectionSystemHeaderBox,
        u"senc": SampleEncryptionBox,
        u"sinf": ProtectionSchemeInformationBox,
        u"frma": OriginalFormatBox,
        u"schm": SchemeTypeBox,
        u"schi": ContainerBoxLazy,
        # piff
        u"uuid": UUIDBox,
        # HDS boxes
        u'abst': HDSSegmentBox,
        u'asrt': HDSSegmentRunBox,
        u'afrt': HDSFragmentRunBox
    }, default=RawBox),
    "end" / TellPlusSizeOf(Int32ub)
), includelength=True)

ContainerBox = Struct(
    "type" / PaddedString(4, STRING_ENCODING),
    "children" / GreedyRange(Box)
)

MP4 = GreedyRange(Box)
