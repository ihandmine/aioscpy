from aioscpy import call_grace_instance
from aioscpy.utils.tools import get_project_settings


def load_file_to_execute():
    process = call_grace_instance("crawler_process", get_project_settings())
    process.load_spider(path='./spiders')
    process.start()


def load_name_to_execute():
    process = call_grace_instance("crawler_process", get_project_settings())
    process.crawl('quotes')
    process.start()


if __name__ == '__main__':
    load_name_to_execute()
