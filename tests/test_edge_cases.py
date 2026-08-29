"""Edge-case checks for page retry and resume-by-size logic.

Assert-based, no framework. Run: python tests/test_edge_cases.py
"""
import os
import sys
import shutil
import tempfile

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENGINE_DIR = os.path.join(ROOT_DIR, "engine")
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, ENGINE_DIR)

import main as cbzmain
import cbz as cbzmod


class FakeChapter:
    def __init__(self, url):
        pass
    def getChapterNumber(self):
        return "1"
    def getPageUrls(self):
        return ["p1", "p2"]
    def getChapterLowerName(self):
        return "ch_001"


class FakeCEngine:
    Chapter = FakeChapter


class FakeState:
    def get(self, key):
        return -1
    def set(self, key, value):
        pass


class FakeCBZArchive:
    def __init__(self, chapter_dir):
        pass
    def compile(self, remove_dir=False):
        pass


def setup_globals():
    cbzmain.dlstate = FakeState()
    cbzmain.ch_start = -1
    cbzmain.ch_end = 9000
    cbzmain.step_workers = 2
    cbzmain.page_retries = 2


def test_retry_recovers_from_transient_failure():
    """Page fails once, succeeds on retry -> chapter reports no failures."""
    attempts = {}

    def fake_worker(cengine, page_url, chapter_dir):
        attempts[page_url] = attempts.get(page_url, 0) + 1
        if page_url == "p1" and attempts[page_url] == 1:
            return page_url
        return None

    setup_globals()
    orig_worker, orig_cbz = cbzmain.downloadPageWorker, cbzmod.CBZArchive
    cbzmain.downloadPageWorker = fake_worker
    cbzmod.CBZArchive = FakeCBZArchive
    try:
        failed = cbzmain.downloadChapter(FakeCEngine(), "http://fake/ch1", tempfile.gettempdir())
    finally:
        cbzmain.downloadPageWorker, cbzmod.CBZArchive = orig_worker, orig_cbz

    assert failed == [], "expected retry to recover transient failure, got %r" % (failed,)
    assert attempts["p1"] == 2, "expected exactly one retry for p1"


def test_retry_exhausts_and_reports_failure():
    """Page fails every attempt -> chapter reports it failed once retries exhaust."""
    def fake_worker(cengine, page_url, chapter_dir):
        return page_url

    setup_globals()
    orig_worker = cbzmain.downloadPageWorker
    cbzmain.downloadPageWorker = fake_worker
    try:
        failed = cbzmain.downloadChapter(FakeCEngine(), "http://fake/ch1", tempfile.gettempdir())
    finally:
        cbzmain.downloadPageWorker = orig_worker

    assert set(failed) == {"p1", "p2"}, "expected both pages to stay failed, got %r" % (failed,)


class FakePage:
    def __init__(self, url):
        pass
    def getPageNumber(self):
        return "1"
    def getImageUrl(self):
        return "http://fake/img1.jpg"
    def getImageHeaders(self):
        return {}


class FakeCEnginePage:
    Page = FakePage


def test_resume_skips_nonempty_existing_page():
    """Existing non-empty page file is skipped, no re-fetch."""
    chapter_dir = tempfile.mkdtemp()
    try:
        with open(os.path.join(chapter_dir, "page_0001.jpg"), "wb") as fh:
            fh.write(b"data")

        called = {"fetched": False}

        class FakeWebResource:
            def __init__(self, *a, **k):
                called["fetched"] = True

        orig_web = cbzmain.web
        cbzmain.web = type("web", (), {"WebResource": FakeWebResource})
        try:
            cbzmain.downloadPage(FakeCEnginePage(), "http://fake/p1", chapter_dir)
        finally:
            cbzmain.web = orig_web

        assert called["fetched"] is False, "expected skip, page was re-fetched"
    finally:
        shutil.rmtree(chapter_dir)


def test_resume_refetches_empty_existing_page():
    """Existing empty (0-byte) page file is treated as missing and re-fetched."""
    chapter_dir = tempfile.mkdtemp()
    try:
        open(os.path.join(chapter_dir, "page_0001.jpg"), "wb").close()

        called = {"fetched": False}

        class FakeWebResource:
            def __init__(self, *a, **k):
                called["fetched"] = True
            def getExtension(self):
                return "jpg"
            def saveTo(self, path):
                pass

        orig_web = cbzmain.web
        cbzmain.web = type("web", (), {"WebResource": FakeWebResource})
        try:
            cbzmain.downloadPage(FakeCEnginePage(), "http://fake/p1", chapter_dir)
        finally:
            cbzmain.web = orig_web

        assert called["fetched"] is True, "expected re-fetch of empty page, was skipped"
    finally:
        shutil.rmtree(chapter_dir)


if __name__ == "__main__":
    test_retry_recovers_from_transient_failure()
    test_retry_exhausts_and_reports_failure()
    test_resume_skips_nonempty_existing_page()
    test_resume_refetches_empty_existing_page()
    print("OK")
