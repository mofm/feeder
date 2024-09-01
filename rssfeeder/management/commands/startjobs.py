# Standard Library
import logging
import configparser
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

# Django
from django.conf import settings
from django.core.management.base import BaseCommand
from feeder.settings import BASE_DIR
from utils.htmlfeed import strip_tags, get_links

# Third Party
import aiohttp
from dateutil import parser
import feedparser
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
# from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution

# Models
from rssfeeder.models import Feed, Category

logger = logging.getLogger(__name__)
config = configparser.ConfigParser()
config.read(BASE_DIR.joinpath('feed.ini'))

executor = ThreadPoolExecutor()

async def fetch_feed(session, url):
    timeout = aiohttp.ClientTimeout(total=10)  # Set a 10-second timeout
    try:
        async with session.get(url, timeout=timeout) as response:
            response.raise_for_status()  # Raise an exception for HTTP errors
            return await response.text(), False
    except aiohttp.ClientError as e:
        logger.error(f"Error fetching {url}: {e}")
        return None, True
    except asyncio.TimeoutError:
        logger.error(f"Timeout error fetching {url}")
        return None, True


async def fetch_feeds(section):
    """ Fetches new episodes from config ini file"""
    async with aiohttp.ClientSession() as session:
        try:
            feed_data, error = await fetch_feed(session, config[section]['feed'])
            if not error:
                feed = feedparser.parse(feed_data)
                feed_title = config[section]['title']
                feed_logo = config[section]['logo']
                feed_cat, _ = await Category.objects.aget_or_create(name=config[section]['category'])
                return feed, feed_title, feed_logo, feed_cat
            logger.warning(f"Skipping {section} due to fetch error on all URLs.")
            return None, None, None, None
        except KeyError as exc:
            logger.warning("Error fetching {}: {}".format(section, exc))
            return None, None, None, None
        except Category.DoesNotExist:
            feed_cat, _ = await Category.objects.aget_or_create(name=config[section]['category'])
            return None, None, None, feed_cat


async def save_new_feeds(item, title, image, category):
    """Saves new feed to the database."""
    html_types = {'text/html', 'application/xhtml+xml'}
    img_tags = {'thumbnail', 'media_thumbnail', 'media_content'}
    feed_img = "/static/imgs/news.png"
    if not await Feed.objects.filter(guid=item.guid).aexists():
        logger.info("Processing: {}".format(item.title))
        try:
            for k, v in item.items():
                if k in img_tags and v is not None:
                    if isinstance(v, list):
                        feed_img = v[0]['url']
                    else:
                        feed_img = v['url']
                else:
                    summary_detail = getattr(item, 'summary_detail', None)
                    # if item.summary_detail.type in html_types:
                    if summary_detail and summary_detail.type in html_types:
                        imgs = get_links(item.description)
                        if imgs:
                            feed_img = imgs[0]
                        item.description = strip_tags(item.description)

            episode_data = {
                "title": item.title,
                "description": item.description,
                "pub_date": parser.parse(item.updated),
                "link": item.link,
                "channel_img": image,
                "feed_img": feed_img,
                "channel_name": title,
                "guid": item.guid,
                "category": category,
            }
            logger.info("Saving: {}".format(item.title))
            await Feed.objects.acreate(**episode_data)
        except AttributeError as exc:
            logger.error("Error saving the feed {}: {}".format(item.guid, exc))


async def save_rss():
    """Saves RSS Feeds"""
    tasks = [fetch_feeds(section) for section in config.sections()]
    results = await asyncio.gather(*tasks)

    save_tasks = []
    for feed, title, image, category in results:
        if feed:
            for item in feed.entries:
                save_tasks.append(save_new_feeds(item, title, image, category))

    await asyncio.gather(*save_tasks)


async def delete_old_feeds(max_days=30):
    """Deletes all feeds older than `max_age`."""
    await Feed.objects.filter(pub_date__lte=datetime.now()-timedelta(days=max_days)).adelete()


async def delete_old_job_executions(max_age=604_800):
    """Deletes all apscheduler job execution logs older than `max_age`."""
    await DjangoJobExecution.objects.delete_old_job_executions(max_age)


class Command(BaseCommand):
    help = "Runs apscheduler."

    def handle(self, *args, **options):
        scheduler = AsyncIOScheduler(timezone=settings.TIME_ZONE)
        #scheduler.add_jobstore(DjangoJobStore(), "default")

        scheduler.add_job(
            save_rss,
            trigger="interval",
            minutes=15,
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

        async def run_scheduler():
            try:
                logger.info("Starting scheduler...")
                scheduler.start()
                # Keep the main thread alive
                while True:
                    await asyncio.sleep(1)
            except (KeyboardInterrupt, SystemExit):
                logger.info("Stopping scheduler...")
                scheduler.shutdown()
                logger.info("Scheduler shut down successfully!")

        asyncio.run(run_scheduler())
