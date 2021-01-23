import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage
import glob
from pathlib import Path
import json
import argparse
import os
import re

# argument parser for command line arguments
parser = argparse.ArgumentParser(
    description='Will take a folder of source-separated and cleaned MIDI files, search for repeated messages over a series of wavelengths, and save to new files within separate instrument directories. Make sure data is passed through smf_type1.py, instrument_isolate.py and data_cleanse.py first to ensure input set is all SMF Type 1, source separated and in the correct format. Must have GM_instruments.txt file located in same directory as launch file'
)
parser.add_argument('-i', '--input', required=True,
                    help="Path to input directory. (Required)")
parser.add_argument('-o', '--output', default=os.getcwd(),
                    help="Path to output directory. (Defaults to current working directory if not specified)")
parser.add_argument('-lw', '--lower_wavelength', default=5, type=int,
                    help="Lower boundary of the tile wavelength, i.e. the lowest number of messages that a tile can have. (Defaults to 5 if not specified)")
parser.add_argument('-uw', '--upper_wavelength', default=200, type=int,
                    help="Upper boundary of the tile wavelength, i.e. the highest number of messages that a tile can have. (Defaults to 200 if not specified)")
parser.add_argument('-tl', '--tile_limit', default=None, type=int,
                    help="Upper boundary of number of tiles per file passed. (No limit applied if not specified)")
parser.add_argument('-mt', '--maximum_time', default=30, type=int,
                    help="Upper boundary of the time in seconds that a tile may be. (Defaults to 30 seconds if not specified)")
# parse the arguments and store as local variables
args = parser.parse_args()
input_dir = vars(args).get('input')
output_dir = vars(args).get('output')
lower_wavelength = vars(args).get('lower_wavelength')
upper_wavelength = vars(args).get('upper_wavelength')
tile_limit = vars(args).get('tile_limit')
maximum_time = vars(args).get('maximum_time')

# import the GM instruments list to populate new folders and file names
f = open(os.getcwd()+'/GM_instruments.txt', 'r')
to_append = ''
for line in f:
    to_append += line
instruments = to_append.split('\n')


# returns first program change message of file passed as parameter
def find_program_change(filepath):
    mid = MidiFile(filepath)
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'program_change':
                program_change = msg
                break
    return program_change


# returns tempo of file passed as parameter
def find_tempo(filepath):
    mid = MidiFile(filepath)
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'set_tempo':
                tempo = msg.tempo
                break
    return tempo


