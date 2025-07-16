# Discord Reddit Bot

A Discord bot that monitors Reddit for posts and comments from specific users and sends notifications to your Discord server.

## Setup

1. **Invite the bot**: [Add to your server](https://discord.com/oauth2/authorize?client_id=1384871341198544989)

2. **Grant permissions**: Make sure the bot has permission to:
   - Send messages in the channel you want notifications in
   - Use slash commands

3. **Configure notifications**: In the channel where you want Reddit notifications, run:
   ```
   /setredditchannel
   ```
   *(Admin permissions required)*

## Commands

- `/setredditchannel` - Set the current channel for Reddit notifications (admin only)
- `/removeredditchannel` - Stop Reddit notifications in this server (admin only)

## What it does

The bot monitors r/2007scape for new posts and comments from Jagex employees and sends real-time notifications to your configured Discord channel, including context for comment replies.
