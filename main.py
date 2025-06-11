import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

bot = MyBot()
warns = {}

# Warn Data Management
def load_warns():
    global warns
    if os.path.exists("warns.json"):
        with open("warns.json", "r") as f:
            try:
                warns = json.load(f)
            except json.JSONDecodeError:
                warns = {}

def save_warns():
    with open("warns.json", "w") as f:
        json.dump(warns, f, indent=4)

@bot.event
async def on_ready():
    load_warns()
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user}")

# /warn Command
@bot.tree.command(name="warn", description="Warn a member with a reason and points")
@app_commands.describe(member="The user to warn")
async def warn(interaction: discord.Interaction, member: discord.Member):
    class ReasonView(discord.ui.View):
        def __init__(self):
            super().__init__()
            self.reasons = {
                "Spam": 5,
                "Minor Language": 10,
                "Harassment": 15,
                "NSFW Content": 20,
                "Staff Disrespect": 25,
                "Hate Speech": 30,
                "Advertising": 40,
                "Doxxing / Personal Info": 50,
                "Serious Offense (Kick)": 75,
                "Extreme Offense (Ban)": 100,
            }
            for reason, points in self.reasons.items():
                self.add_item(discord.ui.Button(label=reason, style=discord.ButtonStyle.danger, custom_id=reason))

        async def interaction_check(self, i: discord.Interaction) -> bool:
            return i.user == interaction.user

        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
        async def cancel(self, interaction_: discord.Interaction, button: discord.ui.Button):
            await interaction_.message.delete()

        async def on_button_click(self, interaction_: discord.Interaction):
            reason = interaction_.data["custom_id"]
            points = self.reasons[reason]

            uid = str(member.id)
            gid = str(interaction.guild.id)
            if gid not in warns:
                warns[gid] = {}
            if uid not in warns[gid]:
                warns[gid][uid] = []

            warns[gid][uid].append({"reason": reason, "points": points})
            save_warns()

            await interaction_.message.delete()
            await interaction_.response.send_message(
                f"⚠️ {member.mention} has been warned for **{reason}** (+{points} points)", ephemeral=False
            )

            log_channel = interaction_.guild.get_channel(1332836562484072509)
            if log_channel:
                await log_channel.send(f"⚠️ {interaction_.user.mention} warned {member.mention} for **{reason}** (+{points} points).")

    view = ReasonView()
    await interaction.response.send_message("Choose a reason to warn:", view=view, ephemeral=False)

# /warnings Command
@bot.tree.command(name="warnings", description="Check a member's warnings")
@app_commands.describe(member="The user to check")
async def warnings(interaction: discord.Interaction, member: discord.Member):
    uid = str(member.id)
    gid = str(interaction.guild.id)

    if gid in warns and uid in warns[gid]:
        user_warns = warns[gid][uid]
        total = sum(w["points"] for w in user_warns)
        reason_list = "\n".join([f"- {w['reason']} (+{w['points']} pts)" for w in user_warns])
        await interaction.response.send_message(
            f"⚠️ Warnings for {member.mention} ({total} points):\n{reason_list}"
        )
    else:
        await interaction.response.send_message(f"✅ {member.mention} has no warnings.")

# /warning_remove Command
@bot.tree.command(name="warning_remove", description="Remove a warning from a member")
@app_commands.describe(member="The user to remove a warning from")
async def warning_remove(interaction: discord.Interaction, member: discord.Member):
    uid = str(member.id)
    gid = str(interaction.guild.id)

    if gid not in warns or uid not in warns[gid] or not warns[gid][uid]:
        await interaction.response.send_message(f"✅ {member.mention} has no warnings.", ephemeral=True)
        return

    class RemoveWarningView(discord.ui.View):
        def __init__(self, warnings_list):
            super().__init__()
            self.warnings_list = warnings_list
            for idx, warn in enumerate(warnings_list):
                label = f"{warn['reason']} (+{warn['points']} pts)"
                self.add_item(discord.ui.Button(label=label, style=discord.ButtonStyle.danger, custom_id=str(idx)))

        async def interaction_check(self, i: discord.Interaction) -> bool:
            return i.user == interaction.user

        async def on_button_click(self, interaction_: discord.Interaction):
            index = int(interaction_.data["custom_id"])
            removed = warns[gid][uid].pop(index)
            save_warns()

            try:
                await interaction_.message.delete()
            except discord.errors.NotFound:
                print("⚠️ Message already deleted or expired.")

            await interaction_.response.send_message(
                f"✅ Removed warning: **{removed['reason']}** (-{removed['points']} pts) from {member.mention}",
                ephemeral=False,
            )

            log_channel = interaction_.guild.get_channel(1332836562484072509)
            if log_channel:
                await log_channel.send(f"✅ {interaction_.user.mention} removed a warning from {member.mention} for **{removed['reason']}** (-{removed['points']} pts).")

    view = RemoveWarningView(warns[gid][uid])
    await interaction.response.send_message(f"Select a warning to remove from {member.mention}:", view=view, ephemeral=True)

