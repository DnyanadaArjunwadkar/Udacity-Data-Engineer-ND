import os
import glob
import psycopg2
import pandas as pd
from sql_queries import *


def process_song_file(cur, filepath):
    '''
    filepath: json file containg song and artist info
    cur:connection

    '''
    # open song file
    df = pd.read_json(filepath, lines=True)

    # insert song record
    song_data = df[['song_id', 'title','artist_id', 'year', 'duration']].values[0].tolist()
    song_data = (song_data[0], song_data[1], song_data[2], song_data[3], song_data[4])
    try:
        cur.execute(song_table_insert, song_data)
    except:
        pass

    # insert artist record
    artist_data = df[['artist_id', 'artist_name', 'artist_location', 'artist_latitude', 'artist_longitude']].values[0].tolist()
    artist_data = (artist_data[0], artist_data[1], artist_data[2], artist_data[3], artist_data[4])
    try:
        cur.execute(artist_table_insert, artist_data)
    except:
        pass

def process_log_file(cur, filepath):
    '''
    filepath: log file containg user,time data
    cur:connection

    '''
    # open log file
    df = pd.read_json(filepath, lines=True)

    # filter by NextSong action
    df = df[df['page']=="NextSong"].reset_index()

    # convert timestamp column to datetime
     t = pd.to_datetime(df.ts, unit='ms')
    
    df['week'] = t.apply(lambda x: datetime.date(x.year, x.month, x.day).isocalendar()[1])
    df['week_day'] = t.apply(lambda x: datetime.date(x.year, x.month, x.day).strftime("%A"))
    # insert time data records
    time_data = (t, t.dt.hour, t.dt.day, df.week, t.dt.month, t.dt.year, df.week_day)
    column_labels = ['start_time','hour','day','week','month', 'year','weekday']
    time_df = pd.DataFrame(dict(zip(column_labels, time_data)))
    df['start_time'] = t

    #dny added
    time_df_in_order=time_df[['start_time','hour','day','week','month','year','weekday']]

    for i, row in time_df_in_order.iterrows():
        cur.execute(time_table_insert, list(row))

    # load user table
    user_df = df[['userId','firstName', 'lastName', 'gender', 'level']]


    # insert user records
    for i, row in user_df.iterrows():
        cur.execute(user_table_insert, row)

    # insert songplay records
    for index, row in df.iterrows():
        song_select="""SELECT songs.song_id, artists.artist_id FROM songs JOIN artists ON  songs.artist_id=artists.artist_id WHERE songs.title=%s AND artists.name=%s AND songs.duration=%s;"""
        # get songid and artistid from song and artist tables
        cur.execute(song_select, (row.song, row.artist, row.length))
        results = cur.fetchone()
        
        if results:
            songid, artistid = results
        else:
            songid, artistid = None, None

        # insert songplay record
        songplay_data = (str(row.start_time),row.userId,row.level,songid,artistid, row.sessionId,row.location,row.userAgent)
        cur.execute(songplay_table_insert, songplay_data)


def process_data(cur, conn, filepath, func):
    # get all files matching extension from directory
    all_files = []
    for root, dirs, files in os.walk(filepath):
        files = glob.glob(os.path.join(root,'*.json'))
        for f in files :
            all_files.append(os.path.abspath(f))

    # get total number of files found
    num_files = len(all_files)
    print('{} files found in {}'.format(num_files, filepath))

    # iterate over files and process
    for i, datafile in enumerate(all_files, 1):
        func(cur, datafile)
        conn.commit()
        print('{}/{} files processed.'.format(i, num_files))


def main():
    conn = psycopg2.connect("host=127.0.0.1 dbname=sparkifydb user=postgres password=password")
    cur = conn.cursor()

    process_data(cur, conn, filepath='data/song_data', func=process_song_file)
    process_data(cur, conn, filepath='data/log_data', func=process_log_file)

    conn.close()


if __name__ == "__main__":
    main()