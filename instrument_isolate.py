import glob
import os
from mido import MidiFile
from pathlib import Path
import argparse

# argument parser for command line arguments
parser = argparse.ArgumentParser(
    description='Will take a folder of MIDI files, isolate instrument parts contained in each file, and save to new files within separate instrument directories. Make sure data is passed through smf_type1.py first to ensure input set is all SMF Type 1. Must have GM_instruments.txt file located in same directory as launch file'
)
parser.add_argument('-i', '--input', required=True,
                    help="Path to input directory. (Required)")
parser.add_argument('-o', '--output', default=os.getcwd(),
                    help="Path to output directory. (Defaults to current working directory if not specified)")
# parse the arguments and store as local variables
args = parser.parse_args()
input_dir = vars(args).get('input')
output_dir = vars(args).get('output')

# import the GM instruments list to populate new folders created
f = open(os.getcwd()+'/GM_instruments.txt', 'r')
to_append = ''
for line in f:
    to_append += line
instruments = to_append.split('\n')


# Checks if a MIDI track is for drums.
# Takes a MidiTrack as an argument, returns true if drums present.
def is_drum(track):
    is_drum = False
    for msg in track:
        if 'channel=9' in str(msg):
            is_drum = True
    return is_drum


# Removes all drum tracks from a passed file.
# Adds all drum tracks to temp list before deleting from file.
# Takes a file path as argument and returns MidiFile object.
def remove_drums(filepath):
    mid = MidiFile(filepath)
    tracks_to_delete = []
    for i, track in enumerate(mid.tracks):
        if is_drum(track):
            tracks_to_delete.append(i)
    for i in sorted(tracks_to_delete, reverse=True):
        del mid.tracks[i]
    return mid


# Checks validity of MidiFile object.
# Takes MidiFile as argument and returns true if more than one
# note_on message is contained, returns false otherwise.
def is_valid(MidiFile):
    mid = MidiFile
    count = 0
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'note_on':
                count += 1
    return True if count > 1 else False


# Identifies all instruments tracks present in passed file,
# and create new files for each single instrument. Takes file path
# as argument and saves new file for each instrument track found.
def isolate_all(filepath):

    # every instrument track has a program number in the range 0-127
    for i in range(0, 128):
        # pass file through remove_drums and store as local MidiFile obj
        mid = remove_drums(filepath)
        # iterate through each track beyond 0th, to search for first
        # program_change number to see if matches current i value
        for track in mid.tracks[1:]:
            for msg in track:
                if msg.type == 'program_change':
                    inst_num = msg.program
                    # if no match, increment i
                    if inst_num != i:
                        break
                    # if match, iterate through MidiFile obj again and remove tracks that do not match
                    else:
                        for track in mid.tracks[1:]:
                            for msg in track:
                                if msg.type == 'program_change':
                                    inst_match = msg.program
                                    if (inst_num != inst_match):
                                        try:
                                            mid.tracks.remove(track)
                                        except:
                                            continue

                                        # create new directory to store new file,
                                        # using matching program number to name folder
                                        new_dir = output_dir + \
                                            '/source_separated/' + \
                                            instruments[i]+'/'
                                        Path(new_dir).mkdir(
                                            parents=True, exist_ok=True)
                                        file_name = os.path.basename(
                                            filepath)

                                        # validate file before saving
                                        if is_valid(mid):
                                            mid.save(new_dir+file_name)
                                        else:
                                            print(
                                                'Invalid file not saved: %s – %s' % (filepath, instruments[i]))


# add all file paths to list, pass each file through isolate_all()
newlist = [str(path) for path in Path(input_dir).rglob('*.mid')]
for file in newlist:
    isolate_all(file)
