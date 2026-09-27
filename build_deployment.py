"""Create an explicitly allowlisted source bundle with a content manifest."""
from pathlib import Path
import hashlib
import zipfile

root = Path(__file__).resolve().parent
out = root / 'output' / 'deployment'
out.mkdir(parents=True, exist_ok=True)
files = []
for folder in ['src', 'tests', 'agents', '.github']:
    for path in (root / folder).rglob('*'):
        if path.is_file() and not any(p in {'__pycache__','.pytest_cache'} for p in path.parts) and path.suffix in {'.py','.js','.cjs','.css','.html','.md','.txt','.yml','.yaml'}:
            files.append(path)
for name in ['requirements.txt','pytest.ini','start.ps1','.env.example','.gitignore','README.md','DEMO.md','PITCH.md','REHEARSAL.md','DEPLOYMENT.md']:
    files.append(root/name)
payload = {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(set(files))}
assert not any(n.endswith(('.db','.log','.pyc')) or n == '.env' for n in payload)
for line in (root/'.env').read_text(encoding='utf-8').splitlines() if (root/'.env').exists() else []:
    if line.startswith('LLM_GATEWAY_API_KEY='):
        secret = line.split('=',1)[1].strip().strip('\"\'')
        if secret:
            assert all(secret.encode() not in data for data in payload.values()), 'Configured key found in payload'
manifest = '\n'.join(f'{hashlib.sha256(data).hexdigest()}  {name}' for name,data in sorted(payload.items()))+'\n'
payload['MANIFEST.sha256'] = manifest.encode()
archive = out/'AgentX_Learn_Deployment.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as bundle:
    for name,data in payload.items(): bundle.writestr(name,data)
with zipfile.ZipFile(archive) as bundle:
    assert bundle.testzip() is None
    assert set(bundle.namelist()) == set(payload)
checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
(out/'AgentX_Learn_Deployment.sha256').write_text(checksum+'  '+archive.name+'\n')
print(f'Created {archive.name}: {len(payload)} entries; verified archive integrity and configured-key exclusion.')
