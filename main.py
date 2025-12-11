import os
import discord
from discord import app_commands, Interaction, Role
from discord.abc import GuildChannel
import asyncio
from datetime import datetime, timezone

# ---------------------- CONFIG ----------------------
GUILD_ID = 1327228156998062111

# Channel IDs
STAGE_CHANNEL_ID = 1446483376377827370
ANNOUNCE_CHANNEL_ID = 1354772035108077638
WELCOME_CHANNEL_ID = 1327228553078505502
RULES_CHANNEL_ID = 1327228580920557650
PROMOTION_LOG_CHANNEL_ID = 1448391519827398910
DEMOTION_LOG_CHANNEL_ID = 1448391619509223556

MODERATOR_ROLE_NAME = "Ⓜ️ Moderator"
UNVERIFIED_ROLE_NAME = "Visitor"

# ---------------------- INTENTS ----------------------
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
stage_announcement = {}

# ---------------------- HELPER FUNCTIONS ----------------------
async def apply_rank_nick(member: discord.Member):
    base_name = member.name

    role_priority = [
        ("💎 Admin", "💎"),
        ("Ⓜ️ Moderator", "Ⓜ️"),
        ("🔰Member", "🔰"),
    ]

    for role_name, symbol in role_priority:
        role = discord.utils.get(member.guild.roles, name=role_name)
        if role and role in member.roles:
            try:
                await member.edit(nick=f"{symbol} {base_name}")
            except discord.Forbidden:
                pass
            return

    # Visitor or no rank
    try:
        await member.edit(nick=None)
    except discord.Forbidden:
        pass

# ---------------------- EVENTS ----------------------
@client.event
async def on_voice_state_update(member, before, after):
    announce_channel = client.get_channel(ANNOUNCE_CHANNEL_ID)
    mod_role = discord.utils.get(member.guild.roles, name=MODERATOR_ROLE_NAME)

    if after.channel and after.channel.id == STAGE_CHANNEL_ID:
        if STAGE_CHANNEL_ID not in stage_announcement:
            mention = mod_role.mention if mod_role else ""
            msg = await announce_channel.send(
                f"{mention} 🎤 Stage **{after.channel.name}** has started!"
            )
            stage_announcement[STAGE_CHANNEL_ID] = msg

    if before.channel and before.channel.id == STAGE_CHANNEL_ID:
        if len(before.channel.members) == 0 and STAGE_CHANNEL_ID in stage_announcement:
            msg = stage_announcement.pop(STAGE_CHANNEL_ID)
            try:
                await msg.delete()
            except:
                pass

@client.event
async def on_member_join(member):
    unverified = discord.utils.get(member.guild.roles, name=UNVERIFIED_ROLE_NAME)
    if unverified:
        await member.add_roles(unverified)

    try:
        await member.send(
            f"Welcome to **{member.guild.name}**!\n"
            f"Use `/verify` in the rules channel to access the server."
        )
    except:
        pass

@client.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    role = discord.utils.get(message.guild.roles, name=UNVERIFIED_ROLE_NAME)
    if role and role in message.author.roles:
        try:
            await message.delete()
        except:
            pass

# ---------------------- SLASH COMMANDS ----------------------
# Schedule
@tree.command(name="schedule", description="Schedule an event")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def schedule(
    interaction: Interaction,
    role: Role,
    time: str,
    location: GuildChannel,
    title: str,
    message: str
):
    try:
        event_time = datetime.fromisoformat(time).replace(tzinfo=timezone.utc)
    except ValueError:
        await interaction.response.send_message(
            "❌ Invalid time. Use `YYYY-MM-DD HH:MM` UTC.",
            ephemeral=True
        )
        return

    embed = discord.Embed(title=title, description=message)
    embed.add_field(name="📍 Location", value=location.mention)
    embed.add_field(name="⏰ Time (UTC)", value=time)

    msg = await interaction.channel.send(content=role.mention, embed=embed)
    await interaction.response.send_message("✅ Event scheduled.", ephemeral=True)

    async def countdown():
        while True:
            delta = (event_time - datetime.now(timezone.utc)).total_seconds()
            if delta <= 0:
                await msg.edit(content=f"{role.mention} **{title} is live!** 🎉", embed=embed)
                break
            await asyncio.sleep(60)

    asyncio.create_task(countdown())

