import datetime
import io
from html import unescape

import discord
from discord.ext import commands
from discord.ext.commands import Bot, Context
from icalendar import Calendar
from pytz import timezone

from models import db_session
from models.event_sync import EventLink
from utils.utils import get_from_url, is_compsoc_exec_in_guild

LONG_HELP_TEXT = """
Sync events to our website uwcs.co.uk/events."""

SHORT_HELP_TEXT = """Sync events"""

ICAL_URL = "https://uwcs.co.uk/uwcs.ical"


class Sync(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    @commands.check(is_compsoc_exec_in_guild)
    async def event(self, ctx: Context, days: int = 7, logging: bool = False):
        now = datetime.datetime.now(timezone("Europe/London"))
        # datetime's main module also being called datetime is annoying
        before = now + datetime.timedelta(days=days)

        await ctx.send(f"Syncing events from {now} to {before}")

        # Fetch and parse ical from website
        r = await get_from_url(ICAL_URL)
        await ctx.send("Got ical")
        c = io.BytesIO(r)
        cal = Calendar.from_ical(c.getvalue())
        db_links = db_session.query(EventLink).all()
        links = {e.uid: e for e in db_links}

        dc_events = await ctx.guild.fetch_scheduled_events()
        dc_events = {e.id: e for e in dc_events}

        # Add events
        for ev in cal.walk():
            if ev.name != "VEVENT":
                continue

            t = (
                ev.decoded("dtstart")
                .replace(tzinfo=None)
                .astimezone(timezone("Europe/London"))
            )
            print(ev.get("summary"), t, before)
            if t < now:
                await self.log_event(ctx, ev, t, logging, "in the past")
                continue
            if t > before:
                await self.log_event(ctx, ev, t, logging, "outside time frme")
                continue
            await self.update_event(ctx, ev, links, dc_events)
        await ctx.send("Done :)")

    async def log_event(self, ctx, ev, t, logging, reason):
        if logging:
            await ctx.send(
                f"Skipping event {ev.get('summary')} at time {t} as it is {reason}"
            )

    async def update_event(self, ctx, ev, links, dc_events):
        """Check discord events for match, update if existing, otherwise create it"""
        event_args = self.ical_event_to_dc_args(ev)

        # Check for existing
        uid = ev.get("uid")
        link = links.get(uid)

        # Attempt to find existing event
        event = None
        if link:
            event = dc_events.get(link.discord_event)

        # If doesn't exist create a new event
        if not event:
            # Create new event
            event = await ctx.guild.create_scheduled_event(**event_args)
            await ctx.send(
                f"Created event **{ev.get('summary')}** at event {event.url}"
            )
        else:
            # Don't edit if no change
            if self.check_event_equiv(event_args, event):
                # Updat existing event
                await event.edit(**event_args)
                await ctx.send(
                    f"Updated event **{ev.get('summary')}** at event {event.url}"
                )
            else:
                # Don't change event
                await ctx.send(f"No change for event **{ev.get('summary')}**")

        self.update_db_link(uid, event.id, link)

    @staticmethod
    def ical_event_to_dc_args(ev):
        """Construct args for discord event from the ical event"""
        desc = unescape(f"{ev.get('description')}\n\nSee more at {ev.get('url')}")
        return {
            "name": unescape(str(ev.get("summary"))),
            "description": desc,
            "start_time": ev.decoded("dtstart"),
            "end_time": ev.decoded("dtend"),
            "entity_type": discord.EntityType.external,
            "location": str(ev.get("location")),
        }

    @staticmethod
    def check_event_equiv(event_args, event):
        """
        Checks if there has been a change to the event.
        Slight faff since we don't want to compare all fields of the discord event or the ical event
        """
        old_args = {
            "name": event.name,
            "description": event.description,
            "start_time": event.start_time,
            "end_time": event.end_time,
            "entity_type": event.entity_type,
            "location": event.location,
        }
        return event_args != old_args

    @staticmethod
    def update_db_link(uid, event_id, link):
        """Update database record. If new, create, otherwise update"""
        now = datetime.datetime.now(timezone("Europe/London"))
        if not link:
            link = EventLink(uid=uid, discord_event=event_id, last_modified=now)
            db_session.add(link)
        else:
            link.discord_event = event_id
        link.last_modified = now

        db_session.commit()


async def setup(bot: Bot):
    await bot.add_cog(Sync(bot))
