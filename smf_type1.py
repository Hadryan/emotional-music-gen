import mido
import os
import glob
from mido import MidiFile
import shutil
import argparse
from pathlib import Path

# argument parser for command line arguments
parser = argparse.ArgumentParser(
    description='Will take a folder of MIDI files, filter those of Type 1 SMF, and copy to a new directory. '
)
parser.add_argument('-i', '--input', required=True,
                    help="Path to input directory. (Required)")
parser.add_argument('-o', '--output', default=os.getcwd(),
                    help="Path to output directory. (Defaults to current working directory if not specified)")
# parse the arguments and store as local variables
args = parser.parse_args()
input_dir = vars(args).get('input')
output_dir = vars(args).get('output')
new_dir = output_dir+'/type_1/'
Path(new_dir).mkdir(parents=True, exist_ok=True)


# filters type 1 SMF files
def is_type1(filepath):
    mid = MidiFile(filepath)
    return True if mid.type == 1 else False


# add all file paths to list, pass each through is_type1()
smf1 = [str(path) for path in Path(input_dir).glob('*.mid')]
for file in smf1:
    try:
        if is_type1(file):
            shutil.copy2(file, new_dir)
    except:
        pass
