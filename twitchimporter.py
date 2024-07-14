import requests
import os
import glob
from moviepy.editor import VideoFileClip, concatenate_videoclips, TextClip, ImageClip, CompositeVideoClip
import time
from datetime import datetime, timedelta
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from googleapiclient.http import MediaFileUpload
import pickle
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
import re
# from pytube import YouTube
import yt_dlp


client_secrets_file = 'client_secret.json'
credentials_file = 'youtube_credentials.pickle'

client_id = str(os.environ['TWITCH_CLIENT_ID'])
client_secret = str(os.environ['TWITCH_CLIENT_SECRET'])
game_name = str(os.environ['GAME_NAME'])

scopes = ["https://www.googleapis.com/auth/youtube.upload", 'https://www.googleapis.com/auth/youtube.readonly']

def get_oauth_token(client_id, client_secret):
    url = 'https://id.twitch.tv/oauth2/token'
    params = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials'
    }
    response = requests.post(url, params=params)
    response.raise_for_status()
    return response.json()['access_token']

def get_game_id(game_name, client_id, oauth_token):
    url = 'https://api.twitch.tv/helix/games'
    headers = {
        'Client-ID': client_id,
        'Authorization': f'Bearer {oauth_token}'
    }
    params = {
        'name': game_name
    }
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    games = response.json()['data']
    if games:
        return games[0]['id']
    else:
        raise ValueError(f'Game "{game_name}" not found')

def get_top_clips(game_id, client_id, oauth_token):
    date_now = datetime.utcnow()
    previous = datetime.utcnow() - timedelta(hours = 12)
    
    url = 'https://api.twitch.tv/helix/clips'
    headers = {
        'Client-ID': client_id,
        'Authorization': f'Bearer {oauth_token}'
    }
    params = {
        'ended_at' : date_now.isoformat("T") + "Z",
        'first': 20,
        'game_id': game_id,
        'started_at' : previous.isoformat("T") + "Z"    
    }
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()['data']

def download_twitch_clip(clip_url, broadcaster_name, output_dir='clips'):
    # Get the clip slug from the URL
    clip_slug = clip_url.split('/')[-1]

    # Step 1: Fetch clip metadata to get the actual video URL
    api_url = f'https://api.twitch.tv/helix/clips?id={clip_slug}'
    oauth_token = get_oauth_token(client_id, client_secret)

    headers = {
        'Client-ID': client_id,
        'Authorization': f'Bearer {oauth_token}'
    }
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()
    clip_data = response.json()

    # Get the URL of the video file
    try:
        video_url = clip_data['data'][0]['thumbnail_url'].split('-preview-')[0] + '.mp4'
    except (IndexError, KeyError):
        raise ValueError('Invalid clip URL or clip not found.')

    # Step 2: Download the video
    response = requests.get(video_url, stream=True)
    response.raise_for_status()

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Save the video file
    output_path = os.path.join(output_dir, f'{broadcaster_name}.mp4')
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f'Clip downloaded successfully: {output_path}')

def get_oauth_token(client_id, client_secret):
    url = 'https://id.twitch.tv/oauth2/token'
    params = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials'
    }
    response = requests.post(url, params=params)
    response.raise_for_status()
    return response.json()['access_token']

def draw_text_with_outline(draw, position, text, font, outline_color, fill_color):
    # Position offsets to create the outline
    x, y = position
    offsets = [-1, 0, 1]
    
    # Draw the outline
    for offset_x in offsets:
        for offset_y in offsets:
            if offset_x != 0 or offset_y != 0:
                draw.text((x + offset_x, y + offset_y), text, font=font, fill=outline_color)
    
    # Draw the text on top
    draw.text((x, y), text, font=font, fill=fill_color)

def text_to_transparent_image(text, font_path, font_size, output_path):
    font = ImageFont.truetype(font_path, font_size)
    
    text_width, text_height = 200000, 221 #font.getsize(text)
    
    outline_width = 2  # width of the outline

    image = Image.new('RGBA', (text_width + 2*outline_width, text_height + 2*outline_width), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    draw_text_with_outline(draw, (outline_width, outline_width), text, font, outline_color=(0, 0, 0, 255), fill_color=(255, 255, 255, 255))
    image.save(output_path, 'PNG')

def concatenate_clips(clips):
    target_resolution = (1920, 1080)  # Specify the target resolution

    outro = VideoFileClip('Outro.mp4')
    resized_outro = outro.resize(newsize=target_resolution)
    clips.append(resized_outro)
    
    final_clip = concatenate_videoclips(clips)
    final_clip.write_videofile('final_video.mp4', codec='libx264', threads = 16, fps=60)

def get_authenticated_service():
    credentials = None

    # Check if credentials are already stored
    if os.path.exists(credentials_file):
        with open(credentials_file, 'rb') as token:
            credentials = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not credentials:
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
        credentials = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(credentials_file, 'wb') as token:
            pickle.dump(credentials, token)
    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=credentials)

    request = youtube.channels().list(
        part="snippet,contentDetails,statistics",
        id= str(os.environ['CHANNEL_ID'])
    )
    response = request.execute()

    return youtube, response["items"][0]["statistics"]["videoCount"]

