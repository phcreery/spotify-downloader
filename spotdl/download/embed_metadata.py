from urllib.request import urlopen

from mutagen.easyid3 import EasyID3, ID3
from mutagen.flac import Picture, FLAC
from mutagen.mp4 import MP4, MP4Cover
from mutagen.id3 import APIC as AlbumCover, USLT, COMM as Comment
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis

import base64

# Apple has specific tags - see mutagen docs -
# http://mutagen.readthedocs.io/en/latest/api/mp4.html
M4A_TAG_PRESET = {
    "album": "\xa9alb",
    "artist": "\xa9ART",
    "date": "\xa9day",
    "title": "\xa9nam",
    "year": "\xa9day",
    "originaldate": "purd",
    "comment": "\xa9cmt",
    "group": "\xa9grp",
    "writer": "\xa9wrt",
    "genre": "\xa9gen",
    "tracknumber": "trkn",
    "albumartist": "aART",
    "discnumber": "disk",
    "cpil": "cpil",
    "albumart": "covr",
    "copyright": "cprt",
    "tempo": "tmpo",
    "lyrics": "\xa9lyr",
    "explicit": "rtng",
}

TAG_PRESET = {}
for key in M4A_TAG_PRESET.keys():
    TAG_PRESET[key] = key


def _set_id3_mp3(converted_file_path, song_obj):
    # embed song details
    # ! we save tags as both ID3 v2.3 and v2.4
    # ! The simple ID3 tags
    audio_file = EasyID3(converted_file_path)

    audio_file = _embed_mp3_metadata(audio_file, song_obj, converted_file_path)

    # ! save as both ID3 v2.3 & v2.4 as v2.3 isn't fully features and
    # ! windows doesn't support v2.4 until later versions of Win10
    audio_file.save(v2_version=3)

    audio_file = _embed_mp3_cover(audio_file, song_obj, converted_file_path)
    audio_file = _embed_mp3_lyrics(audio_file, song_obj)
    # ! setting song links as comment (helpful for devs)
    audio_file.add(
        Comment(
            encoding=3,
            text=song_obj.get_youtube_link()
        )
    )

    audio_file.save(v2_version=3)


def _set_id3_m4a(converted_file_path, song_obj):
    # embed song details
    # ! we save tags as both ID3 v2.3 and v2.4
    # ! The simple ID3 tags
    audio_file = MP4(converted_file_path)

    audio_file = _embed_basic_metadata(audio_file, song_obj, "m4a", M4A_TAG_PRESET)
    audio_file = _embed_m4a_metadata(audio_file, song_obj)

    audio_file.save()


def _set_id3_flac(converted_file_path, song_obj):
    audio_file = FLAC(converted_file_path)

    audio_file = _embed_basic_metadata(audio_file, song_obj, "flac")
    audio_file = _embed_ogg_metadata(audio_file, song_obj)
    audio_file = _embed_cover(audio_file, song_obj, "flac")

    audio_file.save()


def _set_id3_opus(converted_file_path, song_obj):
    audio_file = OggOpus(converted_file_path)

    audio_file = _embed_basic_metadata(audio_file, song_obj, "opus")
    audio_file = _embed_ogg_metadata(audio_file, song_obj)
    audio_file = _embed_cover(audio_file, song_obj, "opus")

    audio_file.save()


def _set_id3_ogg(converted_file_path, song_obj):
    audio_file = OggVorbis(converted_file_path)

    audio_file = _embed_basic_metadata(audio_file, song_obj, "ogg")
    audio_file = _embed_ogg_metadata(audio_file, song_obj)
    audio_file = _embed_cover(audio_file, song_obj, "ogg")

    audio_file.save()


def _embed_mp3_metadata(audio_file, song_obj, converted_file_path):

    # ! Get rid of all existing ID3 tags (if any exist)
    audio_file.delete()

    # ! song name
    audio_file['title'] = song_obj.get_song_name()
    audio_file['titlesort'] = song_obj.get_song_name()

    # ! track number
    audio_file['tracknumber'] = str(song_obj.get_track_number())

    # ! disc number
    audio_file['discnumber'] = str(song_obj.get_disc_number())

    # ! genres (pretty pointless if you ask me)
    # ! we only apply the first available genre as ID3 v2.3 doesn't support multiple
    # ! genres and ~80% of the world PC's run Windows - an OS with no ID3 v2.4 support
    genres = song_obj.get_genres()
    if len(genres) > 0:
        audio_file['genre'] = genres[0]

    # ! all involved artists
    audio_file['artist'] = song_obj.get_contributing_artists()

    # ! album name
    audio_file['album'] = song_obj.get_album_name()

    # ! album artist (all of 'em)
    audio_file['albumartist'] = song_obj.get_album_artists()

    # ! album release date (to what ever precision available)
    audio_file['date'] = song_obj.get_album_release()
    audio_file['originaldate'] = song_obj.get_album_release()

    return audio_file


