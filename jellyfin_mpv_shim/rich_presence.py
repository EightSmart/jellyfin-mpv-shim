from pypresence import Client
from pypresence.types import ActivityType, StatusDisplayType
import time
import requests
from functools import lru_cache
import logging

client_id = "743296148592263240"
RPC = Client(client_id)
RPC.start()


def register_join_event(syncplay_join_group: callable):
    RPC.register_event("activity_join", syncplay_join_group)

def get_anilist_cover(anime_title, season_number=None):
    """
    Fetch cover and banner images for an anime title using the AniList API.
    """
    url = "https://graphql.anilist.co"
    query = """
    query ($search: String) {
      Media(search: $search, type: ANIME) {
        title {
          romaji
          english
          native
        }
        coverImage {
          large
          extraLarge
        }
        bannerImage
        siteUrl
      }
    }
    """
    if season_number and season_number > 1:
        variables = {"search": f"{anime_title} Season {season_number}"}
    else:
        variables = {"search": anime_title}

    try:
        response = requests.post(url, json={"query": query, "variables": variables})
        response.raise_for_status()
        data = response.json()
        media = data.get("data", {}).get("Media")
        if media:
            return {
                "title": media["title"]["romaji"],
                "title_jp": media["title"]["native"],
                "cover": media["coverImage"]["extraLarge"] or media["coverImage"]["large"],
                "banner": media["bannerImage"],
                "url": media["siteUrl"],
            }
    except requests.exceptions.RequestException as e:
        pass

    return None

@lru_cache(maxsize=200)
def get_anilist_cover_cached(anime_title, season_number=None):
    return get_anilist_cover(anime_title, season_number)

def send_presence(
    title: str,
    subtitle: str,
    season_number: int = None,
    playback_time: float = None,
    duration: float = None,
    playing: bool = False,
    syncplay_group: str = None,
):
    small_image = "play-dark3" if playing else None
    anilist_data = get_anilist_cover_cached(title, season_number=season_number)
    if anilist_data:
        image_url = anilist_data["cover"]
        anilist_url = anilist_data["url"]
        image_text = anilist_data["title_jp"]
    else:
        image_url = "jellyfin2"
        anilist_url = None
        image_text = title
    start = None
    end = None
    if playback_time is not None and duration is not None and playing:
        start = int(time.time() - playback_time)
        end = int(start + duration)

    payload = {
        "activity_type": ActivityType.WATCHING,
        "status_display_type": StatusDisplayType.DETAILS,
        "name": "Jellyfin",
        "details": title,
        "state": subtitle if subtitle else "Unknown Media",
        "instance": False,
        "large_image": image_url,
        "start": start,
        "end": end,
        "large_text": image_text,
        "small_image": small_image,
        "buttons": [{"label": "Anilist", "url": anilist_url}]
    }

    if syncplay_group:
        payload["party_id"] = str(hash(syncplay_group))
        payload["party_size"] = [1, 100]
        payload["join"] = syncplay_group

    RPC.set_activity(**payload)


def clear_presence():
    RPC.clear_activity()