# create tiles from file passed by searching for repeated messages
def create_tiles(filepath):

    global tile_limit
    # check to see if tile limit has been set
    if tile_limit is not None:
        single_tile_limit = tile_limit

    # store file as MidiFile obj
    mid = MidiFile(filepath)
    msglist = []

    # append all messages beyond header track to list
    for track in mid.tracks[1:]:
        for msg in track:
            msglist.append(msg)

    # stores accumulated time of each message index
    acc_time_index = {}
    acc_time = 0
    for i in range(0, len(msglist)):
        time = int(re.search(r'time=(\d+)', str(msglist[i])).group(1))
        acc_time += time
        acc_time_index.update({i: acc_time})

    # check each offset of the message list
    for offset in range(0, len(msglist)):
        # check across a range of wavelengths
        for wavelength in range(lower_wavelength, upper_wavelength):
            # validate if the tile repeats
            isvalid = True
            for i in range(wavelength):
                if tile_limit is not None:
                    if single_tile_limit == 0:
                        break
                # ensure values do not exceed list index range
                if offset+i >= len(msglist) or offset+wavelength+i >= len(msglist):
                    isvalid = False
                    break
                if (msglist[offset+i] != msglist[offset+wavelength+i]):
                    isvalid = False
                    break
                # create tile from matching wavelength
                if (isvalid):
                    tile = []
                    for i in range(wavelength):
                        tile.append(msglist[offset+i])

                    # dummy MidiFile created to determine absolute time of tile for metadata
                    temp_mid = mido.MidiFile(type=1)
                    temp_mid.ticks_per_beat = mid.ticks_per_beat
                    track = mido.MidiTrack()
                    if find_program_change(filepath) is not None:
                        prog_change = mido.parse_string(re.sub(
                            r'time=(\d+)', r'time=0', str(find_program_change(filepath))))
                        track.append(prog_change)
                    for line in tile:
                        track.append(line)
                    temp_mid.tracks.append(track)

                    # save tile metadata to json formatted string
                    tick_time = acc_time_index[offset]
                    current_time = mido.tick2second(
                        tick_time, mid.ticks_per_beat, find_tempo(filepath))

                    tile_dict = {
                        'file': filepath,
                        'offset': offset,
                        'wavelength': wavelength,
                        'start_time_seconds': ('%.2f' % current_time),
                        'total_length_seconds': ('%.2f' % temp_mid.length)
                    }
                    meta_dict = json.dumps(tile_dict)

                    # MidiFile to be created as tile
                    new_mid = mido.MidiFile(type=1)
                    new_mid.ticks_per_beat = mid.ticks_per_beat

                    # header track containing same info as original file
                    header_track = mido.MidiTrack()
                    for msg in mid.tracks[0]:
                        if msg.type != 'end_of_track':
                            header_track.append(msg)
                    header_track.append(MetaMessage(
                        'text', text=str(tile_dict), time=0))
                    new_mid.tracks.append(header_track)

                    # music track containing the notes
                    music_track = mido.MidiTrack()
                    # add program change message
                    if find_program_change(filepath) is not None:
                        prog_change = mido.parse_string(re.sub(
                            r'time=(\d+)', r'time=0', str(find_program_change(filepath))))
                        music_track.append(prog_change)
                    # add notes from tile list
                    for line in tile:
                        music_track.append(line)
                    new_mid.tracks.append(music_track)

                    try:
                        # save to new file if tile within valid time range
                        if new_mid.length > 0 and new_mid.length <= maximum_time:
                            file_name = os.path.basename(filepath)
                            instrument = int(
                                re.search(r'program=(\d+)', str(find_program_change(filepath))).group(1))
                            tile_dir = '/tiles/' + \
                                instruments[instrument]+'/'
                            Path(
                                output_dir+tile_dir).mkdir(parents=True, exist_ok=True)

                            new_mid.save(output_dir+tile_dir+'%s_%s_%d_%d.mid' %
                                         (file_name[:-4], instruments[instrument], offset, wavelength))

                            # print info to screen for development
                            """
                            print('\nFile name: %s' % filepath)
                            for i, track in enumerate(new_mid.tracks):
                                print('Track number: %d' % (i+1))
                                for msg in track:
                                    print(msg)
                                print(
                                    '\n____________________________________________________________________________________________________________________________________\n')
                            """

                            try:
                                # save json file
                                json_dir = '/tile_metadata/' + \
                                    instruments[instrument]+'/'
                                Path(
                                    output_dir+json_dir).mkdir(parents=True, exist_ok=True)
                                f = open(output_dir+json_dir+'%s_%s_%d_%d.json' % (
                                    file_name[:-4], instruments[instrument], offset, wavelength), 'w')
                                f.write(meta_dict)
                            except:
                                print('JSON object not created for file: %s\n' %
                                      filepath)
                                for msg in new_mid.tracks[0]:
                                    print(msg)
                                print(
                                    '\n____________________________________________________________________________________________________________________________________\n____________________________________________________________________________________________________________________________________\n\n')

                            # dacrement tile limit for next loop
                            if tile_limit is not None:
                                single_tile_limit -= 1

                    except:
                        print('Error with tile creation for file: %s\nAttempted tile length %d' % (
                            filepath, new_mid.length))
                        for msg in new_mid.tracks[0]:
                            print(msg)
                        print(
                            '\n____________________________________________________________________________________________________________________________________\n____________________________________________________________________________________________________________________________________\n\n')


# add all file paths to list, pass each file through create_tiles()
newlist = [str(path) for path in Path(input_dir).rglob('*.mid')]
for file in newlist:
    create_tiles(file)