# /dm Command
@bot.tree.command(name="dm", description="Send a direct message to a user and receive their response in the bot-talk channel")
@app_commands.describe(member="The user to send a DM to", msg="The message to send")
async def dm(interaction: discord.Interaction, member: discord.Member, msg: str):
    try:
        # Send the DM to the user
        await member.send(msg)
        await interaction.response.send_message(f"✅ Sent DM to {member.mention}. Please wait for a response.")
        
        
        # Wait for a reply from the user in the DM
        def check(m):
            return m.author == member and isinstance(m.channel, discord.DMChannel)

        # Wait for the user to send a message in DM
        response = await bot.wait_for("message", check=check)
        
        # Log the user's reply in the bot-talk channel
        bot_talk_channel = bot.get_channel(1365070042152304660)  # Replace with your bot-talk channel ID
        if bot_talk_channel:
            await bot_talk_channel.send(f"💬 **{member.name}** responded in DM: {response.content}")

    except discord.errors.Forbidden:
        await interaction.response.send_message(f"❌ Could not send a DM to {member.mention}. They may have DMs disabled.")

# /kick Command
@bot.tree.command(name="kick", description="Kick a member")
@app_commands.describe(member="The user to kick", reason="Reason for the kick")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str):
    try:
        await member.kick(reason=reason)
        await interaction.response.send_message(f"👈 {member.mention} has been kicked. Reason: {reason}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to kick: {e}")

# /ban Command
@bot.tree.command(name="ban", description="Ban a member")
@app_commands.describe(member="The user to ban", reason="Reason for the ban")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str):
    try:
        await member.ban(reason=reason)
        await interaction.response.send_message(f"🔨 {member.mention} has been banned. Reason: {reason}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to ban: {e}")

# /unban Command
@bot.tree.command(name="unban", description="Unban a user by their username#discriminator or ID")
@app_commands.describe(user="Username#1234 or user ID")
async def unban(interaction: discord.Interaction, user: str):
    bans = await interaction.guild.bans()
    for entry in bans:
        if user == str(entry.user) or user == str(entry.user.id):
            await interaction.guild.unban(entry.user)
            await interaction.response.send_message(f"✅ Unbanned {entry.user}.")
            return
    await interaction.response.send_message("❌ User not found in ban list.")

# /mute Command
@bot.tree.command(name="mute", description="Timeout a member for a duration")
@app_commands.describe(member="The user to timeout", minutes="Minutes to mute them")
async def mute(interaction: discord.Interaction, member: discord.Member, minutes: int):
    try:
        duration = discord.utils.utcnow() + discord.timedelta(minutes=minutes)
        await member.edit(timeout_until=duration)
        await interaction.response.send_message(f"🔇 {member.mention} has been muted for {minutes} minute(s).")
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to mute: {e}")

# /purge Command
@bot.tree.command(name="purge", description="Delete messages from a channel")
async def purge(interaction: discord.Interaction):
    class PurgeView(discord.ui.View):
        def __init__(self):
            super().__init__()
            self.preset_counts = [1, 5, 10, 15, 20, 25, 30, 35, 40, 45,
                                  50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100]
            for count in self.preset_counts:
                self.add_item(discord.ui.Button(label=str(count), style=discord.ButtonStyle.danger, custom_id=str(count)))
            self.add_item(discord.ui.Button(label="Custom", style=discord.ButtonStyle.primary, custom_id="custom"))

        async def interaction_check(self, i: discord.Interaction) -> bool:
            return i.user == interaction.user

        async def on_button_click(self, i: discord.Interaction):
            selection = i.data["custom_id"]

            async def perform_purge(amount):
                deleted = await i.channel.purge(limit=amount)
                await i.response.send_message(f"🧹 Deleted {len(deleted)} message(s).", ephemeral=False)

            if selection == "custom":
                await i.response.send_message("💬 Enter a number (max 100) to purge:", ephemeral=True)

                def check(m):
                    return m.author == interaction.user and m.channel == interaction.channel

                try:
                    msg = await bot.wait_for("message", check=check)
                    amount = int(msg.content)
                    if 1 <= amount <= 100:
                        await msg.delete()
                        await perform_purge(amount)
                    else:
                        await interaction.followup.send("❌ Invalid number. Must be between 1 and 100.", ephemeral=True)
                except ValueError:
                    await interaction.followup.send("❌ Invalid input. Please enter a number.", ephemeral=True)
            else:
                await perform_purge(int(selection))

    view = PurgeView()
    await interaction.response.send_message("🧹 Select how many messages to purge:", view=view, ephemeral=False)

bot.run(TOKEN)
