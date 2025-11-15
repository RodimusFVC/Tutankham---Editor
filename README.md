# Tutankham---Editor
GUI Based ROM Editor - written in Python/TK for Portability

--------------------------------------------------------------------------------
INSTRUCTIONS
--------------------------------------------------------------------------------

Python should be installed/working
  - This project was developed with Python 3.13.7
  - Install additional required packages via 'pip install -r requirements.txt'

Must have your own copy of Tutankham game roms (Mame zipped version)
  - The current MAME zipped version should be placed in the folder with the editor
    - Editor looks for the full merged zip
    - Konami Version is loaded by default at startup
    - Zip should contain roms for all 3 variants, if you want to edit other versions
    - The zip is treated as read-only, so you can always revert to your original, unmodified data
  - Modified files will be written in the same folder with the editor, unless otherwise specified
  - To play your newly created maps
    - Place a copy of Mame in the folder with the editor
    - Create a subfolder called 'tutankhm'
    - Extract the mame zip to this 'tutankhm' folder, so the sound roms are also available for use
    - Save your modified roms to this 'tutankhm' folder
    - run mame with some variation of : mame -window tutankhm -rompath .

ALWAYS REMEMBER TO SAVE BEFORE EXITING!!!! Editor only writes files when told to, for safety.

--------------------------------------------------------------------------------
REMAINING TASKS
--------------------------------------------------------------------------------

  - Decode Game Title Graphics / Add to UI Graphics Editor
  - Enforce one Respawn per 'Screen' to avoid weird scrolling issues on death
  - Finish Decoding Stage Reference Data to allow changing of Stage/Difficulty Order
  - Add Editor for Animation / Display Animation Frames (Found, Not Added)
  - Update MemoryMap.txt with new findings
  - Fix Bugs

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
