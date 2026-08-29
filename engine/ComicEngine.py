import importlib
import time
import web
import feedback

import modules.moduleslist

""" Module to determine which module to use, given a URL
"""

def getAvailableEngineFiles():
    "Get the list of module files"
    return modules.moduleslist.engine_files

def getAvailableModuleNames():
    "Get the list of plain module names"
    return modules.moduleslist.module_names
    

class ComicError(Exception):
    "Standard cbzdl error"

    def __init__(self, message):
        Exception.__init__(self, message)

def determineFromName(module_name):
    """ Return a download module given its plain name (e.g. "MangaFox")
    """
    if module_name not in getAvailableModuleNames():
        raise ComicError("Unknown module: %s" % module_name)

    return importlib.import_module("modules.%s" % module_name)

def scanCatalog(cengine, max_pages=None, delay=None):
    """ Iterates a module's listing pages via listCatalogPage(), page by page.

    Stops at the first empty page, or at max_pages if given. Respects
    the module's recommended_delay (or the given delay) between pages.

    Returns {url: {titulo, url, ultimo_capitulo}} keyed by comic URL, so
    a title appearing more than once across pages collapses into one entry.
    """
    if not hasattr(cengine, "listCatalogPage"):
        raise ComicError("%s does not support catalog scanning" % cengine.__name__)

    if delay is None:
        delay = getattr(cengine, "recommended_delay", 1)

    entries = {}
    page = 1
    while max_pages is None or page <= max_pages:
        items = cengine.listCatalogPage(page)
        if not items:
            break

        for item in items:
            entries[item['url']] = item

        feedback.info("  Page %i: %i title(s)" % (page, len(items) ) )

        page += 1
        if max_pages is None or page <= max_pages:
            time.sleep(delay)

    return entries

def determineFrom(comic_url):
    """ Return a download module determined by the URL
    """

    scheme, domain, path = web.getUrlComponents(comic_url)

    if domain == None:
        ComicError("Invalid URL")

    for engine_file in getAvailableEngineFiles():
        cengine = importlib.import_module(engine_file)
        if domain in cengine.valid_domains:
            return cengine

    raise ComicError("Unknown handler for %s"%domain)
