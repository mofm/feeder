# Standard Library
import logging
import configparser
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor, as_completed
from feeder.settings import BASE_DIR
from utils.htmlfeed import strip_tags, get_links

# Django
from django.conf import settings
from django.core.management.base import BaseCommand

# Third Party
import feedparser
from dateutil import parser
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution

# Models
from rssfeeder.models import Feed, Category

# added for macOS compatibility. Because macOS default method: spawn
mp.set_start_method('fork')

logger = logging.getLogger(__name__)
config = configparser.ConfigParser()
config.read(BASE_DIR.joinpath('feed.ini'))


def save_new_feeds(item, title, image, category):
    """Saves new feed to the database.

    Checks the feed GUID against the feeds currently stored in the
    database. If not found, then a new `feed` is added to the database.

    Args:
        item: requires a feedparser object
        category: requires a category
        title: title of the feed
        image: channel image
    """
    html_types = {'text/html', 'application/xhtml+xml'}
    img_tags = {'thumbnail', 'media_thumbnail', 'media_content'}
    feed_img = "/static/imgs/news.png"
    # Check if feed exists in the database
    if not Feed.objects.filter(guid=item.guid).exists():
        try:
            for k, v in item.items():
                if k in img_tags and v is not None:
                    if isinstance(v, list):
                        feed_img = v[0]['url']
                    else:
                        feed_img = v['url']
                else:
                    if item.summary_detail.type in html_types:
                        imgs = get_links(item.description)
                        if imgs:
                            feed_img = imgs[0]
                        item.description = strip_tags(item.description)

            episode = Feed(
                title=item.title,
                description=item.description,
                pub_date=parser.parse(item.published),
                link=item.link,
                channel_img=image,
                feed_img=feed_img,
                channel_name=title,
                guid=item.guid,
                category=category,
            )
            return episode
        except AttributeError:
            pass


def fetch_feeds(section):
    """ Fetches new episodes from config ini file"""
    try:
        _feed = feedparser.parse(config[section]['feed'])
        feed_title = config[section]['title']
        feed_logo = config[section]['logo']
        feed_cat = Category.objects.get(name=config[section]['category'])
    except KeyError:
        pass
    except Category.DoesNotExist:
        feed_cat = Category.objects.get_or_create(name=config[section]['category'])[0]

    return _feed, feed_title, feed_logo, feed_cat


def save_rss():
    """Saves RSS Feeds"""
    futures = []
    with ThreadPoolExecutor() as executor:
        for section in config.sections():
            feed, title, image, category = fetch_feeds(section)
            for item in feed.entries:
                futures.append(executor.submit(save_new_feeds, item, title, image, category))

    Feed.objects.bulk_create([future.result() for future in as_completed(futures)
                              if future.result()], batch_size=1000)


def delete_old_job_executions(max_age=604_800):
    """Deletes all apscheduler job execution logs older than `max_age`."""
    DjangoJobExecution.objects.delete_old_job_executions(max_age)


class Command(BaseCommand):
    help = "Runs apscheduler."

    def handle(self, *args, **options):
        scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
        scheduler.add_jobstore(DjangoJobStore(), "default")

        scheduler.add_job(
            save_rss,
            trigger="interval",
            minutes=1,
            id="FetchFeeds",
            max_instances=1,
            replace_existing=True,
        )
        logger.info("Added job: News Feed.")

        scheduler.add_job(
            delete_old_job_executions,
            trigger=CronTrigger(
                day_of_week="mon", hour="00", minute="00"
            ),  # Midnight on Monday, before start of the next work week.
            id="Delete Old Job Executions",
            max_instances=1,
            replace_existing=True,
        )
        logger.info("Added weekly job: Delete Old Job Executions.")

        try:
            logger.info("Starting scheduler...")
            scheduler.start()
        except KeyboardInterrupt:
            logger.info("Stopping scheduler...")
            scheduler.shutdown()
            logger.info("Scheduler shut down successfully!")
