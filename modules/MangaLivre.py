""" Manga Livre (mangalivre.blog)

Chapter pages carry their images directly in the markup, so only the comic
page needs interpreting - see Comic.getChapterUrls()
"""

import web
import re
import base64
import feedback
import ComicEngine
import util

# Edit this to list the valid domains for the site
valid_domains = ['mangalivre.blog', 'www.mangalivre.blog']
recommended_delay = 1

site_url = "https://mangalivre.blog"

class ComicSite(web.WebResource):

    def __init__(self, url):
        url = self.validateUrl(url)

        web.WebResource.__init__(self, url)
        self.domain = web.getUrlComponents(url, 2)

    def validateUrl(self, url):
        """ If you want to rewrite the URL before accessing it, modify this section
        """
        url = re.sub("^http://", "https://", url)
        return re.sub("^https://(www\\.)?mangalivre\\.blog/", "%s/" % site_url, url)

class Comic(ComicSite):

    def __init__(self, url):
        ComicSite.__init__(self, url)

        if "/capitulo/" in self.url:
            # re-initialise, so the chapter page does not stay cached as our data
            ComicSite.__init__(self, self.findComicUrl() )

        self.url = re.sub("(/manga/[^/]+)/.*", "\\1/", self.url)

    def findComicUrl(self):
        """ Get the comic's own page from one of its chapter pages
        """
        for elem_a in self.getDomObject().cssselect("a"):
            matched = re.match("(%s/manga/[^/]+)/" % site_url, elem_a.attrib.get('href', "") )

            if matched:
                return "%s/" % matched.group(1)

        raise ComicEngine.ComicError("Could not find the comic page of %s" % self.url)

    def getComicLowerName(self):
        return util.regexGroup(".+/manga/([^/]+)", self.url)

    def getChapterUrls(self):
        doc = self.getDomObject()
        chapters = {}

        for item in doc.cssselect("article.chapter-grid-item"):
            number = item.attrib.get('data-chapter-number', "")
            links  = item.cssselect("a")

            if not re.match("^[0-9]+(\\.[0-9]+)?$", number) or len(links) == 0:
                continue

            url = links[0].attrib.get('href', "")

            # re-posted chapters get a numbered slug (...-capitulo-179-2) and tend
            # to be the shorter version of the chapter - keep the original one
            if number not in chapters or len(url) < len(chapters[number]):
                chapters[number] = url

        if len(chapters) == 0:
            raise ComicEngine.ComicError("Could not find any chapters on %s" % self.url)

        # the chapter number is only stated here, so carry it in a bogus query string
        urls = [ "%s?n=%s" % (chapters[number], number) for number in chapters ]

        util.naturalSort(urls, ".+[?&]n=([0-9.]+)$")

        return urls

class Chapter(ComicSite):

    def __init__(self, url):
        ComicSite.__init__(self, url)

        self.number = util.regexGroup(".+[?&]n=([0-9.]+)", self.url)
        self.url = re.sub("[?].*$", "", self.url)

        if self.number == None:
            self.number = self.findChapterNumber()

    def findChapterNumber(self):
        """ Read the chapter number off the page itself

        Only needed when a chapter URL was supplied directly - the slug cannot
        be trusted, as a re-posted chapter 179 lives at ...-capitulo-179-2
        """
        titles = self.getDomObject().cssselect("title")

        if len(titles) > 0:
            number = util.regexGroup(".+[Cc]ap[ií]tulo\\s*([0-9]+(\\.[0-9]+)?)", titles[0].text_content() )

            if number != None:
                return number

        raise ComicEngine.ComicError("Could not determine the chapter number of %s" % self.url)

    def getChapterNumber(self):
        return self.number

    def getChapterLowerName(self):
        slug = util.regexGroup(".+/capitulo/([^/?]+)", self.url)
        return "%s_c%s" % (re.sub("-capitulo-.*$", "", slug), util.padChapterNumber(self.number) )

    def getPageUrls(self):
        images = self.getDomObject().cssselect("img.chapter-image")
        page_urls = []

        for index in range(len(images) ):
            image_url = images[index].attrib.get('src', images[index].attrib.get('data-src', "") )

            if image_url == "":
                continue

            feedback.debug(image_url)

            # the page number and its image are stuffed in a bogus query string
            page_urls.append("%s?p=%i&u=%s" % (
                self.url,
                index + 1,
                base64.urlsafe_b64encode(image_url.encode("utf-8") ).decode("utf-8")
                ) )

        return page_urls

class Page(ComicSite):

    def __init__(self, url):
        ComicSite.__init__(self, url)
        self.pagenum = util.regexGroup(".+[?&]p=([0-9]+)", self.url)
        self.imgurl = base64.urlsafe_b64decode( util.regexGroup(".+[?&]u=([^&]+)", self.url) ).decode("utf-8")

    def getPageNumber(self):
        return self.pagenum

    def getImageUrl(self):
        return self.imgurl
