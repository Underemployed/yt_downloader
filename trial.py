from pytube import Playlist, YouTube
import os
import pandas as pd
import concurrent.futures
import string
from googletrans import Translator
from pytube.exceptions import VideoUnavailable, RegexMatchError


def contains_only_english(text):
    for char in text:
        if not ("a" <= char.lower() <= "z" or char.isspace()):
            return False
    return True


def translate_to_english(title):
    if contains_only_english(title):
        return title
    else:
        translator = Translator()
        translated_title = translator.translate(title, dest="en").text
        return translated_title


def sanitize_filename(title):
    valid_chars = "-_.() & %s%s%s" % (
        string.ascii_letters,
        string.digits,
        string.printable,
    )
    title = title.replace("&", "and").replace('"', "'").replace("|" or "\\" or "/", "-")
    translated_title = translate_to_english(title)

    sanitized_title = "".join(
        (
            char
            if char in valid_chars and char not in ["/", "?", "\\", "|", '"', ":", "?"]
            else "_"
        )
        for char in translated_title
    )
    sanitized_title = sanitized_title.strip("_")

    return sanitized_title


def download_video(video_url, folder_path, failed_downloads):
    try:
        video = YouTube(video_url)
        video_title = video.title
        channel_name = video.author

        sanitized_translated_title = sanitize_filename(video_title)
        sanitized_channel_name = sanitize_filename(channel_name)

        if video:
            video_stream = (
                video.streams.get_highest_resolution()
            )  # Get the video stream here

            filename = f"{sanitized_translated_title} - {sanitized_channel_name}.{video_stream.subtype}"

            if not os.path.exists(folder_path):
                os.makedirs(folder_path)

            video_stream.download(folder_path, filename=filename)
            print(filename)

            return True

    except (VideoUnavailable, RegexMatchError) as e:
        title = "Unknown Title"
        translated_title = ""
        if video:
            title = video.title
            translated_title = translate_to_english(title)
            filename = f"{sanitize_filename(translated_title)} - {channel_name}.{video_stream.subtype}"
            video_stream.download(folder_path, filename=filename)

        failed_downloads.append(
            {
                "Title": title,
                "Translated Title": translated_title,
                "Link": video_url,
                "Error": str(e),
            }
        )

        error_file = os.path.join(folder_path, "failed_downloads.txt")
        with open(error_file, "a", encoding="utf-8") as file:
            file.write(f"Title: {title}\n")
            file.write(f"Translated Title: {translated_title}\n")
            file.write(f"Link: {video_url}\n")
            file.write(f"Error: {str(e)}\n")
            file.write("\n")

        return False


def is_playlist_url(url):
    return "list=" in url


# Get the video or playlist URL
input_url = input("Enter the YouTube URL (video or playlist): ")

# Check if the input URL is a playlist or video
if is_playlist_url(input_url):
    try:
        playlist = Playlist(input_url)
        is_playlist = True
    except:
        is_playlist = False
else:
    is_playlist = False


# Function to download videos in parallel using multi-threading
def download_videos_parallel(video_urls, folder_path, failed_downloads):
    # Set the maximum number of threads you want to use for downloading videos
    max_threads = 6  #  adjust this number based on your system and network capacity

    with concurrent.futures.ThreadPoolExecutor(max_threads) as executor:
        future_to_url = {
            executor.submit(download_video, url, folder_path, failed_downloads): url
            for url in video_urls
        }
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                download_result = future.result()
                if not download_result:
                    failed_downloads.append({"Title": "Unknown Title", "Link": url})
            except Exception as exc:
                print(f"Download for {url} generated an exception: {exc}")


# Perform the download based on whether it's a playlist or individual video
failed_downloads = []
if is_playlist:
    # Create a folder for the playlist
    playlist_folder = sanitize_filename(playlist.title)
    if not os.path.exists(playlist_folder):
        os.makedirs(playlist_folder)
    # Download videos from the playlist
    download_videos_parallel(playlist.video_urls, playlist_folder, failed_downloads)

else:
    # Create a folder for the video
    video_folder = "Favourites"
    if not os.path.exists(video_folder):
        os.makedirs(video_folder)

    # Download the individual video
    download_video(input_url, video_folder, failed_downloads)

# Failed download list
failed_downloads_df = pd.DataFrame(failed_downloads)
if not failed_downloads_df.empty:
    output_file = os.path.join(
        playlist_folder if is_playlist else video_folder, "failed_downloads.txt"
    )
    with open(output_file, "w", encoding="utf-8") as file:
        file.write("Failed Downloads:\n")
        file.write(failed_downloads_df.to_string(index=False))
    print(f"Failed downloads written to: {output_file}")

print("Download process completed.")