def _embed_mp3_cover(audio_file, song_obj, converted_file_path):
    # ! setting the album art
    audio_file = ID3(converted_file_path)
    rawAlbumArt = urlopen(song_obj.get_album_cover_url()).read()
    audio_file['APIC'] = AlbumCover(
        encoding=3,
        mime='image/jpeg',
        type=3,
        desc='Cover',
        data=rawAlbumArt
    )

    return audio_file


def _embed_mp3_lyrics(audio_file, song_obj):
    # ! setting the lyrics
    lyrics = song_obj.get_lyrics()
    USLTOutput = USLT(encoding=3, lang=u'eng', desc=u'desc', text=lyrics)
    audio_file["USLT::'eng'"] = USLTOutput

    return audio_file


def _embed_m4a_metadata(audio_file, song_obj):
    # set year
    year = song_obj.get_album_release().split("-")[0]
    if year:
        audio_file[M4A_TAG_PRESET["year"]] = year

    # set youtube link as comment
    youtube_link = song_obj.get_youtube_link()
    if youtube_link:
        audio_file[M4A_TAG_PRESET["comment"]] = youtube_link

    # set lyrics
    lyrics = song_obj.get_lyrics()
    if lyrics:
        audio_file[M4A_TAG_PRESET["lyrics"]] = lyrics

    # Explicit values: Dirty: 4, Clean: 2, None: 0
    audio_file[M4A_TAG_PRESET["explicit"]] = (0,)
    try:
        audio_file[M4A_TAG_PRESET["albumart"]] = [
            MP4Cover(urlopen(song_obj.get_album_cover_url()).read(),
                     imageformat=MP4Cover.FORMAT_JPEG)
        ]
    except IndexError:
        pass

    return audio_file


def _embed_basic_metadata(audio_file, song_obj, encoding, preset=TAG_PRESET):

    # set main artist
    main_artist = song_obj.get_contributing_artists()[0]
    if main_artist:
        audio_file[preset["artist"]] = main_artist
        audio_file[preset["albumartist"]] = main_artist

    # set song title
    song_title = song_obj.get_song_name()
    if song_title:
        audio_file[preset["title"]] = song_title

    # set album name
    album_name = song_obj.get_album_name()
    if album_name:
        audio_file[preset["album"]] = album_name

    # set release data
    release_data = song_obj.get_album_release()
    if release_data:
        audio_file[preset["date"]] = release_data
        audio_file[preset["originaldate"]] = release_data

    # set genre
    genre = song_obj.get_genres()[0]
    if genre:
        audio_file[preset["genre"]] = genre

    # set disc number
    disc_number = song_obj.get_disc_number()
    if disc_number:
        if encoding in ["flac", "ogg", "opus"]:
            audio_file[preset["discnumber"]] = str(disc_number)
        else:
            audio_file[preset["discnumber"]] = [(disc_number, 0)]

    # set track number
    track_number = song_obj.get_track_number()
    if track_number:
        if encoding in ["flac", "ogg", "opus"]:
            audio_file[preset["tracknumber"]] = str(track_number)
        else:
            audio_file[preset["tracknumber"]] = [(track_number, 0)]

    return audio_file


def _embed_ogg_metadata(audio_file, song_obj):
    # set year
    year = song_obj.get_album_release().split("-")[0]
    if year:
        audio_file["year"] = year

    # set youtube link as comment
    youtube_link = song_obj.get_youtube_link()
    if youtube_link:
        audio_file["comment"] = youtube_link

    # set lyrics
    lyrics = song_obj.get_lyrics()
    if lyrics:
        audio_file["lyrics"] = lyrics

    return audio_file


def _embed_cover(audio_file, song_obj, encoding):
    image = Picture()
    image.type = 3
    image.desc = "Cover"
    image.mime = "image/jpeg"
    image.data = urlopen(
        song_obj.get_album_cover_url()
    ).read()

    if encoding == "flac":
        audio_file.add_picture(image)
    elif encoding == "ogg" or encoding == "opus":
        # From the Mutagen docs (https://mutagen.readthedocs.io/en/latest/user/vcomment.html)
        image_data = image.write()
        encoded_data = base64.b64encode(image_data)
        vcomment_value = encoded_data.decode("ascii")
        audio_file["metadata_block_picture"] = [vcomment_value]

    return audio_file


SET_ID3_FUNCTIONS = {
    "mp3": _set_id3_mp3,
    "flac": _set_id3_flac,
    "opus": _set_id3_opus,
    "ogg": _set_id3_ogg,
    "m4a": _set_id3_m4a
}


def set_id3_data(converted_file_path, song_obj, outputFormat):
    function = SET_ID3_FUNCTIONS.get(outputFormat)
    if function:
        function(converted_file_path, song_obj)
