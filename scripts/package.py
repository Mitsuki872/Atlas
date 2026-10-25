"""Create a source-only release; never include user data, credentials or caches."""
from pathlib import Path
import hashlib
import zipfile
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'dist'
INCLUDE=['app','migrations','scripts','tests','docs']
ROOT_FILES=['.gitignore','README.md','INSTALLATION_WINDOWS.md','USER_GUIDE.md','ARCHITECTURE.md','CONNECTORS.md','SECURITY.md','TEST_REPORT.md','KNOWN_LIMITATIONS.md','CHANGELOG.md','PATCH_V1_1.md','PATCH_V1_1_1.md','PATCH_V1_1_2.md','LOCAL_OSM_GUIDE.md','SCORING_V1_3.md','PATCH_V1_3_1.md','requirements.in','requirements.txt','package.json','package-lock.json','pytest.ini','alembic.ini','Installer.ps1','Install.bat','Start.bat','Stop.bat','Diagnose.bat','Backup.bat','Restore.bat','Uninstall.bat']
def main():
    DEST.mkdir(exist_ok=True)
    archive=DEST/'ProspectEngine-1.3.1-source.zip'
    paths=[ROOT/name for name in ROOT_FILES]
    for folder in INCLUDE:
        paths.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.log'))
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(paths):z.write(p,'ProspectEngine/'+p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert not any('/data/' in n or '/.venv/' in n or '/node_modules/' in n or '/.git/' in n or n.endswith('.env') for n in z.namelist())
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    (DEST/(archive.name+'.sha256')).write_text(digest+'  '+archive.name+'\n')
    print(archive,archive.stat().st_size,'bytes',digest)
if __name__=='__main__':main()
