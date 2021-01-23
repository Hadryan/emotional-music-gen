import mido
from mido import MidiFile, MetaMessage, Message
import os
import glob
import argparse
from pathlib import Path
import re

# argument parser for command line arguments
parser = argparse.ArgumentParser(
    description='Will take a folder of source-separated MIDI files, filter out duplicate/non-essential messages, and save to new files within separate instrument directories. Make sure data is passed through smf_type1.py and instrument_isolate.py first to ensure input set is all SMF Type 1 and source separated. Must have GM_instruments.txt file located in same directory as launch file'
)
parser.add_argument('-i', '--input', required=True,
                    help="Path to input directory. (Required)")
parser.add_argument('-o', '--output', default=os.getcwd(),
                    help="Path to output directory. (Defaults to current working directory if not specified)")
# parse the arguments and store as local variables
args = parser.parse_args()
input_dir = vars(args).get('input')
output_dir = vars(args).get('output')
Path(output_dir).mkdir(parents=True, exist_ok=True)

# import the GM instruments list to populate new folders created
f = open(os.getcwd()+'/GM_instruments.txt', 'r')
to_append = ''
for line in f:
    to_append += line
instruments = to_append.split('\n')


# Function to check validity of MidiFile object.
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


# Function to process source separated MIDI file, by trimming any start and
# end silence, removing nonessential channel and system messages
def clean(filepath):

    # store file as MidiFile obj, create new obj to store output
    mid = MidiFile(filepath)
    ticksperbeat = mid.ticks_per_beat
    newmid = MidiFile(type=1)
    newmid.ticks_per_beat = ticksperbeat

    # in the event that an instrument-isolated file contains multiple tracks of the same instrument,
    # this will ensure that when the start time is trimmed, the timing is all kept correct
    start_times = []
    for track in mid.tracks:
        for msg in track:
            # finds first note_on message time, i.e. starting time
            # for all tracks in file
            if msg.type == 'note_on':
                start_time = msg.time
                start_times.append(start_time)
                break
    start_times.sort()
    if start_times:
        first_start_time = start_times[0]
    # if no start time, file has no note on messages and is invalid
    else:
        pass

    # iterate through tracks in file
    for i, track in enumerate(mid.tracks):
        # new track for cleaned output
        newtrack = mido.MidiTrack()
        # new list to store messages ready for processing
        msglist = [msg for msg in track]

        # each processed file will have one of each: tempo, time signature,
        # key signature and program change messages
        count = 0
        tempocount = 0
        timesigcount = 0
        keysigcount = 0
        progchangecount = 0
        # list of accepted messages to help filter any unwanted ones
        goodmessages = ['note_on', 'note_off', 'program_change',
                        'set_tempo', 'time_signature', 'key_signature']

        # iterate through each message and determine if it will be kept or discarded
        for msg in msglist:
            if msg.type == 'program_change':
                # finds first program change message to store instrument number
                instrument = msg.program
                progchangecount += 1
            # ensures no unwanted messages are appended
            if str(msg.type) not in goodmessages:
                continue
            if msg.type == 'set_tempo':
                # appends one tempo message at time delta of 0 to new track
                if tempocount < 1 and msg.time == 0:
                    newtrack.append(MetaMessage(
                        'set_tempo', tempo=msg.tempo, time=msg.time))
                    tempocount += 1
                else:
                    continue
            if msg.type == 'time_signature':
                # appends one time signature message at time delta of 0 to new track
                if timesigcount < 1 and msg.time == 0:
                    newtrack.append(MetaMessage(
                        'time_signature', numerator=msg.numerator, denominator=msg.denominator, time=msg.time))
                    timesigcount += 1
                else:
                    continue
            if msg.type == 'key_signature':
                # appends one key signature message at time delta of 0 to new track
                if keysigcount < 1 and msg.time == 0:
                    newtrack.append(MetaMessage(
                        'key_signature', key=msg.key, time=msg.time))
                    keysigcount += 1
                else:
                    continue
            # ensures first note on message has time delta of zero,
            # adjusts other potential tracks to equivalent time difference
            if count < 1:
                if msg.type == 'note_on':
                    start_time = msg.time
                    if start_time == first_start_time:
                        trimsilence = re.sub(
                            r'time=(\d+)', r'time=0', str(msg))
                    else:
                        time_diff = 'time=%d' % (start_time - first_start_time)
                        trimsilence = re.sub(
                            r'time=(\d+)', time_diff, str(msg))

                    newtrack.append(mido.parse_string(trimsilence))
                    count += 1
                    continue
            # append all other messages to new track
            if not msg.type == 'set_tempo' and not msg.type == 'time_signature' and not msg.type == 'key_signature':
                newtrack.append(msg)
        # append header track to new MidiFile obj
        if i == 0:
            newmid.tracks.append(newtrack)
            continue
        # append all other valid tracks to new MidiFile obj
        if progchangecount > 0 and i > 0:
            newmid.tracks.append(newtrack)

    # create new directory to store output
    new_dir = output_dir+'/cleaned/'+instruments[instrument]+'/'
    Path(new_dir).mkdir(parents=True, exist_ok=True)
    file_name = os.path.basename(filepath)

    # validates and saves new file
    if is_valid(newmid):
        newmid.save(new_dir+file_name)
    else:
        print('Invalid file not saved: %s' % filepath)


# add all file paths to list, pass each file through clean()
newlist = [str(path) for path in Path(input_dir).rglob('*.mid')]
for file in newlist:
    clean(file)
