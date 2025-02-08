import discord
from discord.ext import commands, tasks
import re
import time
import os 
import webserver

intents = discord.Intents.default()
intents.message_content = True  # Enable access to message content
bot = commands.Bot(command_prefix="!", intents=intents)

TARGET_USER_ID = 1326576731821309982  # Replace with the user's ID (spydeybbot)
SOURCE_CHANNEL_ID = 1326576615538429996  # Replace with the channel to read messages from
DESTINATION_CHANNEL_ID = 1337446260248150036  # Replace with the channel to send messages to
YOUR_BOT_TOKEN = os.environ['discordkey'] # Replace with your bot's token

user_messages = {}
allowed_mentions = discord.AllowedMentions(users=False)
latest_sent_message = None


async def send_new_message(channel_id, user_id, timestamp):
    channel = bot.get_channel(channel_id)
    # Additional actions here if needed


async def send_message_list(channel_id):
    global latest_sent_message
    channel = bot.get_channel(channel_id)
    if not channel:
        return

    message_list = []
    total_lines, non_offline_count = 0, 0

    if user_messages:
        sorted_messages = sorted(user_messages.values(), key=lambda x: x["timestamp"], reverse=True)
        current_time = int(time.time())

        for data in sorted_messages:
            total_lines += 1
            timestamp = data["timestamp"]
            timestamp_unix = int(timestamp.split(":")[1])

            # Determine whether the message is offline or not
            is_offline = current_time - timestamp_unix > 1890
            status = "OFFLINE" if is_offline else ""
            message_list.append(
                f"• {status} <@{data['content']}> {timestamp} **({data['second_line_numbers']} instances)**"
            )
            if not is_offline:
                non_offline_count += 1

        # Join the messages and update the latest sent message
        message_content = f"Latest heart beats: {non_offline_count} active roller(s)\n" + "\n".join(message_list)

        if latest_sent_message:
            await latest_sent_message.edit(content=message_content)
        else:
            latest_sent_message = await channel.send(message_content, allowed_mentions=allowed_mentions)
    else:
        # If no valid messages, update the message to show no valid messages
        if latest_sent_message:
            await latest_sent_message.edit(content="No valid messages stored yet.")
        else:
            latest_sent_message = await channel.send("No valid messages stored yet.")


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    if not send_message_list_task.is_running():
        send_message_list_task.start()


@bot.event
async def on_message(message):
    if message.author.id == TARGET_USER_ID and message.channel.id == SOURCE_CHANNEL_ID:
        if message.content.startswith("<") and "\n" in message.content:
            lines = message.content.split("\n")
            first_line = lines[0].strip()
            second_line = lines[1].strip() if len(lines) > 1 else ""  # Get the second line

            if "@" in first_line:
                return  # Ignore the message if it contains '@' after '<'

            if ">" in first_line:
                user_id = first_line.split("<")[1].split(">")[0].strip()
                unix_timestamp = int(message.created_at.timestamp())
                timestamp_formatted = f"<t:{unix_timestamp}:R>"

                # Count the number of separate numbers in the second line
                second_line_numbers = len(re.findall(r'\d+', second_line))

                # Extract digits from the first line (Main line) and format with commas
                main_line_match = re.search(r'.*Main.*', message.content, re.MULTILINE)
                digit_list = f"{int(''.join(re.findall(r'\d+', main_line_match.group()))):,}" if main_line_match else "0"

                # Store or update message data with digits and the count of numbers in the second line
                for msg_id, data in user_messages.items():
                    if data["content"] == user_id:
                        data.update({"timestamp": timestamp_formatted, "digits": digit_list, "second_line_numbers": second_line_numbers})
                        break
                else:
                    user_messages[message.id] = {
                        "content": user_id,
                        "digits": digit_list,
                        "timestamp": timestamp_formatted,
                        "second_line_numbers": second_line_numbers
                    }

                await send_new_message(DESTINATION_CHANNEL_ID, user_id, timestamp_formatted)

    await bot.process_commands(message)

webserver.keep_alive()

@tasks.loop(minutes=2)
async def send_message_list_task():
    await send_message_list(DESTINATION_CHANNEL_ID)
    


bot.run(YOUR_BOT_TOKEN)
