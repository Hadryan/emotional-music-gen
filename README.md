# emotional-music-gen
Research project to assess the viability of applying top-level industry tools to the problem area: creating original audio to scale, that would elicit certain emotional responses in the listener, and could be used as part of a feature soundtrack or background audio. Alternative generative methods were posited to address the problem area.

This repo contains the final algorithms produced to perform the required MIDI manipulation.  

—————————————————————————  
DEPENDENCIES  
—————————————————————————  
Python >= 3.2  
https://github.com/mido/mido  
—————————————————————————  
—————————————————————————  
  
All processing files must be used in the following order  
—————————————————————————  
smf_type1.py  
instrument_isolate.py  
data_cleanse.py  
—————————————————————————  
to prepare for passing through word.py and tile.py  
—————————————————————————  
—————————————————————————  
For detailed descriptions, pass the -h parameter  
in the command line when running each script  
