from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from src import addresses

import urllib.parse as p
import csv
import re
import os
import pickle

SCOPES = addresses.SCOPES

# authenticate interaction with the YouTube API
def youtube_authenticate():
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    api_service_name = "youtube"
    api_version = "v3"
    client_secrets_file = "../config/credentials.json"
    creds = None
    # the file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    # if there are no (valid) credentials availablle, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
            creds = flow.run_local_server(port=0)
        # save the credentials for the next run
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return build(api_service_name, api_version, credentials=creds)

# Interaction with a YouTube channel information
def parse_channel_url(url):
    """
    This function takes channel `url` to check whether it includes a
    channel ID, user ID or channel name
    """
    path = p.urlparse(url).path
    id = path.split("/")[-1]
    if "/c/" in path:
        return "c", id
    elif "/channel/" in path:
        return "channel", id
    elif "/user/" in path:
        return "user", id

def get_channel_id_by_url(youtube, url):
    """
    Returns channel ID of a given `id` and `method`
    - `method` (str): can be 'c', 'channel', 'user'
    - `id` (str): if method is 'c', then `id` is display name
        if method is 'channel', then it's channel id
        if method is 'user', then it's username
    """
    # parse the channel URL
    method, id = parse_channel_url(url)
    if method == "channel":
        # if it's a channel ID, then just return it
        return id
    elif method == "user":
        # if it's a user ID, make a request to get the channel ID
        response = get_channel_details(youtube, forUsername=id)
        items = response.get("items")
        if items:
            channel_id = items[0].get("id")
            return channel_id
    elif method == "c":
        # if it's a channel name, search for the channel using the name
        # may be inaccurate
        response = search(youtube, q=id, maxResults=1)
        items = response.get("items")
        if items:
            channel_id = items[0]["snippet"]["channelId"]
            return channel_id
    raise Exception(f"Cannot find ID:{id} with {method} method")

def get_channel_videos(youtube, **kwargs):
    return youtube.search().list(
        **kwargs
    ).execute()


def get_channel_details(youtube, **kwargs):
    return youtube.channels().list(
        part="statistics,snippet,contentDetails",
        **kwargs
    ).execute()


# Function to get the channels stats
# It will also contain the upload playlist ID we can use to grab videos.
def get_channel_stats(youtube, channel_id):
    request = youtube.channels().list(
        part="snippet,contentDetails,statistics",
        id=channel_id
    )
    response = request.execute()

    return response['items']

# Interaction with YouTube Video

# This will get us a list of videos from a playlist.
# Note a page of results has a max value of 50 so we will
# need to loop over our results with a pageToken

def get_video_list(youtube, upload_id):
    video_list = []
    request = youtube.playlistItems().list(
        part="snippet,contentDetails",
        playlistId=upload_id,
        maxResults=50
    )
    next_page = True
    while next_page:
        response = request.execute()
        data = response['items']

        for video in data:
            video_id = video['contentDetails']['videoId']
            if video_id not in video_list:
                video_list.append(video_id)

        # Do we have more pages?
        if 'nextPageToken' in response.keys():
            next_page = True
            request = youtube.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=upload_id,
                pageToken=response['nextPageToken'],
                maxResults=50
            )
        else:
            next_page = False

    return video_list

def get_video_id_by_url(url):
    """
    Return the Video ID from the video `url`
    """
    # split URL parts
    parsed_url = p.urlparse(url)
    # get the video ID by parsing the query of the URL
    video_id = p.parse_qs(parsed_url.query).get("v")
    if video_id:
        return video_id[0]
    else:
        raise Exception(f"Wasn't able to parse video URL: {url}")


def get_video_details(youtube, **kwargs):
    return youtube.videos().list(
        part="snippet,contentDetails,statistics",
        **kwargs
    ).execute()

