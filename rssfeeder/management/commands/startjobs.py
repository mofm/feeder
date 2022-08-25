# Standard Library
import logging
import configparser

from feeder.settings import BASE_DIR
from ..tools.htmlfeed import strip_tags, get_links

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
from rssfeeder.models import Episode, Category


logger = logging.getLogger(__name__)
config = configparser.ConfigParser()
config.read(BASE_DIR.joinpath('feed.ini'))


def save_new_episodes(feed, title, image, category):
    """Saves new episodes to the database.

    Checks the episode GUID agaist the episodes currently stored in the
    database. If not found, then a new `Episode` is added to the database.

    Args:
        feed: requires a feedparser object
        category: requires a category
        title: title of the episode
        image: feed image
    """
    podcast_title = title
    podcast_image = image

    html_types = ["text/html", "application/xhtml+xml"]
    img_tags = ['thumbnail', 'media_thumbnail', 'media_content']
    feed_img = "static/imgs/news.png"

    for item in feed.entries:
        if not Episode.objects.filter(guid=item.guid).exists():
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

                episode = Episode(
                    title=item.title,
                    description=item.description,
                    pub_date=parser.parse(item.published),
                    link=item.link,
                    image=podcast_image,
                    news_img=feed_img,
                    podcast_name=podcast_title,
                    guid=item.guid,
                    category=category,
                )
                episode.save()
            except AttributeError:
                pass


def fetch_feeds():
    """ Fetches new episodes from config ini file"""
    for e in config.sections():
        _feed = feedparser.parse(config[e]['feed'])
        feed_cat = Category.objects.get(name=config[e]['category'])
        feed_title = config[e]['title']
        feed_logo = config[e]['logo']
        save_new_episodes(_feed, feed_title, feed_logo, feed_cat)


def delete_old_job_executions(max_age=604_800):
    """Deletes all apscheduler job execution logs older than `max_age`."""
    DjangoJobExecution.objects.delete_old_job_executions(max_age)


class Command(BaseCommand):
    help = "Runs apscheduler."

    def handle(self, *args, **options):
        scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
        scheduler.add_jobstore(DjangoJobStore(), "default")

        scheduler.add_job(
            fetch_feeds,
            trigger="interval",
            minutes=2,
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
