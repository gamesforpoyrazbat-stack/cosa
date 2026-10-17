import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.bans = True
intents.moderation = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= YETKİLENDİRME VE AYARLAR =================
OWNER_IDS = [1506368638897356941, 1547400739775844356]  # Kendi ve arkadaşının ID'sini yaz
LOG_CHANNELS = {}

async def send_log(guild, title, description, executor=None, color=discord.Color.red()):
    if guild.id in LOG_CHANNELS:
        channel_id = LOG_CHANNELS[guild.id]
        channel = guild.get_channel(channel_id)
        if channel:
            embed = discord.Embed(title=f"🛡️ Güvenlik Koruması: {title}", description=description, color=color)
            if executor:
                embed.add_field(name="Sorumlu / Eylemi Yapan", value=f"{executor.mention} (`{executor.id}`)", inline=False)
            embed.set_footer(text=f"{guild.name} • Güvenlik Logu", icon_url=guild.icon.url if guild.icon else None)
            embed.timestamp = discord.utils.utcnow()
            try:
                await channel.send(embed=embed)
            except Exception:
                pass

async def get_audit_executor(guild, action_type):
    try:
        await asyncio.sleep(0.3)
        async for entry in guild.audit_logs(action=action_type, limit=1):
            if entry.user.id != bot.user.id:
                return entry.user
    except Exception:
        pass
    return None

@bot.event
async def on_ready():
    try:
        # Slash komutların Discord'a senkronize edilmesi
        synced = await bot.tree.sync()
        print(f"{len(synced)} adet Slash komutu senkronize edildi.")
    except Exception as e:
        print(e)
    print(f"{bot.user.name} aktif!")

# ================= SLASH (/) KOMUTLARI =================

@bot.tree.command(name="logayarla", description="Güvenlik log kanalını belirler.")
@app_commands.describe(channel="Log gönderilecek metin kanalı")
async def log_ayarla(interaction: discord.Interaction, channel: discord.TextChannel):
    if interaction.user.id not in OWNER_IDS:
        await interaction.response.send_message("❌ Bu komutu kullanmaya yetkin yok!", ephemeral=True)
        return
    LOG_CHANNELS[interaction.guild.id] = channel.id
    await interaction.response.send_message(f"✅ Güvenlik log kanalı başarıyla {channel.mention} olarak ayarlandı.", ephemeral=True)

