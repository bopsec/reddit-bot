import discord
from discord import app_commands
import asyncpraw
import os
import json
import asyncio
from dotenv import load_dotenv

load_dotenv()

SETTINGS_FILE = "reddit_channel_settings.json"

def load_settings():
    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)

channel_settings = load_settings()

def set_channel_for_guild(guild_id, channel_id):
    channel_settings[str(guild_id)] = channel_id
    save_settings(channel_settings)

REDDIT_USERNAMES = [
    "JagexElena", "JagexGoblin", "JagexAyiza", "JagexLight",
    "JagexBlossom", "JagexRach", "JagexArcane", "JagexHusky", "JagexSarnie",
    "JagexNox", "JagexSween", "JagexRice", "JagexTwisted"
    ,"BopOSRS" # just for testing i dont actually use the acc
]

NAMES_LOWER = set(u.lower() for u in REDDIT_USERNAMES)
SUBREDDIT = "2007scape"
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()

class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.already_notified_submissions = set()
        self.already_notified_comments = set()
        self.reddit = None
    async def setup_hook(self):
        self.reddit = asyncpraw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
        )
        self.bg_task = self.loop.create_task(self.reddit_checker_task())

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})', flush=True)
        activity = discord.Activity(type=discord.ActivityType.listening, name="/setredditchannel")
        await self.change_presence(activity=activity)
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} slash command(s)", flush=True)
        except Exception as e:
            print(f"Error syncing slash commands: {e}", flush=True)

    async def reddit_checker_task(self):
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                # Build the list of Discord channels to send alerts to
                channels = []
                for channel_id in set(channel_settings.values()):
                    channel = self.get_channel(int(channel_id))
                    if channel is not None:
                        channels.append(channel)
                if not channels:
                    print("No Discord channels are configured for notifs.", flush=True)
                    await asyncio.sleep(60)
                    continue

                subreddit = await self.reddit.subreddit(SUBREDDIT)
                # -----------------------------
                # ----------- Posts -----------
                # -----------------------------
                async for submission in subreddit.new(limit=25):
                    if (
                        submission.author
                        and submission.author.name.lower() in NAMES_LOWER
                        and submission.id not in self.already_notified_submissions
                    ):
                        msg = f"**New post by u/{submission.author.name}**: [{submission.title}]({submission.shortlink})"
                        for channel in channels:
                            try:
                                await channel.send(msg)
                            except Exception as e:
                                print(f"Tried to send post: {e}", flush=True)
                        self.already_notified_submissions.add(submission.id)

                # --------------------------------
                # ----------- Comments -----------
                # --------------------------------
                async for comment in subreddit.comments(limit=150):
                    if (
                        comment.author
                        and comment.author.name.lower() in NAMES_LOWER
                        and comment.id not in self.already_notified_comments
                    ):
                        parent_context = ""
                        parent_author = ""
                        try:
                            parent = await comment.parent()
                            # wait for the fker to load
                            await parent.load()
                            # Only fetch parent if it's a comment, not a submission
                            if isinstance(parent, asyncpraw.models.Comment):
                                parent_body = parent.body.strip()
                                parent_author = parent.author.name if parent.author else "[deleted]"

                                # Add ">" formatting to parent context
                                # Limit to first 500 chars
                                if len(parent_body) > 500:
                                    parent_body = parent_body[:500] + "..."

                                parent_lines = parent_body.splitlines()
                                parent_blockquote = "\n".join([f"> {line}" for line in parent_lines])
                                parent_context = f"**Replying to u/{parent_author}**:\n{parent_blockquote}\n\n"
                            else:
                                # The "parent" is the main post itself
                                submission_title = parent.title
                                parent_context = f"**Commenting on**: [{submission_title}]({parent.shortlink})\n\n"
                        except Exception as e:
                            print(f"Error getting parent context: {e}", flush=True)
                            parent_context = ""

                        # Build the context-link (shows parent tree on Reddit)
                        # < > around link to remove embed
                        link = f"<https://reddit.com{comment.permalink}?context=10>"

                        msg = (
                            f"{parent_context}"
                            f"**{comment.author.name}**:\n"
                            f"{comment.body.strip()[:1000]}{'...' if len(comment.body.strip()) > 1000 else ''}\n\n"
                            f"[View full conversation]({link})"
                        )
                        for channel in channels:
                            try:
                                await channel.send(msg)
                            except Exception as e:
                                print(f"Tried to send comment: {e}", flush=True)
                        self.already_notified_comments.add(comment.id)
            except Exception as e:
                print("EXCEPTION in reddit_checker_task:", repr(e), flush=True)
            await asyncio.sleep(60)
client = MyClient()

@client.tree.command(name="setredditchannel", description="Set this channel for Reddit notifications (admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def setredditchannel(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    channel_id = interaction.channel.id

    # Load and check bot perms
    channel = interaction.channel
    bot_member = interaction.guild.get_member(client.user.id)
    channel_perms = channel.permissions_for(bot_member)
    if not channel_perms.view_channel:
        await interaction.response.send_message("Error: I don't have permission to view this channel.", ephemeral=True)
        return
    if not channel_perms.send_messages:
        await interaction.response.send_message("Error: I don't have permission to send messages in this channel.", ephemeral=True)
        return

    # If we have the right perms, set channel
    set_channel_for_guild(guild_id, channel_id)
    await interaction.response.send_message("This channel is now set for Reddit notifications!", ephemeral=True)

@client.tree.command(name="removeredditchannel", description="Stop Reddit notifications in this server (admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def removeredditchannel(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    if str(guild_id) in channel_settings:
        del channel_settings[str(guild_id)]
        save_settings(channel_settings)
        await interaction.response.send_message("Reddit notifications have been removed for this server.", ephemeral=True)
    else:
        await interaction.response.send_message("There is no Reddit notifications channel set for this server.", ephemeral=True)

@client.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("You need to be an admin to use this!", ephemeral=True)
    else:
        await interaction.response.send_message("An unknown error occurred.", ephemeral=True)

client.run(DISCORD_TOKEN)
