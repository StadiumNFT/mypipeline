Ageless Pipeline UI (Electron)
--------------------------------
This desktop app runs your Python pipeline with buttons.

Install (first run):
1) Install Node.js LTS from nodejs.org
2) Open a terminal in this folder and run:
   npm install
3) Start the app:
   npm start

Usage:
- Click "Choose Project Root" and select the repo folder that contains `pipeline/`, `Scans_Inbox/`, etc.
- Click "Run Pair" to move *_F/*_B pairs into Scans_Ready/SKU
- Click "Run Queue" to create a batch (the Job ID auto-fills)
- Click "Run Post" to produce JSON/TXT/CSV for that batch

Note:
- The Python CLI must be available as `python` in your PATH.
- The Post step uses the mock model until you wire GPT-5 Batch.
