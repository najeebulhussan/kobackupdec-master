import PyInstaller.__main__
import tkinterdnd2
import os
import shutil

def build():
    tkdnd_path = os.path.join(os.path.dirname(tkinterdnd2.__file__), 'tkdnd')
    
    # Ensure dist and build dirs are clean
    if os.path.exists('dist'): shutil.rmtree('dist')
    if os.path.exists('build'): shutil.rmtree('build')

    PyInstaller.__main__.run([
        'kobackupdec_gui.py',
        '--name=KoBackupDecryptor',
        '--onefile',
        '--windowed',
        '--icon=app.ico',
        f'--add-data={tkdnd_path};tkinterdnd2/tkdnd'
    ])

if __name__ == '__main__':
    build()
