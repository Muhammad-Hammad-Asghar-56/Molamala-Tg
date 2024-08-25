import datetime
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty, InputPeerChannel, InputPeerUser
from telethon.errors.rpcerrorlist import PeerFloodError, UserPrivacyRestrictedError
from telethon.tl.functions.channels import InviteToChannelRequest, GetFullChannelRequest, GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsRecent
from telethon.errors.rpcerrorlist import ChatAdminRequiredError
import traceback
from time import sleep
import random

def read_text_file(filename):
    try:
        with open(filename, 'r') as file:
            line = file.readline().strip()  # Read the first line and strip any extra whitespace
            return line
    except FileNotFoundError:
        storeOutput(f"Error: File '{filename}' not found.")
        return None
    except Exception as e:
        storeOutput(f"Error reading file '{filename}': {e}")
        return None

def storeOutput(message:str):
    """Stores the given message in a text file.

    Args:
        message (str): The message to be stored.
        file_path (str, optional): The path to the output file. Defaults to "error.txt".
    """
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("error.txt", 'a', encoding='utf-8') as file:
            file.write(f"{timestamp}   : {message} \n")
    except IOError as e:
        storeOutput(f"Error writing to file: {e}")


api_id = 21578909
api_hash = 'bc7aa963f8f7979344c9ad4aa10d09b5'
phone = read_text_file("phoneNum.txt")
client = TelegramClient(phone, api_id, api_hash)

def is_number(value):
    return isinstance(value, (int, float))

def read_Channels_file(filename):
    try:
        with open(filename, 'r') as file:
            line = file.readlines()
            fromChannel = line[0].split("/")[-1].removesuffix("\n")
            toChannel = line[1].split("/")[-1]
            return fromChannel,toChannel
    except FileNotFoundError:
        storeOutput(f"Error: File '{filename}' not found.")
        return None
    except Exception as e:
        storeOutput(f"Error reading file '{filename}': {e}")
        return None

def reconnect_client():
    client.disconnect()
    sleep(5)  # Wait for a while before reconnecting
    client.connect()
    if not client.is_user_authorized():
        client.send_code_request(phone)
        client.sign_in(phone, input('Enter the code: '))

def get_Group_and_Participant(client, channel_username):
    try:
        entity = client.get_entity(channel_username)
        full_channel = client(GetFullChannelRequest(entity))
        channel_id = full_channel.full_chat.id
        about = full_channel.full_chat.about
        participants_count = full_channel.full_chat.participants_count
        
        # print(f"Channel ID: {channel_id}")
        # print(f"About: {about}")
        # print(f"Participants Count: {participants_count}")
        
        participants = client(GetParticipantsRequest(
            channel=entity,
            filter=ChannelParticipantsRecent(),
            offset=0,
            limit=200,
            hash=0
        ))
        
        participant_list = [user.username if user.username else user.id for user in participants.users]
        
        # print(f"Participants: {participant_list}")
    except ChatAdminRequiredError:
        # print("Error: Admin privileges are required to access participants. Ensure you are an admin in the channel.")
        storeOutput("Error: Admin privileges are required to access participants. Ensure you are an admin in the channel.")
        return None, []
    except Exception as e:
        storeOutput(f"An unexpected error occurred: {e}")
        return None, []
    return channel_id, participant_list

client.connect()

if not client.is_user_authorized():
    client.send_code_request(phone)
    client.sign_in(phone, input('Enter the code: '))

fromChannel,targetChannelName = read_Channels_file("channels.txt")
_, users = get_Group_and_Participant(client, fromChannel)

chats = []
last_date = None
chunk_size = 200
groups = []

result = client(GetDialogsRequest(
    offset_date=last_date,
    offset_id=0,
    offset_peer=InputPeerEmpty(),
    limit=chunk_size,
    hash=0
))
chats.extend(result.chats)

for chat in chats:
    try:
        if chat.megagroup:
            groups.append(chat)
    except:
        continue

# i = 0

target_group = None
for group in groups:
    # print(f"{i} - {group.title} - {group.username}")
    if(group.username == targetChannelName):
        target_group=group
    # i += 1

if(target_group==None):
    storeOutput(f"Such group with username {targetChannelName} is not in the list")
    exit()
target_group_entity = InputPeerChannel(target_group.id, target_group.access_hash)

n = 0
max_peer_flood_errors = 5
peer_flood_error_count = 0

for user in users[0:]:
    n += 1
    if n % 50 == 0:
        sleep(900)
    
    retry_attempts = 1
    attempt = 0

    while attempt < retry_attempts:
        try:
            user_to_add = None
            if is_number(user):
                break
            elif "bot" not in user.lower():
                user_to_add = client.get_input_entity(user)
            else:
                break  # Skip this user

            storeOutput(f"Adding {user}")
            client(InviteToChannelRequest(target_group_entity, [user_to_add]))
            storeOutput("Waiting for 60-180 Seconds...")
            sleep(random.randrange(60, 180))
            break 

        except PeerFloodError:
            peer_flood_error_count += 1
            attempt += 1
            storeOutput(f"PeerFloodError encountered. Attempt {attempt} of {retry_attempts}. Retrying in 15 minutes...")
            client.disconnect()
            sleep(15*60)
            reconnect_client()
            if peer_flood_error_count >= max_peer_flood_errors:
                storeOutput("Too many PeerFloodErrors. Reconnecting client...")
                reconnect_client()
                peer_flood_error_count = 0  # Reset the count after reconnecting

        except UserPrivacyRestrictedError:
            storeOutput("The user's privacy settings do not allow you to do this. Skipping.")
            break  # Skip this user

        except Exception as e:
            traceback.print_exc()
            storeOutput(f"Unexpected Error: {e}. Skipping this user.")
            break  # Skip this user if an unexpected error occurs
