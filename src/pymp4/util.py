#!/usr/bin/env python
"""
   Copyright 2016-2019 beardypig
   Copyright 2017-2019 truedread

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

from .exceptions import BoxNotFound

log = logging.getLogger(__name__)


class BoxUtil(object):
    @classmethod
    def first(cls, box, type_):
        if hasattr(box, "children"):
            for sbox in box.children:
                try:
                    return cls.first(sbox, type_)
                except BoxNotFound:
                    # ignore the except when the box is not found in sub-boxes
                    pass
        elif box.type == type_:
            return box

        raise BoxNotFound("could not find box of type: {}".format(type_))

    @classmethod
    def index(cls, box, type_):
        if hasattr(box, "children"):
            for i, box in enumerate(box.children):
                if box.type == type_:
                    return i

    @classmethod
    def find(cls, box, type_):
        if box.type == type_:
            yield box
        elif hasattr(box, "children"):
            for sbox in box.children:
                for fbox in cls.find(sbox, type_):
                    yield fbox

    @classmethod
    def find_extended(cls, box, extended_type_):
        if hasattr(box, "extended_type"):
            if box.extended_type == extended_type_:
                yield box
            elif hasattr(box, "children"):
                for sbox in box.children:
                    for fbox in cls.find_extended(sbox, extended_type_):
                        yield fbox
        elif hasattr(box, "children"):
            for sbox in box.children:
                for fbox in cls.find_extended(sbox, extended_type_):
                    yield fbox

    @classmethod
    def find_and_return_first(cls, parent_box, box_type):
        """
        Simple helper for recursive box search.

        Uses BoxUtil.find method to find and return first occurrence.
        Returns None if not found.
        """
        try:
            return [ box for box in BoxUtil.find(parent_box, box_type)][0]
        except IndexError:
            return None


    @classmethod
    def find_samples_progressive(cls, trak_box, moov_box=None):
        """
        Finds samples in case of progressive mp4.
        """
        sample_count = 0
        samples = []


        # edit list and sample table 
        
        elst = BoxUtil.find_and_return_first(trak_box, b"elst")
        mdhd = BoxUtil.find_and_return_first(trak_box, b"mdhd")
        stbl = BoxUtil.find_and_return_first(trak_box, b"stbl")
        
        if(mdhd == None):
            print("error mdhd not found")
            return None

        # in case no moview header default to track header (warning this is not always ok)
        trak_timescale = mdhd["timescale"]
        movie_timescale = mdhd["timescale"]
        
        if moov_box == None: 
            print("error no movie box given, using trak timescale instead of movie timescale")    
        else:
            mvhd = BoxUtil.find_and_return_first(moov_box, b"mvhd")
            if mvhd == None :
                print("error moviebox does not contain movieheaderbox")
                return None
            else:
                movie_timescale = mvhd["timescale"]
            

        if stbl != None:
            # children of sample table
            stts = BoxUtil.find_and_return_first(stbl, b"stts")
            ctts = BoxUtil.find_and_return_first(stbl, b"ctts")
            stsz = BoxUtil.find_and_return_first(stbl, b"stsz")
            stsc = BoxUtil.find_and_return_first(stbl, b"stsc")
            stco = BoxUtil.find_and_return_first(stbl, b"stco")
            st64 = BoxUtil.find_and_return_first(stbl, b"co64")
            
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
                
                for k in range(len(samples)):
                    if "composition_time" in samples[k]:
                        sample[k]["presentation_time"] = samples[k]["composition_time"] + edit_offset * trak_timescale / movie_timescale
                    else:
                        samples[k]["presentation_time"] = samples[k]["decode_time"] + edit_offset * trak_timescale / movie_timescale

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

    @classmethod
    def find_samples_fragmented(cls, movie_box, movie_fragment_box, supress_flags=False):
        """
        Finds sample times and offsets in case of fragmented/segmented mp4
                        limitations 
                edit list only 1 or 2 entries
            single traf box only per movie fragment
                only default base is moof
        """
        if movie_fragment_box == None: 
            print("no movie fragment box given")
            return None

        if movie_box == None: 
            print("error no movie box given")
            return None
        
        mvhd = BoxUtil.find_and_return_first(movie_box, b"mvhd")
        if mvhd == None :
            print("error moviebox does not containe movieheaderbox")
            return

        movie_fragment_size = movie_fragment_box["end"] - movie_fragment_box["offset"]
        movie_timescale = mvhd["timescale"]

        ## find trak and trex
        mvex = BoxUtil.find_and_return_first(movie_box, b"mvex")  
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

            mdhd = BoxUtil.find_and_return_first(trak, b"mdhd")
            tkhd = BoxUtil.find_and_return_first(trak, b"tkhd")
            elst = BoxUtil.find_and_return_first(trak, b"elst")
            
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
                            (elst["entries"][0]["edit_duration"] - elst["entries"][1]["media_time"]) 
            
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
            tfhd = BoxUtil.find_and_return_first(traf_boxes[0], b"tfhd")
            
            if(tfhd == None):
                print("error no track fragment header ")
                return None

            tfdt = BoxUtil.find_and_return_first(traf_boxes[0], b"tfdt")
            
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
            trun = BoxUtil.find_and_return_first(traf_boxes[0], b"trun")

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