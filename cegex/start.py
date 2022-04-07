from aioscpy.crawler import CrawlerProcess
# from aioscpy.utils.project import get_project_settings


from baidu import BaiduSpider


process = CrawlerProcess()

# process.crawl(BaiduSpider)
process.crawl(BaiduSpider)

process.start()

