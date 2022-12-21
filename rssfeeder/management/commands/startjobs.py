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
from datetime import datetime, timedelta
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
        logger.info("Processing: {}".format(item.title))
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
                # as of version 5.1.1, feedparser returns a datetime object
                # if this key doesn’t exist but entries[i].published does,
                # the value of entries[i].published will be returned.
                # changed to use updated_parsed instead of published_parsed
                pub_date=parser.parse(item.updated),
                link=item.link,
                channel_img=image,
                feed_img=feed_img,
                channel_name=title,
                guid=item.guid,
                category=category,
            )
            logger.info("Saving: {}".format(item.title))
            return episode
        except AttributeError as exc:
            logger.error("Error saving the feed {}: {}".format(item.guid, exc))
            pass


def fetch_feeds(section):
    """ Fetches new episodes from config ini file"""
    try:
        _feed = feedparser.parse(config[section]['feed'])
        feed_title = config[section]['title']
        feed_logo = config[section]['logo']
        feed_cat = Category.objects.get(name=config[section]['category'])
    except KeyError as exc:
        logger.warning("Error fetching {}: {}".format(section, exc))
        pass
    except Category.DoesNotExist:
        feed_cat = Category.objects.get_or_create(name=config[section]['category'])[0]

    return _feed, feed_title, feed_logo, feed_cat


def save_rss():
    """Saves RSS Feeds"""
    futures = []
    with ThreadPoolExecutor() as executor:
        for section in config.sections():
            logger.info("Fetching {}".format(section))
            feed, title, image, category = fetch_feeds(section)
            for item in feed.entries:
                futures.append(executor.submit(save_new_feeds, item, title, image, category))

    logger.info("Saving bulk feeds")
    Feed.objects.bulk_create([future.result() for future in as_completed(futures)
                              if future.result()], batch_size=1000, ignore_conflicts=True)


def delete_old_feeds(max_days=30):
    """Deletes all feeds older than `max_age`."""
    Feed.objects.filter(pub_date__lte=datetime.now()-timedelta(days=max_days)).delete()


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
            minutes=30,
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

        scheduler.add_job(
            delete_old_feeds,
            trigger=CronTrigger(
                hour="00", minute="30"
            ),  # every day at 00:30
            id="Delete Old News Feeds",
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
