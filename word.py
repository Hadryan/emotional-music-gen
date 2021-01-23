import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage
import glob
import re
from pathlib import Path
import json
import argparse
import os

# argument parser for command line arguments
parser = argparse.ArgumentParser(
    description='Will take a folder of source-separated and cleaned MIDI files, search for passages of music surrounded by silence, and save to new files within separate instrument directories. Make sure data is passed through smf_type1.py, instrument_isolate.py and data_cleanse.py first to ensure input set is all SMF Type 1, source separated and in the correct format. Must have GM_instruments.txt file located in same directory as launch file'
)
# add parameters you want to parse (positional / optional)
parser.add_argument('-i', '--input', required=True,
                    help="Path to input directory. (Required)")
parser.add_argument('-o', '--output', default=os.getcwd(),
                    help="Path to output directory. (Defaults to current working directory if not specified)")
parser.add_argument('-ms', '--minimum_silence', default=0.5, type=float,
                    help="Value in seconds of the silence gap significant enough to determine a word. (Defaults to 0.5 seconds if not specified)")
parser.add_argument('-wl', '--word_limit', default=None, type=int,
                    help="Upper boundary of number of words per file passed. (No limit applied if not specified)")
parser.add_argument('-mt', '--maximum_time', default=10, type=int,
                    help="Upper boundary of the time in seconds that a word may be. (Defaults to 10 seconds if not specified)")
# parse the arguments and store as local variables
args = parser.parse_args()
input_dir = vars(args).get('input')
output_dir = vars(args).get('output')
minimum_silence = vars(args).get('minimum_silence')
word_limit = vars(args).get('word_limit')
maximum_time = vars(args).get('maximum_time')

# import the GM instruments list to populate new folders and file names
f = open(os.getcwd()+'/GM_instruments.txt', 'r')
to_append = ''
for line in f:
    to_append += line
instruments = to_append.split('\n')


# check if track contains any note on messages
# takes MidiTrack as parameter and returns boolean
def has_note_on(track):
    has_note_on = False
    for msg in track:
        if msg.type == 'note_on':
            has_note_on = True
    return has_note_on


# returns tempo of file passed as parameter
def find_tempo(filepath):
    mid = MidiFile(filepath)
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'set_tempo':
                tempo = msg.tempo
                break
    return tempo


# returns channel number of file passed as parameter
def find_channel(filepath):
    mid = MidiFile(filepath)
    for track in mid.tracks:
        for msg in track:
            if 'channel=' in str(msg):
                channel = int(re.search(r'channel=(\d+)', str(msg)).group(1))
                break
    return channel


# returns first program change number of file passed as parameter
def find_program_change(filepath):
    program_change = ''
    mid = MidiFile(filepath)
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'program_change':
                program_change = msg
                break
    return program_change


