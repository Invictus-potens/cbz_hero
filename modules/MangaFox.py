import web
import util
import re
import time
import base64
import feedback
import ComicEngine

valid_domains = ['fanfox.net', 'm.fanfox.net', 'mangafox.me', 'mangafox.la']
recommended_delay = 1

class ComicSite(web.WebResource):

    def __init__(self, url):
        url = self.validateUrl(url)

        web.WebResource.__init__(self, url)
        self.domain = web.getUrlComponents(url, 2)

    def validateUrl(self, url):
        """ If you want to rewrite the URL before accessing it, modify this section
        """
        for target_domain in valid_domains:
            url = url.replace(target_domain, valid_domains[0])

        newstring = re.sub("https://", "http://", url)
        return newstring

    def getImageHeaders(self):
        # the image CDN answers 403 to referer-less requests
        return {'Referer': "http://%s/" % valid_domains[0]}

class Comic(ComicSite):
    
    def __init__(self, url):
        ComicSite.__init__(self, url)
        self.url = re.sub("/manga/([^/]+)/.+", "/manga/\\1/", self.url)
        self.name = self.getComicLowerName()

    def getComicLowerName(self):
        return util.regexGroup(".+/manga/([^/]+)", self.url)

    def getChapterUrls(self):
        feedback.debug("domain: "+str(self.domain))

        doc = self.getDomObject()
        obj_a = doc.cssselect("a")
        
        urls = []
        for item in obj_a:
            if not "href" in item.attrib.keys():
                continue
            # site serves relative hrefs (/manga/name/...) now; used to be protocol-relative (//domain/manga/name/...)
            m = re.match(r"""(?:https?:)?(?://%s)?(/manga/%s/[^"]+)"""%(re.escape(self.domain),re.escape(self.name) ), item.attrib["href"])
            if not m:
                continue
            target_url = "http://%s%s" % (self.domain, m.group(1))
            if not target_url in urls:
                urls.append(target_url)

        if len(urls) < 1:
            raise ComicEngine.ComicError("No URLs returned from %s"%self.url)

        util.naturalSort(urls, ".+/c([0-9.]+)/")
        # I've seen one series which was a load of "chapter 1" in different volumes... how to deal with that ?
        feedback.debug(urls)
        return urls

class Chapter(ComicSite):
    
    def __init__(self, url):
        ComicSite.__init__(self, url)

    def getChapterNumber(self):
        # FIXME what about when volumes have same-numbered chapters ??
        return util.regexGroup(".+/c([0-9.]+)/", self.url)

    def getChapterLowerName(self):
        chapter_lower = "%s%s%s" % ( Comic(self.url).name , "_chapter-" , self.getChapterNumber() )
        return chapter_lower

    def getBaseChapterUrl(self):
        """ Chapters are defined by their first page, so the base has to be the parent
        """
        i = self.url.rfind('/')
        return self.url[:i]

    def getImageBatch(self, base_url, chapter_id, page, key):
        """ Ask the chapterfun.ashx AJAX endpoint for the images starting at a page

        Site answers with packed javascript declaring a host prefix (pix) and
        the paths of that page and the next one (pvalue) - same scheme as
        MangaHere's chapterfun.ashx. Returns the full URLs.
        """
        endpoint = "%s/chapterfun.ashx?cid=%s&page=%i&key=%s" % (base_url, chapter_id, page, key)
        resource = web.WebResource(endpoint, headers={'Referer': "%s/1.html" % base_url})

        unpacked = util.unpackJs(resource.getSource() )

        if unpacked == None:
            return []

        prefix = re.search('pix\\s*=\\s*"([^"]*)"', unpacked)
        values = re.search('pvalue\\s*=\\s*\\[(.*?)\\]', unpacked)

        if prefix == None or values == None:
            return []

        return [ re.sub("^//", "https://", prefix.group(1) + path) for path in re.findall('"([^"]+)"', values.group(1) ) ]

    def getPageUrls(self):
        base_url = self.getBaseChapterUrl()
        source   = self.getSource()

        chapter_id  = re.search("chapterid\\s*=\\s*([0-9]+)", source)
        image_count = re.search("imagecount\\s*=\\s*([0-9]+)", source)
        # the anti-scrape key (dm5_key) ships packed with Dean Edwards' packer
        packed_key  = util.unpackJs(source)

        if chapter_id == None or image_count == None or packed_key == None:
            raise ComicEngine.ComicError("Could not read the page list of %s" % self.url)

        chapter_id  = chapter_id.group(1)
        image_count = int(image_count.group(1) )
        key         = ''.join(re.findall("'([0-9a-z])'", packed_key) )

        image_urls = []
        page = 1

        while len(image_urls) < image_count and page <= image_count:
            batch = self.getImageBatch(base_url, chapter_id, page, key)

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
                base_url,
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
