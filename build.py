import PyInstaller.__main__

PyInstaller.__main__.run([
    'src/gui.py',
    '--name=AgentCBR',
    '--onefile',
    '--windowed',
    '--add-data=config;config',
    '--hidden-import=selenium',
    '--hidden-import=PIL',
    '--hidden-import=pytesseract',
    '--hidden-import=PyPDF2',
    '--hidden-import=docx',
    '--hidden-import=openpyxl',
    '--icon=NONE',
])