# create words from file passed by finding notes surrounded by silence
def create_words(filepath):

    global word_limit
    # check to see if word limit has been set
    if word_limit is not None:
        single_word_limit = word_limit

    # store file as MidiFile obj
    mid = MidiFile(filepath)
    note_on_list = []

    # new list of relevant messages
    for track in mid.tracks:
        if has_note_on(track):
            for msg in track:
                if msg.type == 'note_on' or msg.type == 'note_off':
                    note_on_list.append(str(msg))

    # to store accumulated time of message index
    acc_time = 0
    acc_time_seconds = 0

    # dictionary with each possible note stored,
    # to see what notes are on/off at any given offset
    note_dict = {}
    for i in range(0, 128):
        note_dict.update({i: {'on': False}})

    # temporary list to store annotated messages
    note_on_new = []

    for i in range(0, len(note_on_list)):
        # capture note number, velocity & time, note number in dictionary
        note = int(re.search(r'note=(\d+)', note_on_list[i]).group(1))
        velocity = int(re.search(r'velocity=(\d+)', note_on_list[i]).group(1))
        time = int(re.search(r'time=(\d+)', note_on_list[i]).group(1))
        note_info = note_dict[note]
        try:
            # find time delta of next message in index
            next_note_time = int(
                re.search(r'time=(\d+)', note_on_list[i+1]).group(1))
        except:
            pass
        if i > 0:
            # find time delta of previous message in index
            previous_note = int(
                re.search(r'note=(\d+)', note_on_list[i-1]).group(1))
        else:
            previous_note = note

        # increment accumulated time at offset, find time of note at offset and next offset
        acc_time += time
        note_time_seconds = mido.tick2second(
            time, mid.ticks_per_beat, find_tempo(filepath))
        next_note_time_seconds = mido.tick2second(
            next_note_time, mid.ticks_per_beat, find_tempo(filepath))
        acc_time_seconds = mido.tick2second(
            acc_time, mid.ticks_per_beat, find_tempo(filepath))

        # update dictionary with note status
        # if on, write to note_on_new with '-1'
        if 'note_on' in note_on_list[i] and velocity > 0:
            note_info['on'] = True
            note_on_new.append(note_on_list[i]+' - 1')

        # if off, find out if there will be silence
        elif 'note_off' in note_on_list[i] or velocity == 0:
            note_info['on'] = False
            notes_on = []

            # find out how many notes are on at this offset
            for j in note_dict:
                if note_dict[j]['on'] == True:
                    notes_on.append(note_dict[j])

            if len(notes_on) == 0:
                # find length of silence if all notes off
                silence_start = acc_time_seconds - note_time_seconds
                next_note_start = acc_time_seconds + next_note_time_seconds
                silence_length = next_note_start - silence_start
                # append '-0' to new list if silence above minimum threshold
                if silence_length > minimum_silence:
                    note_on_new.append(note_on_list[i]+' - 0')
                else:
                    note_on_new.append(note_on_list[i]+' - 1')
            else:
                note_on_new.append(note_on_list[i]+' - 1')

    # store accumulated time of each message index
    acc_time_index = {}
    acc_time = 0
    for i in range(0, len(note_on_list)):
        time = int(re.search(r'time=(\d+)', str(note_on_list[i])).group(1))
        acc_time += time
        acc_time_index.update({i: acc_time})

    for i in range(0, len(note_on_new)):
        # check if word limit is exceeded here
        if word_limit is not None and single_word_limit == 0:
            break

        previous_msg = note_on_new[i-1]
        if int(previous_msg[-1]) == 0:
            # note ended with silence
            silence_time = int(
                re.search(r'time=(\d+)', note_on_new[i]).group(1))
            silence_time_sec = mido.tick2second(
                silence_time, mid.ticks_per_beat, find_tempo(filepath))
            if silence_time_sec > minimum_silence:
                # create word if silence above threshold
                word = []
                # set first note_on time attribute to 0 to trim any start silence
                count = 0
                for j in range(i, len(note_on_new)):
                    if count == 0:
                        word_lines = re.sub(
                            r'time=(\d+)', r'time=0', note_on_new[j])
                        count += 1
                    else:
                        word_lines = note_on_new[j]

                    # remaining messages appended with '-1' or '-0' removed
                    if int(word_lines[-1]) == 1:
                        word.append(word_lines[:-4])
                    if int(word_lines[-1]) == 0:
                        word.append(word_lines[:-4])
                        break

                # dummy mid created to determine absolute time of word for metadata
                temp_mid = mido.MidiFile(type=1)
                temp_mid.ticks_per_beat = mid.ticks_per_beat
                track = mido.MidiTrack()
                if find_program_change(filepath) is not None:
                    prog_change = mido.parse_string(re.sub(
                        r'time=(\d+)', r'time=0', str(find_program_change(file))))
                    track.append(prog_change)
                for line in word:
                    track.append(mido.parse_string(line))
                temp_mid.tracks.append(track)

                # save word metadata to json formatted string
                tick_time = acc_time_index[i]
                current_time = mido.tick2second(
                    tick_time, mid.ticks_per_beat, find_tempo(filepath))

                word_dict = {
                    'file': filepath,
                    'offset': i,
                    'wavelength': len(word),
                    'start_time_seconds': ('%.2f' % current_time),
                    'total_length_seconds': ('%.2f' % temp_mid.length)
                }
                meta_dict = json.dumps(word_dict)

                # MidiFile to be created as tile
                new_mid = mido.MidiFile(type=1)
                new_mid.ticks_per_beat = mid.ticks_per_beat

                # header track containing same info as original file
                header_track = mido.MidiTrack()
                for msg in mid.tracks[0]:
                    header_track.append(msg)
                header_track.append(MetaMessage(
                    'text', text=str(word_dict), time=0))
                new_mid.tracks.append(header_track)

                # music track containing the notes
                music_track = mido.MidiTrack()
                # add program change message
                if find_program_change(filepath) is not None:
                    prog_change = mido.parse_string(re.sub(
                        r'time=(\d+)', r'time=0', str(find_program_change(filepath))))
                    music_track.append(prog_change)
                # add notes from word list
                for line in word:
                    music_track.append(mido.parse_string(line))
                new_mid.tracks.append(music_track)

                try:
                    # save to new file if word within valid time range
                    if new_mid.length > 0 and new_mid.length <= maximum_time:
                        file_name = os.path.basename(filepath)
                        instrument = int(
                            re.search(r'program=(\d+)', str(find_program_change(filepath))).group(1))
                        word_dir = '/words/'+instruments[instrument]+'/'
                        Path(output_dir+word_dir).mkdir(parents=True, exist_ok=True)

                        new_mid.save(output_dir+word_dir+'%s_%s_%d_%d.mid' %
                                     (file_name[:-4], instruments[instrument], i, len(word)))

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
                            json_dir = '/word_metadata/' + \
                                instruments[instrument]+'/'
                            Path(
                                output_dir+json_dir).mkdir(parents=True, exist_ok=True)
                            f = open(output_dir+json_dir+'%s_%s_%d_%d.json' % (
                                file_name[:-4], instruments[instrument], i, len(word)), 'w')
                            f.write(meta_dict)
                        except:
                            print('JSON object not created for file: %s\n' %
                                  filepath)
                            for msg in new_mid.tracks[0]:
                                print(msg)
                            print(
                                '\n____________________________________________________________________________________________________________________________________\n____________________________________________________________________________________________________________________________________\n\n')

                        # dacrement word limit for next loop
                        if word_limit is not None:
                            single_word_limit -= 1

                except:
                    print('Error with word creation for file: %s\nAttempted tile length %d' % (
                        filepath, new_mid.length))
                    for msg in new_mid.tracks[0]:
                        print(msg)
                    print(
                        '\n____________________________________________________________________________________________________________________________________\n____________________________________________________________________________________________________________________________________\n\n')


# add all file paths to list, pass each file through create_words()
newlist = [str(path) for path in Path(input_dir).rglob('*.mid')]
for file in newlist:
    create_words(file)
