import mido
from mido import MidiFile
from pathlib import Path

filepath = '/Users/jamienevin/Desktop/final-samples/words/'
newlist = [str(path) for path in Path(filepath).glob('*.mid')]
for file in newlist:
    mid = MidiFile(file)

    tempo_list = [msg.tempo for msg in mid.tracks[0]
                  if msg.type == 'set_tempo']
    tick_tempo = tempo_list[0]
    tempo = mido.tempo2bpm(tick_tempo)
    key = [msg.key for msg in mid.tracks[0] if msg.type == 'key_signature']
    try:
        key1 = key[0]
    except:
        print('List index out of range: likely no key signature message')

    filesplitter = file.split('/')
    filename = filesplitter[-1]
    newsplitter = filename.split('_')
    # newsplitter[0] = orig filename
    # newsplitter[1] = general midi instrument number
    # newsplitter[2] = instrument name
    # newsplitter[3] = offset
    # newsplitter[4] = wavelength
    orig_filename = newsplitter[0]

    for newfile in newlist:
        newfilesplitter = newfile.split('/')
        newfilename = newfilesplitter[-1]
        doublesplitter = newfilename.split('_')
        new_orig_filename = doublesplitter[0]

        if orig_filename != new_orig_filename:
            mid2 = MidiFile(newfile)
            key = [msg.key for msg in mid2.tracks[0]
                   if msg.type == 'key_signature']
            tempo_list = [msg.tempo for msg in mid.tracks[0]
                          if msg.type == 'set_tempo']
            try:
                key2 = key[0]
                tick_tempo2 = tempo_list[0]
                tempo2 = mido.tempo2bpm(tick_tempo2)
                if key2 == key1 and tempo2 < tempo+1 and tempo2 > tempo-1 and mid2.length > mid.length-1 and mid2.length < mid.length+1:
                    newmid = MidiFile(file)
                    newmid.tracks.append(mid2.tracks[1])
                    newmid.save(
                        '/Users/jamienevin/temp/GOODLOOPS/mashup10/%s_+_%s' % (filename[:-4], newfilename))
            except:
                print('List index out of range: likely no key signature message')
                pass





