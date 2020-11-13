#===============
#=== Imports ===
#===============

from os import mkdir, remove, system as run_in_shell
from os.path import join, exists
import os
import traceback

from pytube import YouTube

from mutagen.easyid3 import EasyID3, ID3
from mutagen.id3 import USLT
from mutagen.id3 import APIC as AlbumCover

from urllib.request import urlopen

#! The following are not used, they are just here for static typechecking with mypy
from typing import List

from spotdl.search.songObj import SongObj
from spotdl.download.progressHandlers import DownloadTracker
from spotdl.cli.displayManager import DisplayManager

import hashlib

#==========================
#=== Base functionality ===
#==========================

#! Technically, this should ideally be defined within the downloadManager class. But due
#! to the quirks of multiprocessing.Pool, that can't be done. Do not consider this as a
#! standalone function but rather as part of DownloadManager

def download_song(songObj: SongObj, displayManager: DisplayManager = None,
                                    downloadTracker: DownloadTracker = None) -> None:
    '''
    `songObj` `songObj` : song to be downloaded

    `AutoProxy` `displayManager` : autoproxy reference to a `DisplayManager`

    `AutoProxy` `downloadTracker`: autoproxy reference to a `DownloadTracker`

    RETURNS `~`

    Downloads, Converts, Normalizes song & embeds metadata as ID3 tags.
    '''
    try:

        if displayManager:
            # displayManager.notify_download_begin(os.getpid())
            displayManager.notify_download_begin(str(hashlib.md5(bytes(str(songObj.get_display_name()), 'utf-8')).hexdigest()))

        #! all YouTube downloads are to .\Temp; they are then converted and put into .\ and
        #! finally followed up with ID3 metadata tags

        #! we explicitly use the os.path.join function here to ensure download is
        #! platform agnostic
        
        # Create a .\Temp folder if not present
        tempFolder = join('.', 'Temp')
        
        if not exists(tempFolder):
            mkdir(tempFolder)
        
        convertedFilePath = join('.', songObj.get_display_name()) + '.mp3'


        # if a song is already downloaded skip it
        if exists(convertedFilePath):
            if displayManager:
                displayManager.notify_download_skip()
            if downloadTracker:
                downloadTracker.notify_download_completion(songObj)
            
            #! None is the default return value of all functions, we just explicitly define
            #! it here as a continent way to avoid executing the rest of the function.
            return None
        

        # download Audio from YouTube
        if displayManager:
            youtubeHandler = YouTube(
                url                  = songObj.get_youtube_link(),
                on_progress_callback = displayManager.download_progress_hook
            )
        else:
            youtubeHandler = YouTube(songObj.get_youtube_link())
        
        trackAudioStream = youtubeHandler.streams.get_audio_only()

        #! The actual download, if there is any error, it'll be here,
        try:
            #! pyTube will save the song in .\Temp\$songName.mp4, it doesn't save as '.mp3'
            downloadedFilePath = trackAudioStream.download(
                output_path   = tempFolder,
                filename      = songObj.get_display_name(),
                skip_existing = False
            )
        except:
            #! This is equivalent to a failed download, we do nothing, the song remains on
            #! downloadTrackers download queue and all is well...
            #!
            #! None is again used as a convenient exit
            remove(join(tempFolder, songObj.get_display_name()) + '.mp4')
            return None
        
        if displayManager:
            displayManager.notify_download_completion()

        # convert downloaded file to MP3 with normalization

        #! -af loudnorm=I=-7:LRA applies EBR 128 loudness normalization algorithm with
        #! intergrated loudness target (I) set to -17, using values lower than -15
        #! causes 'pumping' i.e. rhythmic variation in loudness that should not
        #! exist -loud parts exaggerate, soft parts left alone.
        #! 
        #! dynaudnorm applies dynamic non-linear RMS based normalization, this is what
        #! actually normalized the audio. The loudnorm filter just makes the apparent
        #! loudness constant
        #!
        #! apad=pad_dur=2 adds 2 seconds of silence toward the end of the track, this is
        #! done because the loudnorm filter clips/cuts/deletes the last 1-2 seconds on
        #! occasion especially if the song is EDM-like, so we add a few extra seconds to
        #! combat that.
        #!
        #! -acodec libmp3lame sets the encoded to 'libmp3lame' which is far better
        #! than the default 'mp3_mf', '-abr true' automatically determines and passes the
        #! audio encoding bitrate to the filters and encoder. This ensures that the
        #! sampled length of songs matches the actual length (i.e. a 5 min song won't display
        #! as 47 seconds long in your music player, yeah that was an issue earlier.)

        command = 'ffmpeg -v quiet -y -i "%s" -acodec libmp3lame -abr true -af loudnorm=I=-17 "%s"'
        formattedCommand = command % (downloadedFilePath, convertedFilePath)

        run_in_shell(formattedCommand)

        #! Wait till converted file is actually created
        while True:
            if exists(convertedFilePath):
                break

        if displayManager:
            displayManager.notify_conversion_completion()



        # embed song details
        #! we save tags as both ID3 v2.3 and v2.4

        #! The simple ID3 tags
        audioFile = EasyID3(convertedFilePath)

        #! Get rid of all existing ID3 tags (if any exist)
        audioFile.delete()

        #! song name
        audioFile['title'] = songObj.get_song_name()
        audioFile['titlesort'] = songObj.get_song_name()

        #! track number
        audioFile['tracknumber'] = str(songObj.get_track_number())

        #! genres (pretty pointless if you ask me)
        #! we only apply the first available genre as ID3 v2.3 doesn't support multiple
        #! genres and ~80% of the world PC's run Windows - an OS with no ID3 v2.4 support
        genres = songObj.get_genres()

        if len(genres) > 0:
            audioFile['genre'] = genres[0]
        
        #! all involved artists
        audioFile['artist'] = songObj.get_contributing_artists()

        #! album name
        audioFile['album'] = songObj.get_album_name()

        #! album artist (all of 'em)
        audioFile['albumartist'] = songObj.get_album_artists()

        #! album release date (to what ever precision available)
        audioFile['date']         = songObj.get_album_release()
        audioFile['originaldate'] = songObj.get_album_release()

        #! save as both ID3 v2.3 & v2.4 as v2.3 isn't fully features and
        #! windows doesn't support v2.4 until later versions of Win10
        audioFile.save(v2_version = 3)

        #! setting the album art
        audioFile = ID3(convertedFilePath)

        rawAlbumArt = urlopen(songObj.get_album_cover_url()).read()

        audioFile['APIC'] = AlbumCover(
            encoding = 3,
            mime = 'image/jpeg',
            type = 3,
            desc = 'Cover',
            data = rawAlbumArt
        )

        audioFile.save(v2_version = 3)

        # Do the necessary cleanup
        if displayManager:
            displayManager.notify_finished()
        
        if downloadTracker:
            downloadTracker.notify_download_completion(songObj)



        # delete the unnecessary YouTube download File
        remove(downloadedFilePath)

    except KeyboardInterrupt:
        raise RuntimeError("Keyboard interrupt")

    except Exception as e:
        # print 'got exception: %r:, terminating the pool' % (e,)
        tb = traceback.format_exc()
        if displayManager:
            displayManager.notify_error(os.getpid(), e, tb)
        else:
            raise e