def upload_video(youtube, video_file, title, description, tags, category_id, privacy_status):
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id
        },
        "status": {
            "selfDeclaredMadeForKids": False,
            "madeForKids": False,
            "privacyStatus": privacy_status
        }
    }
    
    media_body = MediaFileUpload(video_file, chunksize=-1, resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media_body
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploaded {int(status.progress() * 100)}%")

    print("Upload Complete!")
    print("Video URL: https://www.youtube.com/watch?v=" + response['id'])

def format_clips(broadcaster_name, language, file_name):
    target_resolution = (1920, 1080)  # Specify the target resolution
    text = u'{0}'.format(broadcaster_name)
    if language == 'ja':
        font_path = "fonts/Noto_Sans_JP/static/NotoSansJP-Black.ttf"  
    elif language == 'ko':
        font_path = "fonts/Noto_Sans_KR/static/NotoSansKR-Black.ttf"
    elif language == 'zh':
        font_path = "fonts/Noto_Sans_SC/static/NotoSansSC-Black.ttf"
    else:
        font_path = "fonts/Noto_Sans/static/NotoSans-Black.ttf"

    font_size = 200
    output_path = "output.png"

    text_to_transparent_image(text, font_path, font_size, output_path)
    
    image1 = Image.open('images-removebg-preview.png').convert("RGBA")
    image2 = Image.open(output_path).convert("RGBA")

    new_width = image1.width + image2.width
    new_height = max(image1.height, image2.height)
    new_image = Image.new("RGBA", (new_width, new_height), (255, 255, 255, 0))
    
    new_image.paste(image1, (0, 0))
    new_image.paste(image2, (image1.width, 0))
    new_image.save('combined.png', 'PNG')
    clip = VideoFileClip('clips/' + file_name + '.mp4')
    logo = (ImageClip('combined.png',transparent=True)
    .set_duration(5)
    .resize(height=50)
    .margin(left=8, top=8, opacity=0)
    .set_pos(("left","top")))
    final = CompositeVideoClip([clip, logo])
    final.write_videofile("test.mp4")
    resized_clip = final.resize(newsize=target_resolution)
    return resized_clip

def download_video(url, output_path='.'):
    ydl_opts = {
        'format': 'best',
        'outtmpl': f'{output_path}/%(title)s.%(ext)s',
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def main():
    try:
        # Downloading Outro from unlisted youtube video for outro
        # No need for Git LFS
        video_url = 'https://www.youtube.com/watch?v={0}'.format(str(os.environ['OUTRO_ID']))
        download_video(video_url, '')
        
        # Oauth Token needed for grabbing twitch clips
        oauth_token = get_oauth_token(client_id, client_secret)
        game_id = get_game_id(game_name, client_id, oauth_token)
        clips = get_top_clips(game_id, client_id, oauth_token)

        # Grab broadcasters to use as description for video's chapters (must be greater than 10 seconds in duration)
        broadcasters = []
        duration_video = []
        duration = 0
        formatted_clips = []
        
        for idx, clip in enumerate(clips):
            if (clip['duration'] >= 10):
                # Download clips, Edit them, and add them to our formatted_clips list
                download_twitch_clip(clip['url'], str(idx) + '_' + clip['broadcaster_name'])
                formatted_clips.append(format_clips(clip['broadcaster_name'], clip['language'], str(idx) + '_' + clip['broadcaster_name']))
                broadcasters.append(clip['broadcaster_name'])
                minutes, seconds = divmod(duration, 60)
                duration_video.append("%02d:%02d" % (minutes, seconds))
                duration = duration + clip['duration']
        
        # Put all of our clips together, and then upload
        concatenate_clips(formatted_clips)
        
        youtube, video_count = get_authenticated_service()
        formatted_game_name = ''

        if game_name == 'league of legends':
            formatted_game_name = 'LoL'
        elif game_name == 'valorant':
            formatted_game_name = 'Valorant'
        
        video_file = "final_video.mp4"
        title = "{0} Bi-Daily Twitch Highlights #{1}".format(formatted_game_name, str(video_count))
        description = "{0} \nFeatured Streamers: \n{1}".format(str(os.environ['YOUTUBE_DESCRIPTION']), "\n".join("{} {}".format(x, y) for x,y in zip(duration_video, broadcasters)))
        tags = broadcasters
        category_id = "20"  # Category ID for YouTube video categories
        privacy_status = "public"
        
        upload_video(youtube, video_file, title, description, tags, category_id, privacy_status)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