@bot.tree.command(name="logsifirla", description="Log kanalını sıfırlar.")
async def log_sifirla(interaction: discord.Interaction):
    if interaction.user.id not in OWNER_IDS:
        await interaction.response.send_message("❌ Bu komutu kullanmaya yetkin yok!", ephemeral=True)
        return
    if interaction.guild.id in LOG_CHANNELS:
        del LOG_CHANNELS[interaction.guild.id]
        await interaction.response.send_message("🔒 Log kanalı sıfırlandı.", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ Zaten ayarlanmış bir log kanalı yok.", ephemeral=True)

@bot.tree.command(name="yetkiver", description="Belirtilen kullanıcıya bot yetkisi verir.")
@app_commands.describe(member="Yetki verilecek kullanıcı")
async def yetki_ver(interaction: discord.Interaction, member: discord.Member):
    if interaction.user.id not in OWNER_IDS:
        await interaction.response.send_message("❌ Bu komutu kullanmaya yetkin yok!", ephemeral=True)
        return
    if member.id in OWNER_IDS:
        await interaction.response.send_message(f"⚠️ **{member.name}** zaten yetkili listesinde!", ephemeral=True)
        return
    OWNER_IDS.append(member.id)
    await interaction.response.send_message(f"✅ Başarıyla **{member.name}** adlı kullanıcıya bot yönetim yetkisi verildi.", ephemeral=True)

@bot.tree.command(name="yetkial", description="Kullanıcının bot yetkisini alır.")
@app_commands.describe(member="Yetkisi alınacak kullanıcı")
async def yetki_al(interaction: discord.Interaction, member: discord.Member):
    if interaction.user.id not in OWNER_IDS:
        await interaction.response.send_message("❌ Bu komutu kullanmaya yetkin yok!", ephemeral=True)
        return
    if len(OWNER_IDS) <= 1:
        await interaction.response.send_message("❌ Son yetkiliyi alamazsın!", ephemeral=True)
        return
    if member.id in OWNER_IDS:
        OWNER_IDS.remove(member.id)
        await interaction.response.send_message(f"🔒 **{member.name}** adlı kullanıcının bot yetkisi alındı.", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ **{member.name}** yetkili listesinde değil.", ephemeral=True)

# ================= KORUMALAR =================

@bot.event
async def on_guild_role_update(before, after):
    executor = await get_audit_executor(before.guild, discord.AuditLogAction.role_update)
    if executor and executor.id in OWNER_IDS:
        return
    if before.name != after.name:
        await after.edit(name=before.name, reason="Güvenlik Koruması")
        await send_log(before.guild, "Rol Adı Değişikliği Engellendi", f"**Rol:** `{before.name}` eski haline çevrildi.", executor=executor)

@bot.event
async def on_guild_role_delete(role):
    executor = await get_audit_executor(role.guild, discord.AuditLogAction.role_delete)
    if executor and executor.id in OWNER_IDS:
        return
    guild = role.guild
    await guild.create_role(name=role.name, permissions=role.permissions, color=role.color, hoist=role.hoist, mentionable=role.mentionable, reason="Güvenlik Koruması")
    await send_log(guild, "Rol Silme Engellendi", f"**Rol:** `{role.name}` tekrar oluşturuldu.", executor=executor)

@bot.event
async def on_guild_update(before, after):
    executor = await get_audit_executor(before, discord.AuditLogAction.guild_update)
    if executor and executor.id in OWNER_IDS:
        return
    if before.name != after.name:
        await after.edit(name=before.name, reason="Güvenlik Koruması")
        await send_log(before, "Sunucu Adı Değişikliği Engellendi", f"Eski ada geri döndürüldü.", executor=executor)
    if before.description != after.description:
        await after.edit(description=before.description, reason="Güvenlik Koruması")
        await send_log(before, "Sunucu Açıklaması Değişikliği Engellendi", f"Orijinal haline döndürüldü.", executor=executor)

@bot.event
async def on_guild_channel_update(before, after):
    executor = await get_audit_executor(before.guild, discord.AuditLogAction.channel_update)
    if executor and executor.id in OWNER_IDS:
        return
    if before.name != after.name:
        await after.edit(name=before.name, reason="Güvenlik Koruması")
        await send_log(before.guild, "Kanal Adı Değişikliği Engellendi", f"{after.mention} eski adına çevrildi.", executor=executor)

@bot.event
async def on_guild_channel_delete(channel):
    executor = await get_audit_executor(channel.guild, discord.AuditLogAction.channel_delete)
    if executor and executor.id in OWNER_IDS:
        return
    guild = channel.guild
    if isinstance(channel, discord.CategoryChannel):
        await guild.create_category(name=channel.name, position=channel.position, overwrites=channel.overwrites)
        await send_log(guild, "Kategori Silme Engellendi", f"`{channel.name}` yeniden açıldı.", executor=executor)
    elif isinstance(channel, discord.TextChannel):
        await guild.create_text_channel(name=channel.name, category=channel.category, position=channel.position, overwrites=channel.overwrites, topic=channel.topic, slowmode_delay=channel.slowmode_delay)
        await send_log(guild, "Metin Kanalı Silme Engellendi", f"`{channel.name}` yeniden oluşturuldu.", executor=executor)
    elif isinstance(channel, discord.VoiceChannel):
        await guild.create_voice_channel(name=channel.name, category=channel.category, position=channel.position, overwrites=channel.overwrites, bitrate=channel.bitrate, user_limit=channel.user_limit)
        await send_log(guild, "Ses Kanalı Silme Engellendi", f"`{channel.name}` yeniden oluşturuldu.", executor=executor)

@bot.event
async def on_member_unban(guild, user):
    executor = await get_audit_executor(guild, discord.AuditLogAction.ban_remove)
    if executor and executor.id in OWNER_IDS:
        return
    try:
        await guild.ban(user, reason="Güvenlik Koruması")
        await send_log(guild, "Yasak Kaldırma Engellendi", f"{user.mention} tekrar banlandı.", executor=executor)
    except Exception:
        pass

@bot.event
async def on_member_join(member):
    if member.bot:
        executor = await get_audit_executor(member.guild, discord.AuditLogAction.bot_add)
        if executor and executor.id in OWNER_IDS:
            return
        try:
            await member.kick(reason="Güvenlik Koruması")
            await send_log(member.guild, "Yetkisiz Bot Ekleme Engellendi", f"{member.mention} sunucudan atıldı.", executor=executor)
        except Exception:
            pass

keep_alive()
bot.run(os.getenv("TOKEN"))