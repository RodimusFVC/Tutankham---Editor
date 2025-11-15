# Tutankham---Editor
GUI Based ROM Editor - written in Python/TK for Portability

--------------------------------------------------------------------------------
INSTRUCTIONS
--------------------------------------------------------------------------------
Python should be installed/working (this project was developed with Python 3.13.7)
Install additional required packages (pip install -r requirements.txt)
Must have your own copy of Tutankham game roms (Mame zipped version)
  - Only Konami version of the game is supported for editing
  - The current MAME zipped version should be placed in the folder with the editor
  - Modified files will be written in the same folder with the editor, unless otherwise specified
  - The original zip is treated read-only, so you can always return to your prior version
  - To play your newly created maps
    - Place a copy of Mame in the folder with the editor
    - Create a subfolder called 'tutankhm'
    - Extract the mame zip to this 'tutankhm' folder, so the sound roms are also available for use
    - Save your modified roms to this 'tutankhm' folder
    - run mame with some variation of : mame -window tutankhm -rompath .

--------------------------------------------------------------------------------
CREDITS
--------------------------------------------------------------------------------

Original Game: 
  - Tutankham © 1982 Konami 
  - Licensed to Stern Electronics for US distribution 

ROM Analysis: 
  - MAME project for ROM definitions and memory maps 
  - Arcade hardware documentation community 

Editor Development: 
  - Main development by Rodimus 
  - Primary development in collaboration with Claude (Anthropic) 
  - Additional assistance from Grok (xAI) for copyright checksum implementation
  - Additional assistance from ChatGPT for general code fixes 
  - Python, NumPy, Tkinter, Pillow, Colorlog for implementation 

Special Thanks: 
  - MAME developers for emulation and debugging tools 
  - Arcade game preservation community 
  - Tutankham speedrunning and high-score community
