"""Edge-case checks for catalog scanning (pagination) and new/updated diffing.

Assert-based, no framework, no network. Run: python tests/test_catalog.py
"""
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENGINE_DIR = os.path.join(ROOT_DIR, "engine")
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, ENGINE_DIR)

import ComicEngine


class FakeCatalogModule:
    """ Simulates a 3-page site: pages 1-2 have items, page 3 is empty. """
    __name__ = "FakeCatalogModule"
    recommended_delay = 0

    pages = {
        1: [{'titulo': 'A', 'url': 'http://x/a', 'ultimo_capitulo': '1'}],
        2: [{'titulo': 'B', 'url': 'http://x/b', 'ultimo_capitulo': '2'}],
        3: [],
    }

    @staticmethod
    def listCatalogPage(page):
        return FakeCatalogModule.pages.get(page, [])


def test_scan_stops_at_empty_page():
    """Scan without max_pages stops on its own once a page comes back empty."""
    entries = ComicEngine.scanCatalog(FakeCatalogModule, max_pages=None)
    assert set(entries.keys()) == {'http://x/a', 'http://x/b'}, "expected pages 1-2, got %r" % (entries.keys(),)


def test_scan_respects_max_pages():
    """max_pages cuts the scan short even if more pages would have data."""
    entries = ComicEngine.scanCatalog(FakeCatalogModule, max_pages=1)
    assert set(entries.keys()) == {'http://x/a'}, "expected only page 1, got %r" % (entries.keys(),)


def test_scan_rejects_module_without_catalog_support():
    """A module missing listCatalogPage() fails loudly instead of crashing deep in scanCatalog."""
    class NoCatalogModule:
        __name__ = "NoCatalogModule"

    try:
        ComicEngine.scanCatalog(NoCatalogModule)
        assert False, "expected ComicError"
    except ComicEngine.ComicError:
        pass


def diffCatalog(previous, entries):
    """Mirrors the novo/atualizado logic in main.runCatalog(), without the CLI/IO around it."""
    novos, atualizados = [], []
    for url, item in entries.items():
        prev = previous.get(url)
        if prev is None:
            novos.append(item)
        elif prev.get('ultimo_capitulo') != item.get('ultimo_capitulo'):
            atualizados.append(item)
    return novos, atualizados


def test_diff_flags_new_and_updated_only():
    """Unchanged titles are silent; new titles and chapter changes are reported."""
    previous = {
        'http://x/a': {'titulo': 'A', 'url': 'http://x/a', 'ultimo_capitulo': '1'},
        'http://x/b': {'titulo': 'B', 'url': 'http://x/b', 'ultimo_capitulo': '2'},
    }
    entries = {
        'http://x/a': {'titulo': 'A', 'url': 'http://x/a', 'ultimo_capitulo': '1'},   # unchanged
        'http://x/b': {'titulo': 'B', 'url': 'http://x/b', 'ultimo_capitulo': '3'},   # updated
        'http://x/c': {'titulo': 'C', 'url': 'http://x/c', 'ultimo_capitulo': '1'},   # new
    }

    novos, atualizados = diffCatalog(previous, entries)

    assert [n['titulo'] for n in novos] == ['C'], "expected only C as new, got %r" % (novos,)
    assert [u['titulo'] for u in atualizados] == ['B'], "expected only B as updated, got %r" % (atualizados,)


def test_diff_first_run_treats_everything_as_new():
    """No previous catalog (first run) -> every title is 'novo'."""
    entries = {
        'http://x/a': {'titulo': 'A', 'url': 'http://x/a', 'ultimo_capitulo': '1'},
        'http://x/b': {'titulo': 'B', 'url': 'http://x/b', 'ultimo_capitulo': None},
    }

    novos, atualizados = diffCatalog({}, entries)

    assert len(novos) == 2, "expected both titles as new, got %r" % (novos,)
    assert atualizados == [], "expected no updates on first run, got %r" % (atualizados,)


if __name__ == "__main__":
    test_scan_stops_at_empty_page()
    test_scan_respects_max_pages()
    test_scan_rejects_module_without_catalog_support()
    test_diff_flags_new_and_updated_only()
    test_diff_first_run_treats_everything_as_new()
    print("OK")
