"""Regression tests for selecting official course kit archive metadata."""

import importlib.util
from pathlib import Path


SPEC = importlib.util.spec_from_file_location(
    'prepare_pr04_report', Path(__file__).with_name('prepare_pr04_report.py'))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
SHA = 'a' * 64
PINNED = '/downloads/robotics-course-kit-v1-w04-' + SHA[:12] + '.tar.gz'
HOST = 'https://ros.lms.ci.nsu.ru'


def test_selects_pinned_archive_and_ignores_checksum_links():
    metadata = {
        'sha256': SHA,
        'download_url': '/downloads/robotics-course-kit-v1.tar.gz',
        'immutable_download_url': PINNED,
        'sha256_url': PINNED + '.sha256.txt',
    }
    assert MODULE.find_archive(metadata) == (HOST + PINNED, SHA)


def test_duplicate_archive_urls_are_one_candidate():
    metadata = {'sha256': SHA, 'url': PINNED, 'archive_url': HOST + PINNED}
    assert MODULE.find_archive(metadata) == (HOST + PINNED, SHA)


def test_nested_sibling_fields_share_the_single_archive_digest():
    metadata = {'checksums': {'archive': SHA}, 'download': {'url': PINNED}}
    assert MODULE.find_archive(metadata) == (HOST + PINNED, SHA)


def test_single_archive_is_supported():
    metadata = {'archive': {'sha256': SHA, 'url': PINNED}}
    assert MODULE.find_archive(metadata) == (HOST + PINNED, SHA)


def test_ambiguous_releases_are_not_selected():
    metadata = [
        {'sha256': SHA, 'url': PINNED},
        {'sha256': 'b' * 64, 'url': '/downloads/other.tar.gz'},
    ]
    assert MODULE.find_archive(metadata) is None


def test_external_urls_and_checksum_files_are_not_archives():
    metadata = {'sha256': SHA, 'url': 'https://example.com/kit.tar.gz',
                'checksum_url': PINNED + '.sha256.txt'}
    assert MODULE.find_archive(metadata) is None
