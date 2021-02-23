"""
summary.py
"""
import os


class Summary:
    """ Summary Class for an Mp4File Class """

    def __init__(self, input_file, boxes):
        self.data = {}
        self.data['filename'] = input_file
        self.data['filesize (bytes)'] = os.path.getsize(input_file)
        fstyp = [box for box in boxes if box.type == b'ftyp' or box.type == b'styp'][0]
        self.data['brand'] = fstyp.major_brand
        # check if there is a moov and if there is a moov that contains traks N.B only ever 0,1 moov boxes
        if [box for box in boxes if box.type == b'moov']:
            moov = [box for box in boxes if box.type == b'moov'][0]
            mvhd = [mvbox for mvbox in moov.children if mvbox.type == b'mvhd'][0]
            self.data['creation_time'] = mvhd.creation_time
            self.data['modification_time'] = mvhd.modification_time
            self.data['duration (secs)'] = round(mvhd.duration / mvhd.timescale)
            if self.data['duration (secs)'] > 0:
                self.data['bitrate (bps)'] = round(8 * self.data['filesize (bytes)'] / self.data['duration (secs)'])
            traks = [tbox for tbox in moov.children if tbox.type == b'trak']
            self.data['track_list'] = []
            for trak in traks:
                this_trak = {}
                this_trak['track_id'] = [box for box in trak.children if box.type == b'tkhd'][0].track_ID
                mdia = [box for box in trak.children if box.type == b'mdia'][0]
                mdhd = [box for box in mdia.children if box.type == b'mdhd'][0]
                hdlr = [box for box in mdia.children if box.type == b'hdlr'][0]
                stbl = [box for box in [box for box in mdia.children if box.type == b'minf'][0].children
                             if box.type == b'stbl'][0]
                t = mdhd.timescale
                d = mdhd.duration
                v = mdhd.version

                sz = [box for box in stbl.children if box.type == b'stsz' or box.type == b'stz2'][0]
                sc = sz.sample_count
                if sz.sample_size > 0:
                    # uniform sample size
                    trak_size = sz.sample_size * sc
                else:
                    trak_size = sum(sz.entry_sizes)

                sample_rate = None
                if (d < 0xffffffff and v == 0) or (d < 0xffffffffffffffff and v == 1):
                    this_trak['track_duration (secs)'] = round(d / t)
                    if trak_size > 0 and this_trak['track_duration (secs)'] > 0:
                        this_trak['track_bitrate (calculated bps)'] = round(8 * trak_size / this_trak['track_duration (secs)'])
                        sample_rate = round((sc * t) / d, 2)

                codec_info = ([box for box in stbl.children if box.type == b'stsd'][0]).entries[0]
                media = hdlr.handler_type
                if media == 'vide':
                    this_trak['media_type'] = 'video'
                    this_trak['codec_type'] = codec_info.format
                    this_trak['width'] = codec_info.width
                    this_trak['height'] = codec_info.height
                    if sample_rate is not None:
                        this_trak['frame_rate'] = sample_rate
                elif media == 'soun':
                    this_trak['media_type'] = 'audio'
                    this_trak['codec_type'] = codec_info.format
                    this_trak['channel_count'] = codec_info.channels
                    this_trak['sample_rate'] = codec_info.sampling_rate
                    this_trak['compression_id'] = codec_info.compression_id
                else:
                    this_trak['media_type'] = media
                    this_trak['codec_type'] = codec_info.format

                self.data['track_list'].append(this_trak)
        else:
            # no moov found
            self.data['contains_moov'] = False

        if [box for box in boxes if box.type == b'moof']:
            self.data['contains_fragments'] = True



