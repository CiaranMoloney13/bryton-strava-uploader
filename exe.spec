# -*- mode: python -*-


a = Analysis(['uploader.py'],
             pathex=[],
             hiddenimports=[],
             hookspath=None)

pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          Tree('strava_uploader/images/', 'images'),
          a.datas,
          name=os.path.join('dist', 'BrytonStravaUploader.exe'),
          debug=False,
          strip=None,
          upx=False,
          console=False, icon='strava_uploader\\images\\bryton.ico')
app = BUNDLE(exe,
             name=os.path.join('dist', 'BrytonStravaUploader.exe.app'))

