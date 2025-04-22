import discord
from discord.ext import commands, tasks
from discord.ext.commands import Bot
from discord import app_commands
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

intents = discord.Intents.default()
intents.members = True  # Required for member-related events like joins and role changes
intents.message_content = True  # Required to read message content for spam detection

client = commands.Bot(command_prefix="!", intents=intents)

# Initialize a dictionary to store points for users (you can use a database for production)
user_points = {}

# Logs directory
log_file = "moderation_logs.json"

# Load previous logs from file
def load_logs():
    if os.path.exists(log_file):
        with open(log_file, 'r') as file:
            return json.load(file)
    return {}

# Save logs to a file
def save_logs(logs):
    with open(log_file, 'w') as file:
        json.dump(logs, file, indent=4)

logs = load_logs()

# Log when a member joins or leaves
@client.event
async def on_member_join(member):
    logs["join_leave_logs"].append(f"{member.name} joined at {member.joined_at}")
    save_logs(logs)

@client.event
async def on_member_remove(member):
    logs["join_leave_logs"].append(f"{member.name} left at {member.joined_at}")
    save_logs(logs)

# Log when roles are added or removed
@client.event
async def on_member_update(before, after):
    if before.roles != after.roles:
        logs["role_changes"].append(f"Roles updated for {after.name} at {after.joined_at}")
        save_logs(logs)

# Log deleted or edited messages
@client.event
async def on_message_delete(message):
    logs["message_logs"].append(f"Message deleted: {message.content} by {message.author}")
    save_logs(logs)

@client.event
async def on_message_edit(before, after):
    logs["message_logs"].append(f"Message edited from {before.content} to {after.content} by {after.author}")
    save_logs(logs)

# Warn Command
@client.command()
async def warn(ctx, member: discord.Member, points: int, *, reason: str):
    """Warn a user, track their points and take action if necessary."""
    if member.id not in user_points:
        user_points[member.id] = 0
    user_points[member.id] += points

    # Save updated points to logs
    logs["warnings"].append(f"{member.name} warned by {ctx.author.name}. Points: {user_points[member.id]} - Reason: {reason}")
    save_logs(logs)

    await ctx.send(f"{member.mention} has been warned. Total points: {user_points[member.id]}")

    # Take action based on points
    if user_points[member.id] >= 100:
        await member.ban(reason=f"Reached 100 points. {reason}")
        await ctx.send(f"{member.name} has been banned for reaching 100 points.")
    elif user_points[member.id] >= 75:
        await member.kick(reason=f"Reached 75 points. {reason}")
        await ctx.send(f"{member.name} has been kicked for reaching 75 points.")

# Anti-Spam & Auto Mute
@client.event
async def on_message(message):
    if message.author.bot:
        return

    # Anti-Spam Check
    if "@" in message.content and message.mentions:
        await message.delete()  # Delete spammy mentions
        await message.author.timeout(duration=60)  # Timeout the user for 1 minute
        await message.channel.send(f"{message.author.mention} has been timed out for spamming pings!")

    await client.process_commands(message)

# Block inappropriate GIFs (basic example)
@client.event
async def on_message(message):
    if message.author.bot:
        return

    # Check for inappropriate gifs
    if "https://cdn.discordapp.com/attachments" in message.content and any(inappropriate_word in message.content.lower() for inappropriate_word in ["porn", "sex", "adult"]):
        await message.delete()
        await message.channel.send(f"{message.author.mention}, inappropriate content is not allowed!")
    
    await client.process_commands(message)

# Command to show warning points of a user
@client.command()
async def points(ctx, member: discord.Member):
    """Check the points of a user."""
    points = user_points.get(member.id, 0)
    await ctx.send(f"{member.name} has {points} points.")

# Bot startup event
@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    print(f"Bot is ready to moderate the server!")

# Start the bot
client.run(os.getenv("DISCORD_TOKEN"))
