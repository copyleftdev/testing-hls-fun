import requests
import pytest
import av
import io
from typing import List, Union

# HELPER FUNCTIONS

def fetch_hls_playlist(url: str) -> str:
    """
    Fetch the content of an HLS playlist given its URL.

    :param url: The URL of the HLS playlist.
    :return: The content of the playlist.
    """
    response = requests.get(url)
    response.raise_for_status()
    return response.text

def parse_m3u8(playlist: str) -> List[str]:
    """
    Parse an m3u8 playlist and extract URIs from it.

    :param playlist: The m3u8 playlist content.
    :return: List of URIs found in the playlist.
    """
    lines = playlist.strip().split("\n")
    uris = [line for line in lines if not line.startswith("#") and line.strip()]
    return uris

def get_segment_urls(main_playlist_url: str) -> List[str]:
    """
    Get the segment URLs from an HLS playlist.

    :param main_playlist_url: The URL of the main HLS playlist.
    :return: List of segment URLs.
    """
    segment_urls = []
    main_playlist = fetch_hls_playlist(main_playlist_url)
    variant_uris = parse_m3u8(main_playlist)

    for uri in variant_uris:
        variant_playlist_url = "/".join(main_playlist_url.split("/")[:-1]) + "/" + uri
        variant_playlist = fetch_hls_playlist(variant_playlist_url)
        segment_uris = parse_m3u8(variant_playlist)

        for segment_uri in segment_uris:
            segment_url = "/".join(variant_playlist_url.split("/")[:-1]) + "/" + segment_uri
            segment_urls.append(segment_url)

    return segment_urls

def validate_ts_content(ts_data: Union[str, bytes]) -> None:
    """
    Validate the content of a .ts segment using PyAV.

    :param ts_data: Raw content of the .ts segment.
    :raises AssertionError: If there's no video or audio stream in the segment.
    """
    container = av.open(io.BytesIO(ts_data))
    video_stream_found = False
    audio_stream_found = False

    for stream in container.streams:
        if stream.type == 'video':
            video_stream_found = True
        elif stream.type == 'audio':
            audio_stream_found = True

    assert video_stream_found, "No video stream found in .ts segment"
    assert audio_stream_found, "No audio stream found in .ts segment"

@pytest.mark.parametrize('segment_url', get_segment_urls("https://demo.unified-streaming.com/k8s/features/stable/video/tears-of-steel/tears-of-steel.ism/.m3u8"))
def test_segment_validity(segment_url: str) -> None:
    """
    Test the validity of a .ts segment.

    :param segment_url: The URL of the .ts segment.
    """
    response = requests.get(segment_url)
    assert response.status_code == 200
    
    # Validate the content of the .ts segment
    validate_ts_content(response.content)
