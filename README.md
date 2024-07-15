<h1>Twitch Clips To Youtube</h1>

<h2>Summary:</h2>

An easy single script for:
1. Grabbing the top twitch clips of a specific game (changes to the "first" paramter in the get_top_clips function will result in how many clips you obtain).
    
    It is currently configured to upload twice a day at 12 hour intervals with 20 clips per upload, set yours accordingly.
2. Editing the clips by placing a twitch logo followed by the twitch channel on each clip using the library moviepy.
3. Concatenating the clips together, downloading the outro from an unlisted youtube link (to bypass GitHub LFS costs).
4. Uploading to Youtube with the description auto-filling with timestamps of the twitch creators downloaded.
5. GitHub Actions workflow to run through twice a day.

<h2>Prerequisites:</h2>

1. Google Cloud account to access Youtube Data V3 (Uploading youtube videos via API)

   [https://developers.google.com/youtube/v3](https://developers.google.com/youtube/v3) 

     
3. Twitch API to grab the clips:
   
     [https://dev.twitch.tv/docs/api/clips/](https://dev.twitch.tv/docs/api/)

4. Requirements installation via:
   
    ```pip install -r requirements.txt```

<h2>Steps:</h2>

🔒SECURITY NOTE: DO NOT PUSH ANY OF THESE TO A PUBLIC REPOSITORY🔒

  - client_secret.json

  - youtube_credentials.pickle
  
  - twitch API credentials 

1. Grab your client secrets JSON from your google cloud account and make sure that you have Youtube Data V3 enabled:
   ![image](https://github.com/user-attachments/assets/413dadf7-b600-484f-acc9-115c1dec5cc9)
2. Store your youtube credentials by utilizing the get_authenticated_service function:

   ```
   def main():
     get_authenticated_service()
   ```
   
   You will be asked to sign in once, and then after, your credentials will now be stored as a 'youtube_credentials.pickle' file in your file system.
3. Base64 encode your client_secret.json and youtube_credentials.pickle:
    ```
    import base64
      
    with open('youtube_credentials.pickle', 'rb') as f:
      encoded_credentials = base64.b64encode(f.read()).decode()
    ```
    ```
    import base64
      
    with open('client_secret.json', 'rb') as f:
      encoded_credentials = base64.b64encode(f.read()).decode()
    ```
Take both outputs and store each of them as a github secret.

4. Grab your twitch API credentials:
![image](https://github.com/user-attachments/assets/2e672c32-57ed-4bd8-b97d-7441efb16bdc)

5. Store them in your Github Secrets as TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET respectively.
6. Now create a Github Actions workflow or use any of mine as a template:

   Note: If using my workflow, change both of these to the GitHub Secret names you specified in step 3:

   - ${{ secrets.LEAGUE_OF_LEGENDS_YOUTUBE_CHANNEL_PICKLE }}

   - ${{ secrets.GOOGLE_CLIENT_SECRET_JSON }}
   
   
  ```
  - name: Decode and save Google client secret
      env:
        GOOGLE_CLIENT_SECRET: ${{ secrets.GOOGLE_CLIENT_SECRET_JSON }}
      run: |
        echo "$GOOGLE_CLIENT_SECRET_JSON" | base64 --decode > client_secret.json
  - name: Decode and save YouTube credentials
      env:
        YOUTUBE_CREDENTIALS: ${{ secrets.LEAGUE_OF_LEGENDS_YOUTUBE_CHANNEL_PICKLE }}
      run: |
        echo "$YOUTUBE_CREDENTIALS" | base64 --decode > youtube_credentials.pickle
   ```
7. Finally make changes to these environment variables with your variables for channel ID.
```
- name: python run
      run: python twitchimporter.py
      env:
        TWITCH_CLIENT_ID: ${{ secrets.TWITCH_CLIENT_ID }}
        TWITCH_CLIENT_SECRET: ${{ secrets.TWITCH_CLIENT_SECRET }}
        GAME_NAME: "YOUR GAME NAME"
        YOUTUBE_DESCRIPTION: "YOUR DESCRIPTION FOR YOUR YOUTUBE VIDEO"
        CHANNEL_ID: "YOUR CHANNEL ID WHICH IS FOUND HERE https://www.youtube.com/account_advanced"
        OUTRO_ID: "YOUR UNLISTED OUTRO YOUTUBE VIDEO ID"
  ```
8. The workflow takes care of everything else, make sure you make changes to the cron schedule in the workflow so it will upload at the times that you want.



   
