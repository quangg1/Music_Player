# ============================================
# YOUTUBE HANDLER - Download và xử lý YouTube
# ============================================

import os
import re
import threading
from typing import Optional

# YouTube support
try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False
    print("⚠️ yt-dlp not installed. Run: pip install yt-dlp")

from linked_list import Song


def parse_youtube_url(url: str) -> Optional[str]:
    """Parse YouTube URL và trả về video ID"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/playlist\?list=([a-zA-Z0-9_-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def is_youtube_url(url: str) -> bool:
    """Kiểm tra xem URL có phải YouTube không"""
    youtube_patterns = [
        'youtube.com',
        'youtu.be',
        'youtube.com/embed',
        'youtube.com/playlist'
    ]
    return any(pattern in url.lower() for pattern in youtube_patterns)


def download_youtube(url: str, output_dir: str, progress_callback=None) -> Optional[str]:
    """Download YouTube video/audio và trả về đường dẫn file"""
    if not YT_DLP_AVAILABLE:
        return None
    
    try:
        video_id = parse_youtube_url(url)
        if not video_id:
            return None
        
        # Cấu hình yt-dlp - tối ưu để tránh SABR streaming warnings
        ydl_opts = {
            'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'noplaylist': True,
            'ignoreerrors': False,
            # Tránh SABR streaming issues
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],  # Tránh web_safari client
                }
            },
        }
        
        if progress_callback:
            ydl_opts['progress_hooks'] = [progress_callback]
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Lấy thông tin video
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            
            # Download
            ydl.download([url])
            
            # Tìm file đã download
            files = os.listdir(output_dir)
            video_files = [f for f in files if os.path.splitext(f)[1].lower() in ['.mp4', '.webm', '.mkv', '.m4a']]
            
            if video_files:
                # Lấy file mới nhất
                video_files.sort(key=lambda x: os.path.getmtime(os.path.join(output_dir, x)), reverse=True)
                file_path = os.path.join(output_dir, video_files[0])
                return file_path
        
        return None
    except Exception as e:
        print(f"Error downloading YouTube: {e}")
        return None


def get_youtube_info(url: str) -> Optional[dict]:
    """Lấy thông tin video YouTube mà không download"""
    if not YT_DLP_AVAILABLE:
        return None
    
    try:
        ydl_opts_info = {
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                }
            },
        }
        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', 'Unknown'),
                'artist': info.get('uploader', 'YouTube'),
                'duration': info.get('duration', 0),
            }
    except:
        return None


def get_playlist_entries(url: str, max_entries: int = 50) -> list:
    """Lấy danh sách videos trong playlist"""
    if not YT_DLP_AVAILABLE:
        return []
    
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'playlistend': max_entries,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                }
            },
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            entries = info.get('entries', [])
            return entries if entries else []
    except:
        return []

