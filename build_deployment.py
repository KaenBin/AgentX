"""Create an explicitly allowlisted source bundle with a content manifest."""
import argparse
from pathlib import Path
import hashlib
import sys
import tempfile
import zipfile

FOLDERS = ('src', 'tests', 'browser_tests', 'agents', '.github')
EXTENSIONS = {'.py', '.js', '.cjs', '.css', '.html', '.md', '.txt', '.yml', '.yaml'}
FILES = (
    'requirements.txt','requirements-runtime.txt','requirements-runtime.in',
    'requirements-dev.in','requirements-browser.in','requirements-browser.txt',
    'BROWSER-TESTING.md','Dockerfile','compose.yaml','.dockerignore',
    'container_smoke.py','restore_demo.py','DEMO-DEPLOYMENT.md','pytest.ini',
    'start.ps1','.env.example','.gitignore','README.md','DEMO.md','PITCH.md',
    'REHEARSAL.md','DEPLOYMENT.md','build_deployment.py','SOURCE-BUNDLE.md',
    'PILOT-TEST-PLAN.md', 'PILOT-RESULTS-TEMPLATE.md', 'PILOT-ASSESSMENT-A.md',
    'PILOT-ASSESSMENT-B.md', 'PILOT-ASSESSMENT-UPDATE.md', 'PILOT-SCORING-GUIDE.md',
    'PILOT-FACILITATOR-RUN-SHEET.md', 'PILOT-REHEARSAL-RESULTS.md',
    'PRODUCT-DELIVERY-PLAN.md', 'PRODUCTION-RELEASE-CHECKLIST.md',
    'pilot_rehearsal.py', 'pilot-browser-evidence.jpg', 'pilot-session-ready.jpg',
    'backup-demo.gif',
    'DEMO-OPERATIONS.md', 'RELEASES.md',
    'UPGRADE-REHEARSAL.md', 'upgrade_smoke.py',
    'ACCESSIBILITY-REVIEW.md',
    'DEMO-RELEASE-CHECKLIST.md',
    'DEMO-HOSTING-OPTIONS.md',
    'DEMO-CAPACITY.md', 'benchmark_demo.py',
    'DEPENDENCY-MAINTENANCE.md', 'lock_dependencies.py',
    'DEPENDENCY-ADVISORIES.md', 'audit_dependencies.py',
)
ARCHIVE = 'AgentX_Learn_Deployment.zip'
CHECKSUM = 'AgentX_Learn_Deployment.sha256'


def collect_payload(root):
    """Snapshot the source allowlist and reject a configured key before any write."""
    files = [root / name for name in FILES]
    for folder in FOLDERS:
        directory = root / folder
        if not directory.is_dir():
            raise ValueError('Required source directory is missing')
        for path in directory.rglob('*'):
            if (path.is_file() and path.suffix in EXTENSIONS
                    and not any(p in {'__pycache__', '.pytest_cache'} for p in path.relative_to(root).parts)):
                files.append(path)
    payload = {}
    for path in sorted(set(files)):
        # Do not let an allowlisted symlink pull files from outside the source root.
        path.resolve().relative_to(root.resolve())
        payload[path.relative_to(root).as_posix()] = path.read_bytes()
    if any(n.endswith(('.db', '.log', '.pyc')) or n == '.env' for n in payload):
        raise ValueError('Excluded file in payload')
    env_file = root / '.env'
    for line in env_file.read_text(encoding='utf-8').splitlines() if env_file.exists() else []:
        if line.startswith('LLM_GATEWAY_API_KEY='):
            secret = line.split('=', 1)[1].strip().strip('\"\'')
            if secret and any(secret.encode() in data for data in payload.values()):
                raise ValueError('Configured key found in payload')
    manifest = ''.join(f'{hashlib.sha256(data).hexdigest()}  {name}\n'
                       for name, data in sorted(payload.items()))
    payload['MANIFEST.sha256'] = manifest.encode('utf-8')
    return payload


def build_bundle(root, output):
    """Stage, verify, then publish a ZIP and its checksum at the selected location."""
    payload = collect_payload(root)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.bundle-', dir=output) as temporary:
        stage = Path(temporary)
        archive = stage / ARCHIVE
        with zipfile.ZipFile(archive, 'w') as bundle:
            for name, data in sorted(payload.items()):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                bundle.writestr(info, data)
        with zipfile.ZipFile(archive) as bundle:
            if bundle.testzip() is not None or set(bundle.namelist()) != set(payload):
                raise ValueError('Archive integrity check failed')
            for name, data in payload.items():
                if bundle.read(name) != data:
                    raise ValueError('Archive payload mismatch')
        checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
        (stage / CHECKSUM).write_text(checksum + '  ' + ARCHIVE + '\n', encoding='utf-8', newline='\n')
        archive.replace(output / ARCHIVE)
        (stage / CHECKSUM).replace(output / CHECKSUM)
    return len(payload)


def main(argv=None):
    """Build the source bundle without exposing file contents in error diagnostics."""
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=root / 'output/deployment',
                        help='Directory for the verified ZIP and SHA-256 checksum')
    args = parser.parse_args(argv)
    try:
        count = build_bundle(root, args.output_dir)
    except (OSError, ValueError, zipfile.BadZipFile):
        print('Bundle build failed: check required source files, output access and configured-key exclusion.', file=sys.stderr)
        return 1
    print(f'Created {ARCHIVE}: {count} entries; verified archive integrity and configured-key exclusion.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
