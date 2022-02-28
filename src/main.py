import Functions as fun
from src import addresses
import pandas as pd

event_no = 0
video_comments_only = True

year = addresses.January_events[event_no]
video_list = addresses.video_ids_all[event_no]

# ========== authenticate to YouTube API ===============================#
youtube = fun.youtube_authenticate()
upload_id = addresses.upload_ids[event_no]

# ========== Used to extract video information e.g., likes, shares, no. of comments & views ============#
if video_comments_only == False:
     video_list = fun.get_video_list(youtube, upload_id)
     video_data = fun.extract_video_infos(youtube, video_list)

     df = pd.DataFrame(video_data)
     df['title_length'] = df['title'].str.len()
     df["view_count"] = pd.to_numeric(df["view_count"])
     df["like_count"] = pd.to_numeric(df["like_count"])
     df["dislike_count"] = pd.to_numeric(df["dislike_count"])
     df["comment_count"] = pd.to_numeric(df["comment_count"])
     # reaction used later add up likes + dislikes + comments
     df["reactions"] = df["like_count"] + df["dislike_count"] + df["comment_count"] + df["comment_count"]

     date_string = df["published"].to_string()
     #list_title = df["title"].to_string()
     #print(list_title[23:31])

     date_string = date_string[5:13]
     outfile = open("../data/statistics" + date_string + ".csv", 'wb')
     df.to_csv(outfile)
     outfile.close()

     #date_string = date_string + "-"

     for i in range (0, len(video_list)):
          video_id = video_list[i]
          print(video_list[i])

# ================== Used to extract video comments ===================#
else:
     for i in range(0, len(video_list)):
          video_id = video_list[i]
          date_string = str(year) + str(i)
          print(video_list[i], " ", date_string)

          # date_comment = date_string
          comments, commentsId, repliesCount, likesCount, updatedAt = [], [], [], [], []
          # #comments, commentsId, repliesCount, likesCount, updatedAt = fun.get_comments(youtube,'snippet',100,'plainText','time',video_id,"comments")
          comments = fun.get_comments(youtube, 'snippet', 100, 'plainText', 'time', video_id, "comments")

          df = pd.DataFrame(comments)
          # date_comment = date_string + str(i)

          outfile = open("../YwP/data/comments" + date_string + ".csv", 'wb')
          df.to_csv(outfile)
          outfile.close()

print("Fin.")





