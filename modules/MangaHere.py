""" MangaHere (mangahere.cc)

The site serves its image URLs from an AJAX endpoint, two pages at a time,
as packed javascript - see Chapter.getImageBatch()
"""

import web
import re
import time
import base64
import feedback
import ComicEngine
import util

# Edit this to list the valid domains for the site
valid_domains = ['www.mangahere.cc', 'mangahere.cc', 'www.mangahere.co', 'mangahere.co']
recommended_delay = 1

site_url = "https://www.mangahere.cc"

class ComicSite(web.WebResource):

    def __init__(self, url):
        url = self.validateUrl(url)

        web.WebResource.__init__(self, url)
        self.domain = web.getUrlComponents(url, 2)
        # some titles sit behind an age check
        self.extra_headers['Cookie'] = "isAdult=1"

    def validateUrl(self, url):
        """ If you want to rewrite the URL before accessing it, modify this section
        """
        url = re.sub("^http://", "https://", url)
        return re.sub("^https://(www\\.)?mangahere\\.(cc|co)/", "%s/" % site_url, url)

    def getImageHeaders(self):
        # the image CDN answers 403 to referer-less requests
        return {'Referer': "%s/" % site_url}

class Comic(ComicSite):

    def __init__(self, url):
        ComicSite.__init__(self, url)
        self.url = re.sub("(/manga/[^/]+)/.*", "\\1/", self.url)

    def getComicLowerName(self):
        return util.regexGroup(".+/manga/([^/]+)", self.url)

    def getChapterUrls(self):
        doc = self.getDomObject()
        # links are site-relative, and each one points at the first page of its chapter
        chapter_pattern = "^(?:https?://[^/]+)?(/manga/%s/c[0-9.]+)/[0-9]+\\.html" % re.escape(self.getComicLowerName() )

        urls = []

        for elem_a in doc.cssselect("a"):
            matched = re.match(chapter_pattern, elem_a.attrib.get('href', "") )

            if matched and "%s%s" % (site_url, matched.group(1) ) not in urls:
                urls.append("%s%s" % (site_url, matched.group(1) ) )

        util.naturalSort(urls, ".+/c([0-9.]+)$")

        return urls

class Chapter(ComicSite):

    def __init__(self, url):
        url = re.sub("/[0-9]+\\.html$", "", url)
        url = re.sub("/$", "", url)

        ComicSite.__init__(self, url)

    def getChapterNumber(self):
        # half chapters (c021.5) exist, so this stays a string for the caller to cast
        return util.regexGroup(".+/c([0-9.]+)$", self.url)

    def getChapterLowerName(self):
        parts = re.match(".+/manga/([^/]+)/c([0-9.]+)$", self.url)
        return "%s_c%s" % (parts.group(1), util.padChapterNumber(parts.group(2) ) )

    def getImageBatch(self, chapter_id, page):
        """ Ask the AJAX endpoint for the images of a page

        Answers with packed javascript declaring a host prefix (pix) and the
        paths of that page and the next one (pvalue). Returns the full URLs.
        """
        endpoint = "%s/chapterfun.ashx?cid=%s&page=%i" % (site_url, chapter_id, page)
        resource = web.WebResource(endpoint, headers={
            'Referer'          : "%s/1.html" % self.url,
            'X-Requested-With' : "XMLHttpRequest",
            'Cookie'           : "isAdult=1"
            })

        unpacked = util.unpackJs(resource.getSource() )

        if unpacked == None:
            return []

        prefix = re.search('pix\\s*=\\s*"([^"]*)"', unpacked)
        values = re.search('pvalue\\s*=\\s*\\[(.*?)\\]', unpacked)

        if prefix == None or values == None:
            return []

        return [ re.sub("^//", "https://", prefix.group(1) + path) for path in re.findall('"([^"]+)"', values.group(1) ) ]

    def getPageUrls(self):
        source = web.WebResource("%s/1.html" % self.url, headers={'Cookie': "isAdult=1"}).getSource()

        chapter_id  = re.search("chapterid\\s*=\\s*([0-9]+)", source)
        image_count = re.search("imagecount\\s*=\\s*([0-9]+)", source)

        if chapter_id == None or image_count == None:
            raise ComicEngine.ComicError("Could not read the page list of %s" % self.url)

        chapter_id  = chapter_id.group(1)
        image_count = int(image_count.group(1) )

        image_urls = []
        page = 1

        while len(image_urls) < image_count and page <= image_count:
            batch = self.getImageBatch(chapter_id, page)

            if len(batch) == 0:
                raise ComicEngine.ComicError("No images listed for page %i of %s" % (page, self.url) )

            for image_url in batch:
                if image_url not in image_urls:
                    image_urls.append(image_url)

            feedback.debug("%i/%i images" % (len(image_urls), image_count) )
            page += len(batch)
            time.sleep(recommended_delay)

        # the page number and its image are stuffed in a bogus query string
        page_urls = []

        for index in range(len(image_urls) ):
            page_urls.append("%s/%i.html?u=%s" % (
                self.url,
                index + 1,
                base64.urlsafe_b64encode(image_urls[index].encode("utf-8") ).decode("utf-8")
                ) )

        return page_urls

class Page(ComicSite):

    def __init__(self, url):
        ComicSite.__init__(self, url)
        self.imgurl = base64.urlsafe_b64decode( util.regexGroup(".+[?&]u=([^&]+)", self.url) ).decode("utf-8")

    def getPageNumber(self):
        return util.regexGroup(".+/([0-9]+)\\.html", self.url)

    def getImageUrl(self):
        return self.imgurl
