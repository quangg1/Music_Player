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


def download_youtube(url: str, output_dir: str, progress_callback=None) -> tuple[Optional[str], Optional[dict]]:
    """Download YouTube video/audio và trả về (file_path, info_dict)
    info_dict chứa: title, artist, duration, uploader, channel, etc.
    """
    if not YT_DLP_AVAILABLE:
        return None, None
    
    try:
        video_id = parse_youtube_url(url)
        if not video_id:
            return None, None
        
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
            # Lấy thông tin video TRƯỚC khi download
            info = ydl.extract_info(url, download=False)
            
            # Download
            ydl.download([url])
            
            # Tìm file đã download
            files = os.listdir(output_dir)
            video_files = [f for f in files if os.path.splitext(f)[1].lower() in ['.mp4', '.webm', '.mkv', '.m4a']]
            
            if video_files:
                # Lấy file mới nhất
                video_files.sort(key=lambda x: os.path.getmtime(os.path.join(output_dir, x)), reverse=True)
                file_path = os.path.join(output_dir, video_files[0])
                
                # Trả về cả file_path và info
                return file_path, info
        
        return None, None
    except Exception as e:
        print(f"Error downloading YouTube: {e}")
        return None, None


def parse_youtube_title(title: str) -> tuple[str, str]:
    """Parse YouTube title để tách artist và song title
    Ví dụ: "ILLIT (아일릿) 'NOT CUTE ANYMORE' Official MV" -> ("ILLIT", "NOT CUTE ANYMORE")
    """
    if not title:
        return "Unknown Artist", "Unknown Title"
    
    # Loại bỏ các từ khóa phổ biến ở cuối
    title_clean = title
    suffixes = [' Official MV', ' Official Music Video', ' Official Audio', ' Official', ' MV', ' Music Video', ' Audio']
    for suffix in suffixes:
        if title_clean.endswith(suffix):
            title_clean = title_clean[:-len(suffix)].strip()
    
    # Pattern 1: "Artist - Title" hoặc "Artist: Title"
    for separator in [' - ', ': ', ' – ', ' — ']:
        if separator in title_clean:
            parts = title_clean.split(separator, 1)
            if len(parts) == 2:
                artist = parts[0].strip()
                song_title = parts[1].strip()
                # Loại bỏ dấu ngoặc đơn/quotes nếu có
                song_title = song_title.strip("'\"")
                return artist, song_title
    
    # Pattern 2: "Artist 'Title'" hoặc "Artist "Title""
    for quote in ["'", '"', '"', '"']:
        if quote in title_clean:
            parts = title_clean.split(quote, 1)
            if len(parts) == 2:
                artist = parts[0].strip()
                song_title = parts[1].strip()
                # Loại bỏ phần còn lại sau quote thứ 2
                if quote in song_title:
                    song_title = song_title.split(quote)[0]
                return artist, song_title
    
    # Pattern 3: "Artist (Title)" - tên trong ngoặc đơn
    if '(' in title_clean and ')' in title_clean:
        import re
        match = re.match(r'^(.+?)\s*\(([^)]+)\)', title_clean)
        if match:
            artist = match.group(1).strip()
            song_title = match.group(2).strip()
            return artist, song_title
    
    # Nếu không parse được, dùng toàn bộ làm title
    return "Unknown Artist", title_clean


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
            title = info.get('title', 'Unknown')
            
            # Parse title để tách artist và song title
            artist, song_title = parse_youtube_title(title)
            
            # Ưu tiên channel name nếu có (thường là artist cho MV)
            uploader = info.get('uploader', '')
            channel = info.get('channel', '')
            
            # Nếu parse được artist từ title, dùng nó; nếu không, dùng channel/uploader
            if artist == "Unknown Artist" and (channel or uploader):
                artist = channel or uploader
            
            return {
                'title': song_title if song_title != "Unknown Title" else title,
                'artist': artist,
                'duration': info.get('duration', 0),
                'full_title': title,  # Giữ nguyên title gốc
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