# Announce
@tree.command(name="announce", description="Send an announcement")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def announce(interaction: Interaction, channel: discord.TextChannel, message: str):
    mod_role = discord.utils.get(interaction.guild.roles, name=MODERATOR_ROLE_NAME)
    if mod_role not in interaction.user.roles:
        await interaction.response.send_message("❌ Mods only.", ephemeral=True)
        return

    formatted_message = message.replace("\\n", "\n")
    embed = discord.Embed(
        title="📢 Announcement",
        description=formatted_message,
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Announced by {interaction.user.display_name}")

    await channel.send(embed=embed)
    await interaction.response.send_message(f"✅ Announcement sent in {channel.mention}", ephemeral=True)

# Verify
@tree.command(name="verify", description="Verify yourself")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def verify(interaction: Interaction):
    await interaction.response.defer(ephemeral=True)

    visitor = discord.utils.get(interaction.guild.roles, name=UNVERIFIED_ROLE_NAME)

    if visitor not in interaction.user.roles:
        await interaction.followup.send("✅ Already verified.", ephemeral=True)
        return

    roles_to_assign = [
        "--------------------Rank--------------------",
        "🔰Member",
        "------------------XP Level------------------"
    ]

    if visitor:
        await interaction.user.remove_roles(visitor)

    for role_name in roles_to_assign:
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        if role:
            try:
                await interaction.user.add_roles(role)
            except discord.Forbidden:
                print("Missing permission for:", role_name)

    await interaction.followup.send("✅ Verified successfully!", ephemeral=True)

    try:
        await apply_rank_nick(interaction.user)
    except Exception as e:
        print("Nick error:", e)

    welcome = client.get_channel(WELCOME_CHANNEL_ID)
    if welcome:
        try:
            msg = await welcome.send(f"🎉 Welcome {interaction.user.mention}!")
            await asyncio.sleep(30)
            await msg.delete()
        except:
            pass

# Nick
@tree.command(name="nick", description="Change nickname")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.describe(
    member="Member to change nickname of",
    nickname="New nickname"
)
async def nick(interaction: Interaction, member: discord.Member, nickname: str):
    await interaction.response.defer(ephemeral=True)
    mod_role = discord.utils.get(interaction.guild.roles, name=MODERATOR_ROLE_NAME)
    if mod_role not in interaction.user.roles:
        await interaction.followup.send("❌ Mods only.", ephemeral=True)
        return

    bot_member = interaction.guild.me
    if member != interaction.guild.owner and member.top_role >= bot_member.top_role:
        await interaction.followup.send(
            "❌ I cannot change that user's nickname due to role hierarchy.",
            ephemeral=True
        )
        return

    try:
        await member.edit(nick=nickname)
        await interaction.followup.send(
            f"✅ Nickname for {member.mention} updated to **{nickname}**.",
            ephemeral=True
        )
    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I do not have permission to change this nickname.",
            ephemeral=True
        )
    except discord.HTTPException as e:
        await interaction.followup.send(f"❌ Discord error: `{e}`", ephemeral=True)

# Promote
@tree.command(name="promote", description="Give a role to a member (Moderators only)")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.describe(
    member="The member to promote",
    role="The role to give"
)
async def promote(interaction: Interaction, member: discord.Member, role: Role):
    mod_role = discord.utils.get(interaction.guild.roles, name=MODERATOR_ROLE_NAME)
    if mod_role not in interaction.user.roles:
        await interaction.response.send_message("❌ You must be a Moderator to use this command.", ephemeral=True)
        return

    bot_member = interaction.guild.me
    invoker = interaction.guild.get_member(interaction.user.id)

    if role >= bot_member.top_role:
        await interaction.response.send_message("❌ I cannot assign that role due to hierarchy.", ephemeral=True)
        return

    if role >= invoker.top_role and invoker != interaction.guild.owner:
        await interaction.response.send_message("❌ You cannot assign a role equal/higher than yours.", ephemeral=True)
        return

    if role in member.roles:
        await interaction.response.send_message(f"❌ {member.mention} already has **{role.name}**.", ephemeral=True)
        return

    await member.add_roles(role, reason=f"Promoted by {interaction.user}")
    await apply_rank_nick(member)

    log_channel = client.get_channel(PROMOTION_LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(f"📈 **Promotion**\n{member.mention} was promoted to **{role.name}**\n👤 By: {interaction.user.mention}")

    await interaction.response.send_message(f"✅ {member.mention} promoted to **{role.name}**.", ephemeral=True)

# Demote
@tree.command(name="demote", description="Demote a member and remove higher roles")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.describe(
    member="Member to demote",
    target_role="Role to demote down to"
)
async def demote(interaction: Interaction, member: discord.Member, target_role: Role):
    mod_role = discord.utils.get(interaction.guild.roles, name=MODERATOR_ROLE_NAME)
    if mod_role not in interaction.user.roles:
        await interaction.response.send_message("❌ You must be a Moderator to use this command.", ephemeral=True)
        return

    bot_member = interaction.guild.me

    if target_role >= bot_member.top_role:
        await interaction.response.send_message("❌ I cannot manage that role due to hierarchy.", ephemeral=True)
        return

    # Visitor reset
    if target_role.name == UNVERIFIED_ROLE_NAME:
        await member.edit(roles=[])
        visitor = discord.utils.get(member.guild.roles, name=UNVERIFIED_ROLE_NAME)
        if visitor:
            await member.add_roles(visitor)

        await apply_rank_nick(member)

        log_channel = client.get_channel(DEMOTION_LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"📉 **Demotion**\n{member.mention} was fully reset to **Visitor**\n👤 By: {interaction.user.mention}")

        await interaction.response.send_message(f"✅ {member.mention} reset to Visitor.", ephemeral=True)
        return

    roles_to_remove = [
        r for r in member.roles
        if r.position >= target_role.position and r.name != "@everyone"
    ]

    await member.remove_roles(*roles_to_remove)
    if target_role not in member.roles:
        await member.add_roles(target_role)

    await apply_rank_nick(member)

    log_channel = client.get_channel(DEMOTION_LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(f"📉 **Demotion**\n{member.mention} was demoted to **{target_role.name}**\n👤 By: {interaction.user.mention}")

    await interaction.response.send_message(f"✅ {member.mention} demoted to **{target_role.name}**.", ephemeral=True)

# ---------------------- READY ----------------------
@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"✅ Logged in as {client.user}")

# ---------------------- RUN BOT ----------------------
TOKEN = os.environ.get("DISCORD_TOKEN")
client.run(TOKEN)
