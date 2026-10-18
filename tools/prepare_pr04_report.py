#!/usr/bin/env python3
"""Install an official course kit and prepare a report for PR04."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
from urllib.parse import urljoin, urlparse
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / '.course-kit'
API = 'https://ros.lms.ci.nsu.ru/api/course-kit'


def download(url):
    """Read course metadata or an archive with a bounded timeout."""
    with urlopen(url, timeout=20) as response:
        return response.read()


def official_url(url):
    """Accept HTTPS links hosted on the course website."""
    parsed = urlparse(url)
    return (parsed.scheme == 'https'
            and parsed.netloc == 'ros.lms.ci.nsu.ru'
            and not any(char in url for char in '\r\n'))


def find_archive(metadata):
    """Read an archive URL and SHA256 from the official API metadata."""
    if isinstance(metadata, dict):
        hashes = [value for value in metadata.values()
                  if isinstance(value, str)
                  and re.fullmatch('[0-9a-fA-F]{64}', value)]
        urls = [urljoin(API, value) for value in metadata.values()
                if isinstance(value, str) and '.tar.gz' in value
                and official_url(urljoin(API, value))]
        if len(hashes) == 1 and len(urls) == 1:
            return urls[0], hashes[0].lower()
        for value in metadata.values():
            found = find_archive(value)
            if found:
                return found
    elif isinstance(metadata, list):
        for value in metadata:
            found = find_archive(value)
            if found:
                return found
    return None


def install_archive(data, url, digest):
    """Verify archive and file hashes before installing its v1 directory."""
    actual = hashlib.sha256(data).hexdigest()
    if actual != digest:
        raise ValueError('Archive SHA256 differs from the official value')
    KIT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='pr04-kit-') as directory:
        temporary = Path(directory)
        archive = temporary / 'kit.tar.gz'
        archive.write_bytes(data)
        with tarfile.open(archive) as bundle:
            bundle.extractall(temporary / 'extracted', filter='data')
        candidates = list((temporary / 'extracted').rglob('VERSION'))
        candidates = [path.parent for path in candidates
                      if (path.parent / 'practices/manifests/pr04.json').is_file()]
        if len(candidates) != 1:
            raise ValueError('Archive does not contain one official PR04 kit')
        source = candidates[0]
        for line in (source / 'MANIFEST.sha256').read_text().splitlines():
            expected, separator, relative = line.partition('  ')
            item = (source / relative).resolve()
            if not separator or source.resolve() not in item.parents:
                raise ValueError('Invalid course kit file manifest')
            if hashlib.sha256(item.read_bytes()).hexdigest() != expected:
                raise ValueError('Course kit file checksum mismatch: ' + relative)
        manifest = json.loads(
            (source / 'practices/manifests/pr04.json').read_text())
        if manifest['id'] != 'PR04':
            raise ValueError('Incorrect practice manifest')
        shutil.copytree(source, KIT / 'v1', dirs_exist_ok=True)
        metadata = {
            'version': (source / 'VERSION').read_text().strip(),
            'archive_sha256': digest,
            'archive_url': url,
        }
    (KIT / 'pr04-source.json').write_text(json.dumps(metadata, indent=2))
    (KIT / 'pr04-course-kit.tar.gz').write_bytes(data)
    return metadata


def main():
    """Prepare evidence only after the implementation commit exists."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--url')
    parser.add_argument('--sha256')
    args = parser.parse_args()
    pending = []
    for command in [
        ['git', 'diff', '--name-only'],
        ['git', 'diff', '--cached', '--name-only'],
        ['git', 'ls-files', '--others', '--exclude-standard'],
    ]:
        pending.extend(subprocess.check_output(command, cwd=ROOT, text=True).splitlines())
    unexpected = [path for path in pending
                  if path != 'AI_USAGE.md' and not path.startswith('evidence/pr04/')]
    if unexpected:
        raise SystemExit('Commit implementation files first: ' + ', '.join(unexpected))
    cache = KIT / 'pr04-source.json'
    if args.archive:
        if not args.url or not official_url(args.url):
            raise SystemExit('--url must be the official archive URL')
        if not args.sha256 or not re.fullmatch('[0-9a-f]{64}', args.sha256):
            raise SystemExit('--sha256 must be the official archive SHA256')
        metadata = install_archive(args.archive.read_bytes(), args.url, args.sha256)
    elif cache.is_file() and (KIT / 'v1/practices/manifests/pr04.json').is_file():
        metadata = json.loads(cache.read_text())
        if metadata['version'] != (KIT / 'v1/VERSION').read_text().strip():
            raise SystemExit('Cached metadata and installed course kit differ')
    else:
        try:
            found = find_archive(json.loads(download(API)))
            if not found:
                raise ValueError('API metadata has no unambiguous archive URL/SHA256; use --archive, --url and --sha256')
            url, digest = found
            metadata = install_archive(download(url), url, digest)
        except Exception as error:
            raise SystemExit('Official course kit could not be installed. Report left unchanged. ' + str(error))
    path = ROOT / 'evidence/pr04/report.json'
    report = json.loads(path.read_text())
    report['commit'] = subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    report['course_kit'] = metadata
    report.pop('notes', None)
    report['tests'] = [test for test in report['tests']
                       if test['name'] != 'Official PR04 evidence contract']
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    result = subprocess.run(
        ['python3', str(KIT / 'v1/tools/check_practice.py'), 'PR04', '--submission', str(ROOT)],
        cwd=ROOT,
    )
    if result.returncode:
        raise SystemExit(result.returncode)
    report['tests'].append({'name': 'Official PR04 evidence contract', 'status': 'passed'})
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('Official kit installed, report prepared and PR04 contract passed.')


if __name__ == '__main__':
    main()
