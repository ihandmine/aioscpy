import os

from aioscpy.utils.tools import referer_str


SCRAPEDMSG = "Scraped from {src}" + os.linesep + "{item}"
DROPPEDMSG = "Dropped: {exception}" + os.linesep + "{item}"
CRAWLEDMSG = "Crawled ({status}) {request}{request_flags} (referer: {referer}){response_flags}"
ITEMERRORMSG = "Error processing {item}"
SPIDERERRORMSG = "Spider error processing {request} (referer: {referer})"
DOWNLOADERRORMSG_SHORT = "Error downloading {request}"
DOWNLOADERRORMSG_LONG = "Error downloading {request}: {errmsg}"


class LogFormatter:

    def crawled(self, request, response, spider):
        request_flags = f' {str(request.flags)}' if request.flags else ''
        response_flags = f' {str(response.flags)}' if response.flags else ''
        return {
            'level': "DEBUG",
            'msg': CRAWLEDMSG,
            'args': {
                'status': response.status,
                'request': request,
                'request_flags': request_flags,
                'referer': referer_str(request),
                'response_flags': response_flags,
                # backward compatibility with Aioscpy logformatter below 1.4 version
                'flags': response_flags
            }
        }

    def scraped(self, item, response, spider):
        """Logs a message when an item is scraped by a spider."""
        src = response
        return {
            'level': "DEBUG",
            'msg': SCRAPEDMSG,
            'args': {
                'src': src,
                'item': item,
            }
        }

    def dropped(self, item, exception, response, spider):
        """Logs a message when an item is dropped while it is passing through the item pipeline."""
        return {
            'level': "WARNING",
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
            'level': "ERROR",
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
            'level': "ERROR",
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
            'level': "ERROR",
            'msg': msg,
            'args': args,
        }

    @classmethod
    def from_crawler(cls, crawler):
        return cls()
