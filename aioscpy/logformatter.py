import os
import logging

from twisted.python.failure import Failure

from aioscpy.utils.tools import referer_str


SCRAPEDMSG = "Scraped from %(src)s" + os.linesep + "%(item)s"
DROPPEDMSG = "Dropped: %(exception)s" + os.linesep + "%(item)s"
CRAWLEDMSG = "Crawled (%(status)s) %(request)s%(request_flags)s (referer: %(referer)s)%(response_flags)s"
ITEMERRORMSG = "Error processing %(item)s"
SPIDERERRORMSG = "Spider error processing %(request)s (referer: %(referer)s)"
DOWNLOADERRORMSG_SHORT = "Error downloading %(request)s"
DOWNLOADERRORMSG_LONG = "Error downloading %(request)s: %(errmsg)s"


class LogFormatter:

    def crawled(self, request, response, spider):
        request_flags = f' {str(request.flags)}' if request.flags else ''
        response_flags = f' {str(response.flags)}' if response.flags else ''
        return {
            'level': logging.DEBUG,
            'msg': CRAWLEDMSG,
            'args': {
                'status': response.status,
                'request': request,
                'request_flags': request_flags,
                'referer': referer_str(request),
                'response_flags': response_flags,
                # backward compatibility with Scrapy logformatter below 1.4 version
                'flags': response_flags
            }
        }

    def scraped(self, item, response, spider):
        """Logs a message when an item is scraped by a spider."""
        src = response
        return {
            'level': logging.DEBUG,
            'msg': SCRAPEDMSG,
            'args': {
                'src': src,
                'item': item,
            }
        }

    def dropped(self, item, exception, response, spider):
        """Logs a message when an item is dropped while it is passing through the item pipeline."""
        return {
            'level': logging.WARNING,
            'msg': DROPPEDMSG,
            'args': {
                'exception': exception,
                'item': item,
            }
        }

    def item_error(self, item, exception, response, spider):
        """Logs a message when an item causes an error while it is passing
        through the item pipeline.

        .. versionadded:: 2.0
        """
        return {
            'level': logging.ERROR,
            'msg': ITEMERRORMSG,
            'args': {
                'item': item,
            }
        }

    def spider_error(self, failure, request, response, spider):
        """Logs an error message from a spider.

        .. versionadded:: 2.0
        """
        return {
            'level': logging.ERROR,
            'msg': SPIDERERRORMSG,
            'args': {
                'request': request,
                'referer': referer_str(request),
            }
        }

    def download_error(self, failure, request, spider, errmsg=None):
        """Logs a download error message from a spider (typically coming from
        the engine).

        .. versionadded:: 2.0
        """
        args = {'request': request}
        if errmsg:
            msg = DOWNLOADERRORMSG_LONG
            args['errmsg'] = errmsg
        else:
            msg = DOWNLOADERRORMSG_SHORT
        return {
            'level': logging.ERROR,
            'msg': msg,
            'args': args,
        }

    @classmethod
    def from_crawler(cls, crawler):
        return cls()