def extract_video_infos(youtube,video_list):
    stats_list = []

    # Can only get 50 videos at a time.
    for i in range(0, len(video_list), 50):
        request = youtube.videos().list(
            part="snippet,contentDetails,statistics",
            id=video_list[i:i + 50]
        )

        data = request.execute()
        for video in data['items']:
            snippet = video["snippet"]
            # get infos from the snippet
            channel_title = snippet["channelTitle"]
            # get stats infos
            title = video['snippet']['title']
            published = video['snippet']['publishedAt']
            description = video['snippet']['description']
            tag_count = len(video['snippet']['tags'])
            #tag_count = 0
            view_count = video['statistics'].get('viewCount', 0)
            viewer_percentage = video['statistics'].get('viewerPercentage', 0)
            estimated_min_watched = video['statistics'].get('estimatedMinutesWatched', 0)
            avg_view_duration = video['statistics'].get('averageViewDuration', 0)
            avg_view_percentage = video['statistics'].get('averageViewPercentage', 0)

            like_count = video['statistics'].get('likeCount', 0)
            dislike_count = video['statistics'].get('dislikeCount', 0)
            share_count = video['statistics'].get('shares', 0)
            comment_count = video['statistics'].get('commentCount', 0)
            content_details = video["contentDetails"]
            duration = content_details["duration"]
            # duration in the form of something like 'PT5H50M15S'
            # parsing it to be something like '5:50:15'
            parsed_duration = re.search(f"PT(\d+H)?(\d+M)?(\d+S)", duration)
            duration_str = ""
            if parsed_duration:
                for d in parsed_duration.groups():
                    if d:
                        duration_str += f"{d[:-1]}:"
                duration_str = duration_str.strip(":")
            aud_watch_ratio = video['statistics'].get('audienceWatchRatio', 0)
            relative_retention_performance = video['statistics'].get('relativeRetentionPerformance', 0)
            stats_dict = dict(channel_title=channel_title, title=title, description=description, published=published,
                              tag_count=tag_count, view_count=view_count, viewer_percentage=viewer_percentage,
                              estimated_min_watched=estimated_min_watched, avg_view_duration=avg_view_duration,
                              avg_view_percentage=avg_view_percentage, like_count=like_count,
                              dislike_count=dislike_count, share_count=share_count,
                              comment_count=comment_count, duration_str=duration_str, aud_watch_ratio=aud_watch_ratio,
                              relative_retention_performance=relative_retention_performance)
            stats_list.append(stats_dict)

    return stats_list

def print_video_infos(video_response):
    items = video_response.get("items")[0]
    # get the snippet, statistics & content details from the video response
    snippet         = items["snippet"]
    statistics      = items["statistics"]
    content_details = items["contentDetails"]
    # get infos from the snippet
    channel_title = snippet["channelTitle"]
    title         = snippet["title"]
    description   = snippet["description"]
    publish_time  = snippet["publishedAt"]
    # get stats infos
    comment_count = statistics["commentCount"]
    like_count    = statistics["likeCount"]
    #dislike_count = statistics["dislikeCount"]
    view_count    = statistics["viewCount"]
    # get duration from content details
    duration = content_details["duration"]
    # duration in the form of something like 'PT5H50M15S'
    # parsing it to be something like '5:50:15'
    parsed_duration = re.search(f"PT(\d+H)?(\d+M)?(\d+S)", duration).groups()
    duration_str = ""
    for d in parsed_duration:
        if d:
            duration_str += f"{d[:-1]}:"
    duration_str = duration_str.strip(":")
    print(f"""\
    Title: {title}
    Description: {description}
    Channel Title: {channel_title}
    Publish time: {publish_time}
    Duration: {duration_str}
    Number of comments: {comment_count}
    Number of likes: {like_count}
    Number of views: {view_count}
    """)
    #Number of dislikes: {dislike_count}

def search(youtube, **kwargs):
    return youtube.search().list(
        part="snippet",
        **kwargs
    ).execute()


def get_comments_short(youtube, **kwargs):
    return youtube.commentThreads().list(
        part="snippet",
        **kwargs
    ).execute()

def write_to_csv(comments,csv_filename):
    with open(f'{csv_filename}.csv', 'w') as comments_file:
        comments_writer = csv.writer(comments_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        comments_writer.writerow(['Video ID', 'Title', 'Comment'])
        for row in comments:
            # convert the tuple to a list and write to the output file
            comments_writer.writerow(list(row))
    comments_file.close()


def get_comments(youtube,part,maxResults,textFormat,order,videoId,csv_filename):
    # create empty lists to store desired information
    # comments, commentsId, repliesCount, likesCount, updatedAt = [], [], [], [], []
    comments_info_list = []
    # make an API call using our service
    response = youtube.commentThreads().list(
        part=part,
        maxResults=maxResults,
        textFormat=textFormat,
        order=order,
        videoId=videoId
    ).execute()

    while response:  # this loop will continue to run until max out the quota

        for item in response['items']:
            # index item for desired data features
            comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
            comment_id = item['snippet']['topLevelComment']['id']
            reply_count = item['snippet']['totalReplyCount']
            like_count = item['snippet']['topLevelComment']['snippet']['likeCount']
            updated_at = item["snippet"]["topLevelComment"]["snippet"]["updatedAt"]

            comments_dict = dict(comment=comment, comment_id=comment_id, reply_count=reply_count, like_count=like_count, updated_at=updated_at )
            comments_info_list.append(comments_dict)

        #  check for nextPageToken, and if it exists, set response equal to the JSON response
        if 'nextPageToken' in response:
            response = youtube.commentThreads().list(
                part=part,
                maxResults=maxResults,
                textFormat=textFormat,
                order=order,
                videoId=videoId,
                pageToken=response['nextPageToken']
            ).execute()
        else:
            break

    # return the data of interest
    return comments_info_list
