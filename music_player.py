# ============================================
# 🎵 MELODIFY - MUSIC PLAYER WITH LINKED LIST
# ============================================
# Ứng dụng nghe nhạc sử dụng Doubly Linked List
# Developed for DSA Project
# ============================================

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import os
import threading
import time
import shutil
import json
from pathlib import Path
from typing import Optional
import random
from datetime import datetime
import webbrowser

# Import từ các module đã tách
from theme import Theme
from ui_components import GlowButton, ModernSlider
from music_engine import MusicEngine, VideoPlayer, VIDEO_AVAILABLE, PYDUB_AVAILABLE, FFMPEG_AVAILABLE
from youtube_handler import (
    YT_DLP_AVAILABLE, parse_youtube_url, is_youtube_url,
    download_youtube, get_youtube_info, get_playlist_entries
)
from linked_list import PlaylistLinkedList, Song


# ==================== MAIN APPLICATION ====================
class MelodifyApp:
    """Ứng dụng nghe nhạc chính"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🎵 Melodify - Music Player")
        self.root.geometry("900x700")
        self.root.configure(bg=Theme.BG_DARK)
        self.root.minsize(800, 600)
        
        # Icon nếu có
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass
        
        # Core components
        self.playlist = PlaylistLinkedList()
        self.favorites = PlaylistLinkedList()  # Linked List thứ 2 cho favorites
        self.engine = MusicEngine()
        self.video_player = None  # Sẽ khởi tạo sau khi tạo UI
        
        # State
        self.repeat_mode = 0  # 0: off, 1: all, 2: one
        self.shuffle_mode = False
        self.update_thread = None
        self.running = True
        
        # Stats
        self.stats = {
            "total_played": 0,
            "total_time": 0.0,
            "last_played": None
        }
        
        # File paths
        self.data_dir = os.path.join(os.path.dirname(__file__), '.melodify_data')
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        self.playlist_file = os.path.join(self.data_dir, 'playlist.json')
        self.favorites_file = os.path.join(self.data_dir, 'favorites.json')
        self.stats_file = os.path.join(self.data_dir, 'stats.json')
        
        # Load saved data
        self._load_saved_data()
        
        # Build UI
        self._create_styles()
        self._create_ui()
        
        # Refresh playlist view để hiển thị playlist đã load
        self._refresh_playlist_view()
        
        self._start_update_loop()
        
        # Keyboard bindings
        self.root.bind("<space>", lambda e: self.toggle_play())
        self.root.bind("<Left>", lambda e: self.previous_song())
        self.root.bind("<Right>", lambda e: self.next_song())
        
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Menu bar
        self._create_menu()
    
    def _create_styles(self):
        """Tạo styles cho ttk widgets"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Listbox style (dùng Treeview thay thế)
        style.configure("Playlist.Treeview",
                       background=Theme.BG_CARD,
                       foreground=Theme.TEXT_PRIMARY,
                       fieldbackground=Theme.BG_CARD,
                       borderwidth=0,
                       font=("Segoe UI", 11))
        
        style.configure("Playlist.Treeview.Heading",
                       background=Theme.BG_DARK,
                       foreground=Theme.ACCENT_PRIMARY,
                       font=("Segoe UI", 10, "bold"))
        
        style.map("Playlist.Treeview",
                 background=[("selected", Theme.BG_HOVER)],
                 foreground=[("selected", Theme.ACCENT_PRIMARY)])
    
    def _create_menu(self):
        """Tạo menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save Playlist", command=self.save_playlist)
        file_menu.add_command(label="Load Playlist", command=self.load_playlist)
        file_menu.add_separator()
        file_menu.add_command(label="Export Playlist...", command=self.export_playlist)
        file_menu.add_command(label="Import Playlist...", command=self.import_playlist)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)
        
        # Playlist menu
        pl_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Playlist", menu=pl_menu)
        pl_menu.add_command(label="🔍 Search...", command=self.search_song, accelerator="Ctrl+F")
        pl_menu.add_command(label="❤️ Favorites", command=self.show_favorites)
        pl_menu.add_separator()
        pl_menu.add_command(label="📊 Statistics", command=self.show_stats)
        
        # Linked List menu - THỂ HIỆN CỐT LÕI ĐỀ BÀI
        ll_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="🔗 Linked List", menu=ll_menu)
        ll_menu.add_command(label="📊 Visualization", command=self.show_linked_list_visualization, accelerator="Ctrl+L")
        ll_menu.add_command(label="⚙️ Operations", command=self.show_linked_list_operations)
        ll_menu.add_command(label="ℹ️ Info", command=self.show_linked_list_info)
        ll_menu.add_separator()
        ll_menu.add_command(label="➕ Insert at Position", command=self.insert_song_at_position)
        ll_menu.add_command(label="➖ Delete at Position", command=self.delete_song_at_position)
        
        # Bind shortcut
        self.root.bind("<Control-l>", lambda e: self.show_linked_list_visualization())
        self.root.bind("<Control-L>", lambda e: self.show_linked_list_visualization())
        
        # Bind shortcuts
        self.root.bind("<Control-f>", lambda e: self.search_song())
        self.root.bind("<Control-F>", lambda e: self.search_song())
    
    def _load_saved_data(self):
        """Load dữ liệu đã lưu"""
        # Load playlist
        saved_playlist = PlaylistLinkedList.load_from_file(self.playlist_file)
        if saved_playlist and not saved_playlist.is_empty:
            self.playlist = saved_playlist
        
        # Load favorites
        saved_favs = PlaylistLinkedList.load_from_file(self.favorites_file)
        if saved_favs and not saved_favs.is_empty:
            self.favorites = saved_favs
        
        # Load stats
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    self.stats = json.load(f)
            except:
                pass
    
    def _save_all_data(self):
        """Lưu tất cả dữ liệu"""
        self.playlist.save_to_file(self.playlist_file)
        self.favorites.save_to_file(self.favorites_file)
        
        # Save stats
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=2)
        except:
            pass
    
    def _create_ui(self):
        """Xây dựng giao diện"""
        
        # ===== HEADER =====
        header = tk.Frame(self.root, bg=Theme.BG_DARK, height=80)
        header.pack(fill=tk.X, padx=20, pady=10)
        header.pack_propagate(False)
        
        # Logo
        logo_frame = tk.Frame(header, bg=Theme.BG_DARK)
        logo_frame.pack(side=tk.LEFT)
        
        tk.Label(logo_frame, text="🎵", font=("Segoe UI Symbol", 32),
                bg=Theme.BG_DARK, fg=Theme.ACCENT_PRIMARY).pack(side=tk.LEFT)
        
        title_frame = tk.Frame(logo_frame, bg=Theme.BG_DARK)
        title_frame.pack(side=tk.LEFT, padx=10)
        
        tk.Label(title_frame, text="MELODIFY", 
                font=("Segoe UI", 24, "bold"),
                bg=Theme.BG_DARK, fg=Theme.TEXT_PRIMARY).pack(anchor=tk.W)
        tk.Label(title_frame, text="Powered by Linked List", 
                font=("Segoe UI", 10),
                bg=Theme.BG_DARK, fg=Theme.TEXT_MUTED).pack(anchor=tk.W)
        
        # Add buttons frame
        add_buttons_frame = tk.Frame(header, bg=Theme.BG_DARK)
        add_buttons_frame.pack(side=tk.RIGHT, padx=10)
        
        # Add songs button
        add_btn = tk.Button(add_buttons_frame, text="➕ Add Songs", 
                           font=("Segoe UI", 11, "bold"),
                           bg=Theme.ACCENT_PRIMARY, fg=Theme.BG_DARK,
                           activebackground=Theme.ACCENT_SECONDARY,
                           activeforeground=Theme.TEXT_PRIMARY,
                           border=0, padx=20, pady=8,
                           cursor="hand2",
                           command=self.add_songs)
        add_btn.pack(side=tk.LEFT, padx=5)
        
        # Add from YouTube button
        yt_btn = tk.Button(add_buttons_frame, text="📺 Add from YouTube", 
                          font=("Segoe UI", 11, "bold"),
                          bg=Theme.ACCENT_SECONDARY, fg=Theme.TEXT_PRIMARY,
                          activebackground=Theme.ACCENT_TERTIARY,
                          activeforeground=Theme.TEXT_PRIMARY,
                          border=0, padx=20, pady=8,
                          cursor="hand2",
                          command=self.add_from_youtube)
        yt_btn.pack(side=tk.LEFT, padx=5)
        
        # ===== MAIN CONTENT =====
        content = tk.Frame(self.root, bg=Theme.BG_DARK)
        content.pack(fill=tk.BOTH, expand=True, padx=20)
        
        # Left: Playlist
        playlist_frame = tk.Frame(content, bg=Theme.BG_CARD)
        playlist_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Playlist header
        pl_header = tk.Frame(playlist_frame, bg=Theme.BG_CARD)
        pl_header.pack(fill=tk.X, padx=15, pady=10)
        
        tk.Label(pl_header, text="📋 PLAYLIST", 
                font=("Segoe UI", 14, "bold"),
                bg=Theme.BG_CARD, fg=Theme.ACCENT_PRIMARY).pack(side=tk.LEFT)
        
        self.playlist_count = tk.Label(pl_header, text="0 songs",
                                       font=("Segoe UI", 10),
                                       bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED)
        self.playlist_count.pack(side=tk.RIGHT)
        
        # Playlist listbox (using Treeview)
        tree_frame = tk.Frame(playlist_frame, bg=Theme.BG_CARD)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        self.playlist_tree = ttk.Treeview(tree_frame, style="Playlist.Treeview",
                                         columns=("title", "artist"),
                                         show="headings", selectmode="browse")
        
        self.playlist_tree.heading("title", text="Title")
        self.playlist_tree.heading("artist", text="Artist")
        self.playlist_tree.column("title", width=250)
        self.playlist_tree.column("artist", width=150)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, 
                                 command=self.playlist_tree.yview)
        self.playlist_tree.configure(yscrollcommand=scrollbar.set)
        
        self.playlist_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.playlist_tree.bind("<Double-1>", self._on_song_double_click)
        self.playlist_tree.bind("<Delete>", self._on_delete_song)
        self.playlist_tree.bind("<Button-3>", self._on_right_click)  # Right-click menu
        
        # Playlist actions
        pl_actions = tk.Frame(playlist_frame, bg=Theme.BG_CARD)
        pl_actions.pack(fill=tk.X, padx=10, pady=10)
        
        for text, cmd in [("🔍 Search", self.search_song),
                         ("❤️ Favorites", self.show_favorites),
                         ("🗑️ Clear", self.clear_playlist), 
                         ("🔀 Shuffle", self.shuffle_playlist)]:
            btn = tk.Button(pl_actions, text=text,
                           font=("Segoe UI Symbol", 10),
                           bg=Theme.BG_HOVER, fg=Theme.TEXT_PRIMARY,
                           activebackground=Theme.ACCENT_TERTIARY,
                           border=0, padx=15, pady=5,
                           cursor="hand2", command=cmd)
            btn.pack(side=tk.LEFT, padx=5)
        
        # Right: Now Playing
        now_playing = tk.Frame(content, bg=Theme.BG_CARD, width=320)
        now_playing.pack(side=tk.RIGHT, fill=tk.Y)
        now_playing.pack_propagate(False)
        
        # Album art placeholder
        art_frame = tk.Frame(now_playing, bg=Theme.BG_DARK, 
                            width=280, height=280)
        art_frame.pack(pady=20, padx=20)
        art_frame.pack_propagate(False)
        
        # Vinyl animation / Video display
        self.vinyl = tk.Canvas(art_frame, width=280, height=280,
                              bg=Theme.BG_DARK, highlightthickness=0)
        self.vinyl.pack()
        self._draw_vinyl()
        
        # Khởi tạo video player với canvas
        if VIDEO_AVAILABLE:
            self.video_player = VideoPlayer(self.vinyl)
        
        # Song info
        info_frame = tk.Frame(now_playing, bg=Theme.BG_CARD)
        info_frame.pack(fill=tk.X, padx=20)
        
        self.song_title = tk.Label(info_frame, text="No song playing",
                                  font=("Segoe UI", 16, "bold"),
                                  bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY,
                                  wraplength=280)
        self.song_title.pack()
        
        self.song_artist = tk.Label(info_frame, text="Add songs to start",
                                   font=("Segoe UI", 12),
                                   bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY)
        self.song_artist.pack()
        
        # Progress
        progress_frame = tk.Frame(now_playing, bg=Theme.BG_CARD)
        progress_frame.pack(fill=tk.X, padx=20, pady=20)
        
        # Progress slider - sẽ cập nhật max_val khi có bài hát
        self.progress_slider = ModernSlider(progress_frame, width=280, height=24,
                                           min_val=0, max_val=100, value=0,
                                           command=self._on_seek)
        self.progress_slider.pack()
        
        time_frame = tk.Frame(progress_frame, bg=Theme.BG_CARD)
        time_frame.pack(fill=tk.X, pady=5)
        
        self.time_current = tk.Label(time_frame, text="0:00",
                                    font=("Segoe UI", 10),
                                    bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED)
        self.time_current.pack(side=tk.LEFT)
        
        self.time_total = tk.Label(time_frame, text="0:00",
                                  font=("Segoe UI", 10),
                                  bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED)
        self.time_total.pack(side=tk.RIGHT)
        
        # ===== CONTROLS =====
        controls_frame = tk.Frame(now_playing, bg=Theme.BG_CARD)
        controls_frame.pack(pady=10)
        
        # Shuffle button
        self.shuffle_btn = GlowButton(controls_frame, icon="🔀",
                                     width=40, height=40,
                                     fg=Theme.TEXT_MUTED,
                                     command=self.toggle_shuffle)
        self.shuffle_btn.pack(side=tk.LEFT, padx=5)
        
        # Previous
        GlowButton(controls_frame, icon="⏮️",
                  width=50, height=50,
                  command=self.previous_song).pack(side=tk.LEFT, padx=5)
        
        # Play/Pause
        self.play_btn = GlowButton(controls_frame, icon="▶️",
                                  width=70, height=70,
                                  fg=Theme.ACCENT_PRIMARY,
                                  command=self.toggle_play)
        self.play_btn.pack(side=tk.LEFT, padx=10)
        
        # Next
        GlowButton(controls_frame, icon="⏭️",
                  width=50, height=50,
                  command=self.next_song).pack(side=tk.LEFT, padx=5)
        
        # Repeat button
        self.repeat_btn = GlowButton(controls_frame, icon="🔁",
                                    width=40, height=40,
                                    fg=Theme.TEXT_MUTED,
                                    command=self.toggle_repeat)
        self.repeat_btn.pack(side=tk.LEFT, padx=5)
        
        # Volume
        vol_frame = tk.Frame(now_playing, bg=Theme.BG_CARD)
        vol_frame.pack(fill=tk.X, padx=20, pady=20)
        
        tk.Label(vol_frame, text="🔊",
                font=("Segoe UI Symbol", 14),
                bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY).pack(side=tk.LEFT)
        
        self.volume_slider = ModernSlider(vol_frame, width=200, height=20,
                                         min_val=0, max_val=100, value=70,
                                         command=self._on_volume_change)
        self.volume_slider.pack(side=tk.LEFT, padx=10)
        
        # ===== STATUS BAR =====
        status = tk.Frame(self.root, bg=Theme.BG_CARD, height=30)
        status.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Hiển thị MP4 support status
        if PYDUB_AVAILABLE and FFMPEG_AVAILABLE:
            video_status = "✅ Video" if VIDEO_AVAILABLE else "✅ MP4 audio"
            mp4_status = video_status
        elif PYDUB_AVAILABLE:
            mp4_status = "⚠️ MP4 (restart terminal for FFmpeg)"
        else:
            mp4_status = "⚠️ MP4 (need pydub+ffmpeg)"
        self.status_label = tk.Label(status, 
                                    text=f"💡 Tip: Double-click to play | Space to pause | {mp4_status}",
                                    font=("Segoe UI", 9),
                                    bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED)
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        # Linked List info
        self.ll_info = tk.Label(status,
                               text="🔗 Linked List: Empty",
                               font=("Segoe UI", 9),
                               bg=Theme.BG_CARD, fg=Theme.ACCENT_TERTIARY)
        self.ll_info.pack(side=tk.RIGHT, padx=10)
    
    def _draw_vinyl(self, rotation=0):
        """Vẽ đĩa vinyl với animation"""
        self.vinyl.delete("all")
        cx, cy = 140, 140
        
        # Outer ring
        self.vinyl.create_oval(10, 10, 270, 270,
                              fill=Theme.BG_CARD, outline=Theme.TEXT_MUTED, width=2)
        
        # Vinyl grooves
        for r in range(30, 120, 8):
            self.vinyl.create_oval(cx - r, cy - r, cx + r, cy + r,
                                  outline=Theme.TEXT_MUTED, width=1)
        
        # Center label
        self.vinyl.create_oval(cx - 40, cy - 40, cx + 40, cy + 40,
                              fill=Theme.ACCENT_PRIMARY, outline="")
        self.vinyl.create_oval(cx - 8, cy - 8, cx + 8, cy + 8,
                              fill=Theme.BG_DARK, outline="")
        
        # Reflection effect
        import math
        angle = math.radians(rotation)
        x1 = cx + 80 * math.cos(angle)
        y1 = cy + 80 * math.sin(angle)
        x2 = cx + 100 * math.cos(angle)
        y2 = cy + 100 * math.sin(angle)
        self.vinyl.create_line(x1, y1, x2, y2, fill=Theme.TEXT_MUTED, width=3)
    
    # ==================== ACTIONS ====================
    
    def add_songs(self):
        """Thêm bài hát vào playlist"""
        files = filedialog.askopenfilenames(
            title="Select Music Files",
            filetypes=[
                ("Audio/Video Files", "*.mp3 *.wav *.ogg *.flac *.mp4 *.m4a *.aac *.wma"),
                ("MP3", "*.mp3"),
                ("MP4/M4A", "*.mp4 *.m4a"),
                ("WAV", "*.wav"),
                ("All Files", "*.*")
            ]
        )
        
        if files:
            for path in files:
                song = Song.from_path(path)
                self.playlist.append(song)
            
            self._refresh_playlist_view()
            self._update_status(f"✅ Added {len(files)} song(s)")
    
    # ==================== YOUTUBE SUPPORT ====================
    
    def add_from_youtube(self):
        """Thêm bài hát từ YouTube URL"""
        if not YT_DLP_AVAILABLE:
            messagebox.showerror("YouTube Support", 
                               "yt-dlp not installed.\n\n"
                               "Please install: pip install yt-dlp\n\n"
                               "YouTube support requires yt-dlp library.")
            return
        
        # Dialog để nhập YouTube URL
        url = simpledialog.askstring(
            "Add from YouTube",
            "Enter YouTube URL (video or playlist):\n\n"
            "Examples:\n"
            "• https://www.youtube.com/watch?v=VIDEO_ID\n"
            "• https://youtu.be/VIDEO_ID\n"
            "• https://www.youtube.com/playlist?list=PLAYLIST_ID"
        )
        
        if not url:
            return
        
        # Kiểm tra URL hợp lệ
        if not is_youtube_url(url):
            messagebox.showerror("Invalid URL", "Please enter a valid YouTube URL")
            return
        
        # Kiểm tra playlist hay single video
        is_playlist = 'playlist?list=' in url.lower()
        
        if is_playlist:
            # Xử lý playlist
            self._add_youtube_playlist(url)
        else:
            # Xử lý single video
            self._add_youtube_video(url)
    
    def _add_youtube_video(self, url: str):
        """Thêm một video YouTube vào playlist"""
        # Progress window
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Downloading YouTube Video")
        progress_window.geometry("400x150")
        progress_window.configure(bg=Theme.BG_DARK)
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        status_label = tk.Label(progress_window, text="Downloading...",
                               font=("Segoe UI", 11),
                               bg=Theme.BG_DARK, fg=Theme.TEXT_PRIMARY)
        status_label.pack(pady=20)
        
        progress_var = tk.StringVar(value="Starting download...")
        progress_label = tk.Label(progress_window, textvariable=progress_var,
                                 font=("Segoe UI", 9),
                                 bg=Theme.BG_DARK, fg=Theme.TEXT_SECONDARY)
        progress_label.pack(pady=10)
        
        def update_progress(d):
            if d['status'] == 'downloading':
                if 'total_bytes' in d:
                    percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
                    self.root.after(0, lambda: progress_var.set(f"Downloading: {percent:.1f}%"))
                else:
                    self.root.after(0, lambda: progress_var.set("Downloading..."))
            elif d['status'] == 'finished':
                self.root.after(0, lambda: progress_var.set("Processing..."))
        
        def download_thread():
            try:
                file_path = download_youtube(url, self.engine._youtube_dir, update_progress)
                
                # Xử lý metadata trong thread để không block UI
                song = None
                if file_path and os.path.exists(file_path):
                    try:
                        # Tạo Song từ file đã download
                        song = Song.from_path(file_path)
                        # Lấy thông tin từ YouTube URL
                        info = get_youtube_info(url)
                        if info:
                            song.title = info.get('title', song.title)
                            song.artist = info.get('artist', 'YouTube')
                            song.duration = info.get('duration', 0)
                            song.youtube_url = url  # Lưu YouTube URL
                    except Exception as e:
                        print(f"Error processing metadata: {e}")
                
                # Chỉ update UI trên main thread
                self.root.after(0, lambda f=file_path, s=song, u=url, pw=progress_window: 
                               self._on_youtube_downloaded(f, s, u, pw))
            except Exception as e:
                self.root.after(0, lambda err=str(e), pw=progress_window: 
                               self._on_youtube_error(err, pw))
        
        threading.Thread(target=download_thread, daemon=True).start()
    
    def _add_youtube_playlist(self, url: str):
        """Thêm playlist YouTube vào playlist"""
        if not YT_DLP_AVAILABLE:
            return
        
        try:
            entries = get_playlist_entries(url, max_entries=50)
            
            if not entries:
                messagebox.showinfo("Playlist", "Playlist is empty or could not be accessed")
                return
                
                # Hỏi user có muốn download tất cả không
                count = len(entries)
                if count > 10:
                    if not messagebox.askyesno("Large Playlist", 
                                              f"Playlist has {count} videos.\n\n"
                                              f"Download all? (This may take a while)"):
                        return
                
                # Download từng video
                progress_window = tk.Toplevel(self.root)
                progress_window.title("Downloading YouTube Playlist")
                progress_window.geometry("400x150")
                progress_window.configure(bg=Theme.BG_DARK)
                progress_window.transient(self.root)
                progress_window.grab_set()
                
                status_label = tk.Label(progress_window, text=f"Downloading playlist ({count} videos)...",
                                       font=("Segoe UI", 11),
                                       bg=Theme.BG_DARK, fg=Theme.TEXT_PRIMARY)
                status_label.pack(pady=20)
                
                progress_var = tk.StringVar(value="Starting...")
                progress_label = tk.Label(progress_window, textvariable=progress_var,
                                         font=("Segoe UI", 9),
                                         bg=Theme.BG_DARK, fg=Theme.TEXT_SECONDARY)
                progress_label.pack(pady=10)
                
                def download_playlist_thread():
                    downloaded = 0
                    songs_to_add = []  # Collect songs để add sau
                    
                    for i, entry in enumerate(entries):
                        if entry is None:
                            continue
                        
                        video_url = f"https://www.youtube.com/watch?v={entry.get('id', '')}"
                        # Update progress trên main thread
                        self.root.after(0, lambda idx=i+1, total=count: 
                                      progress_var.set(f"Downloading video {idx}/{total}..."))
                        
                        try:
                            file_path = download_youtube(video_url, self.engine._youtube_dir)
                            if file_path and os.path.exists(file_path):
                                # Xử lý metadata trong thread
                                try:
                                    song = Song.from_path(file_path)
                                    # Lấy thông tin từ YouTube
                                    info = get_youtube_info(video_url)
                                    if info:
                                        song.title = info.get('title', song.title)
                                        song.artist = info.get('artist', 'YouTube')
                                        song.duration = info.get('duration', 0)
                                        song.youtube_url = video_url
                                    songs_to_add.append(song)
                                    downloaded += 1
                                except Exception as e:
                                    print(f"Error processing video {i+1}: {e}")
                        except Exception as e:
                            print(f"Error downloading video {i+1}: {e}")
                    
                    # Add tất cả songs cùng lúc trên main thread để tránh block UI nhiều lần
                    def add_all_songs():
                        for song in songs_to_add:
                            self.playlist.append(song)
                        self._refresh_playlist_view()
                    
                    # Sử dụng root.after để đảm bảo UI update
                    self.root.after(0, lambda d=downloaded, t=count, pw=progress_window, cb=add_all_songs: 
                                  self._on_playlist_downloaded(d, t, pw, cb))
                
                threading.Thread(target=download_playlist_thread, daemon=True).start()
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process playlist: {str(e)}")
    
    def _on_youtube_downloaded(self, file_path: Optional[str], song: Optional[Song], url: str, progress_window):
        """Xử lý sau khi download YouTube video xong - chỉ update UI"""
        try:
            # Đóng progress window trước
            if progress_window and progress_window.winfo_exists():
                progress_window.destroy()
        except:
            pass
        
        if file_path and os.path.exists(file_path) and song:
            try:
                # Song đã được xử lý trong thread, chỉ cần thêm vào playlist
                self.playlist.append(song)
                # Refresh playlist view trong background để không block UI
                self.root.after_idle(self._refresh_playlist_view)
                self._update_status(f"✅ Added: {song.title}")
            except Exception as e:
                print(f"Error adding song: {e}")
                self._update_status(f"❌ Error adding video: {str(e)}")
        else:
            self._update_status("❌ Failed to download YouTube video")
    
    def _on_youtube_error(self, error_msg: str, progress_window):
        """Xử lý lỗi download YouTube"""
        try:
            # Đóng progress window trước
            if progress_window and progress_window.winfo_exists():
                progress_window.destroy()
        except:
            pass
        
        try:
            messagebox.showerror("Download Error", f"Failed to download:\n{error_msg}")
        except:
            pass
        
        self._update_status("❌ YouTube download failed")
    
    def _on_playlist_downloaded(self, downloaded: int, total: int, progress_window, add_songs_callback=None):
        """Xử lý sau khi download playlist xong"""
        try:
            # Đóng progress window trước
            if progress_window and progress_window.winfo_exists():
                progress_window.destroy()
        except:
            pass
        
        # Add songs nếu có callback
        if add_songs_callback:
            add_songs_callback()
        else:
            self._refresh_playlist_view()
        
        self._update_status(f"✅ Downloaded {downloaded}/{total} videos from YouTube playlist")
    
    def _refresh_playlist_view(self):
        """Cập nhật Treeview từ Linked List - optimized để không block UI"""
        try:
            # Xóa cũ
            for item in self.playlist_tree.get_children():
                self.playlist_tree.delete(item)
            
            # Thêm mới từ linked list - batch để tránh block UI
            items_to_add = []
            for i, song in enumerate(self.playlist):
                # Thêm icon YouTube nếu có YouTube URL
                title_display = song.title
                if hasattr(song, 'youtube_url') and song.youtube_url:
                    title_display = "📺 " + title_display
                
                items_to_add.append((title_display, song.artist, song == self.playlist.current_song))
            
            # Insert tất cả cùng lúc
            for i, (title, artist, is_current) in enumerate(items_to_add):
                item_id = self.playlist_tree.insert("", tk.END,
                                                    values=(title, artist))
                
                # Highlight current song
                if is_current:
                    self.playlist_tree.selection_set(item_id)
                    self.playlist_tree.see(item_id)
            
            # Update count
            if hasattr(self, 'playlist_count'):
                self.playlist_count.config(text=f"{len(self.playlist)} songs")
            self._update_ll_info()
        except Exception as e:
            print(f"Error refreshing playlist view: {e}")
    
    def _on_song_double_click(self, event):
        """Xử lý double-click vào bài hát"""
        selection = self.playlist_tree.selection()
        if selection:
            item = selection[0]
            index = self.playlist_tree.index(item)
            self.playlist.go_to(index)
            self.play_current_song()
    
    def _on_delete_song(self, event):
        """Xóa bài hát được chọn"""
        selection = self.playlist_tree.selection()
        if selection:
            item = selection[0]
            index = self.playlist_tree.index(item)
            song = self.playlist.remove_at(index)
            if song:
                self._refresh_playlist_view()
                self._update_status(f"🗑️ Removed: {song.title}")
    
    def toggle_play(self):
        """Play/Pause"""
        if self.playlist.is_empty:
            return
        
        if not self.engine.is_playing:
            # Chưa playing, bắt đầu phát
            if not self.engine.is_paused:
                self.play_current_song()
            else:
                # Đang pause, resume
                self.engine.play()
                # Resume video
                if self.video_player and self.engine._has_video:
                    self.video_player.resume()
                self.play_btn.icon = "⏸️"
                self.play_btn._draw()
        else:
            # Đang playing, pause
            if self.engine.is_paused:
                # Đang pause, resume
                self.engine.play()
                if self.video_player and self.engine._has_video:
                    self.video_player.resume()
                self.play_btn.icon = "⏸️"
                self.play_btn._draw()
            else:
                # Đang playing, pause
                self.engine.pause()
                # Pause video
                if self.video_player and self.engine._has_video:
                    self.video_player.pause()
                self.play_btn.icon = "▶️"
                self.play_btn._draw()
    
    def next_song(self):
        """Bài tiếp theo"""
        if self.playlist.is_empty:
            return
        
        # Dừng engine và video hiện tại
        self.engine.stop()
        if self.video_player:
            self.video_player.stop()
        
        if self.shuffle_mode:
            # Random trong linked list
            if len(self.playlist) > 1:
                index = random.randint(0, len(self.playlist) - 1)
                while index == self.playlist.current_index:
                    index = random.randint(0, len(self.playlist) - 1)
                self.playlist.go_to(index)
            else:
                # Chỉ có 1 bài, không cần chuyển
                pass
        else:
            next_song = self.playlist.next()
            if not next_song:
                # Không có bài tiếp theo
                self._update_status("⏹️ End of playlist")
                return
        
        self.play_current_song()
    
    def previous_song(self):
        """Bài trước"""
        if self.playlist.is_empty:
            return
        
        # Dừng engine và video hiện tại
        self.engine.stop()
        if self.video_player:
            self.video_player.stop()
        
        prev_song = self.playlist.previous()
        if not prev_song:
            # Không có bài trước
            self._update_status("⏹️ Beginning of playlist")
            return
        
        self.play_current_song()
    
    def toggle_shuffle(self):
        """Bật/tắt shuffle"""
        self.shuffle_mode = not self.shuffle_mode
        color = Theme.ACCENT_PRIMARY if self.shuffle_mode else Theme.TEXT_MUTED
        self.shuffle_btn.fg_color = color
        self.shuffle_btn._draw()
        
        self._update_status(f"🔀 Shuffle: {'ON' if self.shuffle_mode else 'OFF'}")
    
    def toggle_repeat(self):
        """Chuyển chế độ repeat"""
        self.repeat_mode = (self.repeat_mode + 1) % 3
        
        icons = ["🔁", "🔂", "🔂"]  # Off, All, One
        colors = [Theme.TEXT_MUTED, Theme.ACCENT_PRIMARY, Theme.ACCENT_SECONDARY]
        
        self.repeat_btn.icon = icons[self.repeat_mode]
        self.repeat_btn.fg_color = colors[self.repeat_mode]
        self.repeat_btn._draw()
        
        # Update linked list circular mode
        self.playlist.circular = (self.repeat_mode == 1)
        
        modes = ["OFF", "REPEAT ALL", "REPEAT ONE"]
        self._update_status(f"🔁 Repeat: {modes[self.repeat_mode]}")
    
    def shuffle_playlist(self):
        """Xáo trộn playlist"""
        if len(self.playlist) > 1:
            self.playlist.shuffle()
            self._refresh_playlist_view()
            self._update_status("🔀 Playlist shuffled!")
    
    def clear_playlist(self):
        """Xóa toàn bộ playlist"""
        if self.playlist.is_empty:
            return
        
        if messagebox.askyesno("Clear Playlist", "Are you sure you want to clear the playlist?"):
            self.engine.stop()
            if self.video_player:
                self.video_player.stop()
            self.playlist.clear()
            self._refresh_playlist_view()
            self.song_title.config(text="No song playing")
            self.song_artist.config(text="Add songs to start")
            self._draw_vinyl()  # Vẽ lại vinyl
            self._update_status("🗑️ Playlist cleared")
    
    def _on_seek(self, value):
        """Seek trong bài hát - reload và play từ vị trí mới"""
        if not hasattr(self.engine, 'duration') or not self.engine.duration or self.engine.duration <= 0:
            return
        
        # value từ slider là giây (vì max_val = duration)
        position_seconds = max(0, min(value, self.engine.duration))
        
        # Nếu đang phát hoặc đã load, cần reload để seek chính xác
        song = self.playlist.current_song
        if not song:
            return
        
        was_playing = self.engine.is_playing and not self.engine.is_paused
        
        # Dừng hiện tại
        self.engine.stop()
        if self.video_player:
            self.video_player.stop()
        
        # Load lại file
        if self.engine.load(song.path):
            # Seek video trước (nếu có)
            if self.video_player and self.engine._has_video and self.engine._video_path:
                self.video_player.open(self.engine._video_path)
                self.video_player.seek(position_seconds)
            
            # Play từ vị trí mới
            if was_playing:
                # Thử play từ vị trí cụ thể
                self.engine.play(start_pos=position_seconds)
                if self.video_player and self.engine._has_video:
                    self.video_player.play()
            else:
                # Chỉ set position, không play
                self.engine.current_pos = position_seconds
                if self.video_player and self.engine._has_video:
                    self.video_player.seek(position_seconds)
                    self.video_player.pause()
            
            # Cập nhật UI - đảm bảo slider không bị reset
            self.progress_slider.value = position_seconds
            self.time_current.config(text=self._format_time(position_seconds))
            # Cập nhật current_pos trong engine để get_pos() trả về đúng
            self.engine.current_pos = position_seconds
    
    def _on_volume_change(self, value):
        """Thay đổi volume"""
        self.engine.volume = value / 100
    
    # ==================== UPDATE LOOP ====================
    
    def _start_update_loop(self):
        """Bắt đầu thread cập nhật UI"""
        def update():
            vinyl_rotation = 0
            while self.running:
                try:
                    # Update progress khi đang playing (không pause)
                    if self.engine.is_playing and not self.engine.is_paused:
                        # Với video, cần sync với video player
                        if self.engine._has_video and self.video_player and self.video_player.is_playing:
                            # Lấy position từ audio engine
                            pos = self.engine.get_pos()
                            # Sync video với audio
                            self.video_player.sync_with_audio(pos)
                        elif self.engine.is_active():
                            # Chỉ audio, lấy position từ engine
                            pos = self.engine.get_pos()
                        else:
                            # Engine không active nhưng đang playing (có thể đang load)
                            pos = self.engine.current_pos
                        
                        # Cập nhật slider (đảm bảo max_val đã được set)
                        if self.progress_slider.max_val > 0:
                            self.progress_slider.value = min(pos, self.progress_slider.max_val)
                        self.time_current.config(text=self._format_time(pos))
                        
                        # Rotate vinyl chỉ khi không có video
                        if not self.engine._has_video:
                            vinyl_rotation = (vinyl_rotation + 2) % 360
                            self._draw_vinyl(vinyl_rotation)
                    
                    # Check if song ended - CHỈ khi đang playing và KHÔNG pause
                    # Với video, cần check cả video player
                    if self.engine.is_playing and not self.engine.is_paused:
                        if self.engine._has_video and self.video_player:
                            # Với video, check cả video player và audio engine
                            if not self.video_player.is_playing and not self.engine.is_active():
                                self.root.after(0, self._on_song_end)
                        elif not self.engine.is_active():
                            # Chỉ audio, check engine
                            self.root.after(0, self._on_song_end)
                    
                    time.sleep(0.05)
                except:
                    break
        
        self.update_thread = threading.Thread(target=update, daemon=True)
        self.update_thread.start()
    
    def _on_song_end(self):
        """Xử lý khi bài hát kết thúc"""
        # Update total time
        if self.engine.duration > 0:
            self.stats["total_time"] = self.stats.get("total_time", 0) + self.engine.duration
        
        # Dừng video player
        if self.video_player:
            self.video_player.stop()
        
        if self.repeat_mode == 2:
            # Repeat one
            self.play_current_song()
        elif self.playlist.has_next():
            self.next_song()
        else:
            # End of playlist
            self.engine.is_playing = False
            self.play_btn.icon = "▶️"
            self.play_btn._draw()
    
    def _update_status(self, message: str):
        """Cập nhật status bar"""
        self.status_label.config(text=message)
    
    def _update_ll_info(self):
        """Cập nhật thông tin Linked List - THỂ HIỆN RÕ RÀNG CẤU TRÚC DỮ LIỆU"""
        size = len(self.playlist)
        if size == 0:
            self.ll_info.config(text="🔗 Linked List: Empty | Press Ctrl+L to visualize")
            return
        
        current = self.playlist.current_index + 1 if size > 0 else 0
        mode = "Circular" if self.playlist.circular else "Linear"
        has_next = "✓" if self.playlist.has_next() else "✗"
        has_prev = "✓" if self.playlist.has_previous() else "✗"
        
        # Hiển thị thông tin chi tiết hơn
        info = f"🔗 LL: {size} nodes | Head→Tail | Current: {current} | Next:{has_next} Prev:{has_prev} | {mode}"
        self.ll_info.config(text=info)
    
    def _format_time(self, seconds: float) -> str:
        """Format thời gian mm:ss"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"
    
    # ==================== NEW FEATURES ====================
    
    def save_playlist(self):
        """Lưu playlist hiện tại"""
        self._save_all_data()
        self._update_status("💾 Playlist saved!")
    
    def load_playlist(self):
        """Load playlist đã lưu"""
        if messagebox.askyesno("Load Playlist", "Load saved playlist? Current playlist will be replaced."):
            self._load_saved_data()
            self._refresh_playlist_view()
            self._update_status("📂 Playlist loaded!")
    
    def export_playlist(self):
        """Export playlist ra file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Export Playlist"
        )
        if filename:
            if self.playlist.save_to_file(filename):
                self._update_status(f"✅ Exported to {os.path.basename(filename)}")
            else:
                self._update_status("❌ Export failed!")
    
    def import_playlist(self):
        """Import playlist từ file"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Import Playlist"
        )
        if filename:
            imported = PlaylistLinkedList.load_from_file(filename)
            if imported:
                if messagebox.askyesno("Import", "Replace current playlist or append?"):
                    self.playlist = imported
                else:
                    for song in imported:
                        self.playlist.append(song)
                self._refresh_playlist_view()
                self._update_status("✅ Imported successfully!")
            else:
                self._update_status("❌ Import failed!")
    
    def search_song(self):
        """Tìm kiếm bài hát trong playlist"""
        query = simpledialog.askstring("Search", "Enter song name or artist:")
        if query:
            query_lower = query.lower()
            found = False
            for i, song in enumerate(self.playlist):
                if query_lower in song.title.lower() or query_lower in song.artist.lower():
                    self.playlist.go_to(i)
                    self._refresh_playlist_view()
                    # Highlight found song
                    items = self.playlist_tree.get_children()
                    if i < len(items):
                        self.playlist_tree.selection_set(items[i])
                        self.playlist_tree.see(items[i])
                    found = True
                    break
            if found:
                self._update_status(f"🔍 Found: {query}")
            else:
                messagebox.showinfo("Search", f"No song found matching '{query}'")
    
    def _on_right_click(self, event):
        """Menu khi right-click vào bài hát"""
        item = self.playlist_tree.identify_row(event.y)
        if item:
            index = self.playlist_tree.index(item)
            self.playlist.go_to(index)
            song = self.playlist.current_song
            
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(label=f"▶️ Play: {song.title}", command=self.play_current_song)
            menu.add_separator()
            
            # Thêm option mở YouTube nếu có YouTube URL
            if song and hasattr(song, 'youtube_url') and song.youtube_url:
                menu.add_command(label="📺 Open in YouTube", 
                               command=lambda: self._open_youtube_in_browser(song.youtube_url))
                menu.add_separator()
            
            menu.add_command(label="❤️ Add to Favorites", command=self.add_to_favorites)
            menu.add_command(label="➡️ Remove from Favorites", command=self.remove_from_favorites)
            menu.add_separator()
            menu.add_command(label="🗑️ Delete from Playlist", command=lambda: self._delete_at_index(index))
            
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()
    
    def _open_youtube_in_browser(self, url: str):
        """Mở YouTube video trong browser (như Notion embed)"""
        webbrowser.open(url)
    
    def add_to_favorites(self):
        """Thêm bài hát hiện tại vào favorites"""
        song = self.playlist.current_song
        if not song:
            return
        
        # Kiểm tra đã có chưa
        if song not in self.favorites:
            self.favorites.append(song)
            self._update_status(f"❤️ Added to favorites: {song.title}")
        else:
            self._update_status(f"💚 Already in favorites: {song.title}")
    
    def remove_from_favorites(self):
        """Xóa bài hát khỏi favorites"""
        song = self.playlist.current_song
        if not song:
            return
        
        # Tìm và xóa trong favorites
        for i, fav_song in enumerate(self.favorites):
            if fav_song.path == song.path:
                self.favorites.remove_at(i)
                self._update_status(f"💔 Removed from favorites: {song.title}")
                return
        
        self._update_status("❌ Not in favorites")
    
    def show_favorites(self):
        """Hiển thị cửa sổ favorites"""
        fav_window = tk.Toplevel(self.root)
        fav_window.title("❤️ Favorites")
        fav_window.geometry("500x400")
        fav_window.configure(bg=Theme.BG_DARK)
        
        header = tk.Frame(fav_window, bg=Theme.BG_CARD, pady=10)
        header.pack(fill=tk.X)
        tk.Label(header, text=f"❤️ Favorites ({len(self.favorites)} songs)",
                font=("Segoe UI", 14, "bold"),
                bg=Theme.BG_CARD, fg=Theme.ACCENT_SECONDARY).pack()
        
        # Listbox
        listbox_frame = tk.Frame(fav_window, bg=Theme.BG_DARK)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        fav_listbox = tk.Listbox(listbox_frame,
                                bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY,
                                font=("Segoe UI", 11),
                                selectbackground=Theme.ACCENT_PRIMARY,
                                yscrollcommand=scrollbar.set)
        scrollbar.config(command=fav_listbox.yview)
        
        for song in self.favorites:
            fav_listbox.insert(tk.END, str(song))
        
        fav_listbox.pack(fill=tk.BOTH, expand=True)
        
        def play_selected():
            selection = fav_listbox.curselection()
            if selection:
                idx = selection[0]
                fav_song = list(self.favorites)[idx]
                # Tìm trong playlist chính
                for i, song in enumerate(self.playlist):
                    if song.path == fav_song.path:
                        self.playlist.go_to(i)
                        self.play_current_song()
                        fav_window.destroy()
                        return
        
        fav_listbox.bind("<Double-1>", lambda e: play_selected())
        
        # Buttons
        btn_frame = tk.Frame(fav_window, bg=Theme.BG_DARK)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="▶️ Play", command=play_selected,
                 bg=Theme.ACCENT_PRIMARY, fg=Theme.BG_DARK,
                 font=("Segoe UI", 10, "bold"),
                 padx=20, pady=5, border=0).pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="🗑️ Clear All", 
                 command=lambda: self._clear_favorites(fav_window, fav_listbox),
                 bg=Theme.BG_HOVER, fg=Theme.TEXT_PRIMARY,
                 font=("Segoe UI", 10),
                 padx=20, pady=5, border=0).pack(side=tk.LEFT, padx=5)
    
    def _clear_favorites(self, window, listbox):
        """Xóa tất cả favorites"""
        if messagebox.askyesno("Clear Favorites", "Remove all favorites?"):
            self.favorites.clear()
            listbox.delete(0, tk.END)
            self._update_status("💔 Cleared all favorites")
    
    def _delete_at_index(self, index):
        """Xóa bài hát tại index"""
        song = self.playlist.remove_at(index)
        if song:
            self._refresh_playlist_view()
            self._update_status(f"🗑️ Removed: {song.title}")
    
    def show_stats(self):
        """Hiển thị thống kê"""
        stats_window = tk.Toplevel(self.root)
        stats_window.title("📊 Statistics")
        stats_window.geometry("400x300")
        stats_window.configure(bg=Theme.BG_DARK)
        
        content = tk.Frame(stats_window, bg=Theme.BG_CARD, padx=20, pady=20)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(content, text="📊 PLAYER STATISTICS",
                font=("Segoe UI", 16, "bold"),
                bg=Theme.BG_CARD, fg=Theme.ACCENT_PRIMARY).pack(pady=10)
        
        stats_text = f"""
🎵 Total Songs: {len(self.playlist)}
❤️ Favorites: {len(self.favorites)}
▶️ Total Played: {self.stats.get('total_played', 0)}
⏱️ Total Time: {self._format_time(self.stats.get('total_time', 0))}
📅 Last Played: {self.stats.get('last_played', 'Never')}
        """
        
        tk.Label(content, text=stats_text.strip(),
                font=("Segoe UI", 11),
                bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY,
                justify=tk.LEFT).pack(anchor=tk.W, pady=10)
        
        tk.Button(content, text="Reset Stats",
                 command=lambda: self._reset_stats(stats_window),
                 bg=Theme.BG_HOVER, fg=Theme.TEXT_PRIMARY,
                 font=("Segoe UI", 10),
                 padx=20, pady=5, border=0).pack(pady=10)
    
    def _reset_stats(self, window):
        """Reset statistics"""
        if messagebox.askyesno("Reset", "Reset all statistics?"):
            self.stats = {
                "total_played": 0,
                "total_time": 0.0,
                "last_played": None
            }
            window.destroy()
            self.show_stats()
            self._update_status("📊 Statistics reset")
    
    def play_current_song(self):
        """Phát bài hát hiện tại"""
        song = self.playlist.current_song
        if not song:
            return
        
        # Kiểm tra định dạng cần convert
        ext = os.path.splitext(song.path)[1].lower()
        needs_convert = ext in MusicEngine.CONVERT_FORMATS
        
        if self.engine.load(song.path):
            self.engine.play()
            
            # Mở video player nếu có video
            if self.engine._has_video and self.video_player and self.engine._video_path:
                self.video_player.open(self.engine._video_path)
            else:
                # Không có video, vẽ vinyl
                self._draw_vinyl()
            
            # Update stats
            self.stats["total_played"] = self.stats.get("total_played", 0) + 1
            self.stats["last_played"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            # Update UI
            self.song_title.config(text=song.title)
            self.song_artist.config(text=song.artist)
            self.play_btn.icon = "⏸️"
            self.play_btn._draw()
            
            # Update progress
            self.progress_slider.max_val = self.engine.duration if self.engine.duration > 0 else 100
            self.progress_slider.value = 0  # Reset về đầu
            self.time_total.config(text=self._format_time(self.engine.duration))
            self.time_current.config(text="0:00")  # Reset thời gian hiện tại
            
            self._refresh_playlist_view()
            
            # Status với thông tin convert
            convert_info = f" (converted from {ext})" if needs_convert and self.engine._temp_file else ""
            video_info = " 🎬 [Video]" if self.engine._has_video else ""
            self._update_status(f"▶️ Now playing: {song}{convert_info}{video_info}")
        else:
            if needs_convert:
                if not PYDUB_AVAILABLE:
                    self._update_status(f"❌ Cannot play {ext}: Install pydub (pip install pydub)")
                elif not FFMPEG_AVAILABLE:
                    self._update_status(f"❌ Cannot play {ext}: Restart terminal for FFmpeg")
                else:
                    self._update_status(f"❌ Error converting: {song.title}")
            else:
                self._update_status(f"❌ Error loading: {song.title}")
    
    def _on_close(self):
        """Xử lý đóng app"""
        self.running = False
        self.engine.stop()
        
        # Dừng video player
        if self.video_player:
            self.video_player.stop()
        
        # Lưu dữ liệu trước khi đóng
        self._save_all_data()
        
        # Dọn dẹp thư mục temp
        temp_dir = self.engine._temp_dir
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
        
        self.root.destroy()
    
    # ==================== LINKED LIST VISUALIZATION & OPERATIONS ====================
    # CÁC TÍNH NĂNG NÀY THỂ HIỆN RÕ RÀNG KHẢ NĂNG CỦA LINKED LIST
    
    def show_linked_list_visualization(self):
        """Hiển thị cửa sổ visualization Linked List - THỂ HIỆN CẤU TRÚC DỮ LIỆU"""
        vis_window = tk.Toplevel(self.root)
        vis_window.title("🔗 Linked List Visualization")
        vis_window.geometry("900x600")
        vis_window.configure(bg=Theme.BG_DARK)
        
        # Header
        header = tk.Frame(vis_window, bg=Theme.BG_CARD, pady=15)
        header.pack(fill=tk.X, padx=10, pady=10)
        tk.Label(header, text="🔗 DOUBLY LINKED LIST VISUALIZATION",
                font=("Segoe UI", 16, "bold"),
                bg=Theme.BG_CARD, fg=Theme.ACCENT_PRIMARY).pack()
        tk.Label(header, text="Hiển thị cấu trúc Linked List với Head, Tail, Current Node và các pointers",
                font=("Segoe UI", 10),
                bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY).pack(pady=5)
        
        # Canvas để vẽ Linked List
        canvas_frame = tk.Frame(vis_window, bg=Theme.BG_DARK)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(canvas_frame, bg=Theme.BG_CARD, highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Vẽ Linked List
        self._draw_linked_list(canvas)
        
        # Info panel
        info_frame = tk.Frame(vis_window, bg=Theme.BG_CARD, padx=15, pady=10)
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        info_text = f"""
📊 Linked List Info:
   • Size: {len(self.playlist)} nodes
   • Head: {self.playlist._head.data.title if self.playlist._head else "None"}
   • Tail: {self.playlist._tail.data.title if self.playlist._tail else "None"}
   • Current: {self.playlist.current_song.title if self.playlist.current_song else "None"} (Index: {self.playlist.current_index})
   • Circular Mode: {'ON' if self.playlist.circular else 'OFF'}
   • Empty: {self.playlist.is_empty}
        """
        
        tk.Label(info_frame, text=info_text.strip(),
                font=("Segoe UI", 10),
                bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY,
                justify=tk.LEFT).pack(anchor=tk.W)
        
        # Refresh button
        def refresh():
            canvas.delete("all")
            self._draw_linked_list(canvas)
            # Update info
            info_text = f"""
📊 Linked List Info:
   • Size: {len(self.playlist)} nodes
   • Head: {self.playlist._head.data.title if self.playlist._head else "None"}
   • Tail: {self.playlist._tail.data.title if self.playlist._tail else "None"}
   • Current: {self.playlist.current_song.title if self.playlist.current_song else "None"} (Index: {self.playlist.current_index})
   • Circular Mode: {'ON' if self.playlist.circular else 'OFF'}
   • Empty: {self.playlist.is_empty}
            """
            for widget in info_frame.winfo_children():
                widget.destroy()
            tk.Label(info_frame, text=info_text.strip(),
                    font=("Segoe UI", 10),
                    bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY,
                    justify=tk.LEFT).pack(anchor=tk.W)
        
        btn_frame = tk.Frame(vis_window, bg=Theme.BG_DARK)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="🔄 Refresh", command=refresh,
                 bg=Theme.ACCENT_PRIMARY, fg=Theme.BG_DARK,
                 font=("Segoe UI", 10, "bold"),
                 padx=20, pady=5, border=0, cursor="hand2").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Close", command=vis_window.destroy,
                 bg=Theme.BG_HOVER, fg=Theme.TEXT_PRIMARY,
                 font=("Segoe UI", 10),
                 padx=20, pady=5, border=0, cursor="hand2").pack(side=tk.LEFT, padx=5)
    
    def _draw_linked_list(self, canvas):
        """Vẽ Linked List trên Canvas"""
        if self.playlist.is_empty:
            canvas.create_text(450, 200, text="Linked List is Empty",
                             font=("Segoe UI", 16),
                             fill=Theme.TEXT_MUTED)
            return
        
        # Kích thước node
        node_width = 200
        node_height = 80
        node_spacing = 250
        start_x = 50
        start_y = 50
        
        # Vẽ từng node
        node = self.playlist._head
        x = start_x
        y = start_y
        nodes = []
        
        while node:
            # Xác định màu node
            is_current = (node == self.playlist._current)
            is_head = (node == self.playlist._head)
            is_tail = (node == self.playlist._tail)
            
            if is_current:
                node_color = Theme.ACCENT_PRIMARY
                border_color = Theme.ACCENT_SECONDARY
                border_width = 3
            elif is_head or is_tail:
                node_color = Theme.ACCENT_TERTIARY
                border_color = Theme.ACCENT_PRIMARY
                border_width = 2
            else:
                node_color = Theme.BG_HOVER
                border_color = Theme.TEXT_MUTED
                border_width = 1
            
            # Vẽ node (rounded rectangle)
            x1, y1 = x, y
            x2, y2 = x + node_width, y + node_height
            
            # Background
            canvas.create_rectangle(x1, y1, x2, y2,
                                  fill=node_color, outline=border_color,
                                  width=border_width)
            
            # Labels
            labels = []
            if is_head:
                labels.append("HEAD")
            if is_tail:
                labels.append("TAIL")
            if is_current:
                labels.append("CURRENT")
            
            if labels:
                canvas.create_text(x + node_width // 2, y + 15,
                                 text=" | ".join(labels),
                                 font=("Segoe UI", 8, "bold"),
                                 fill=Theme.BG_DARK)
            
            # Song info
            song_text = node.data.title[:25] + "..." if len(node.data.title) > 25 else node.data.title
            canvas.create_text(x + node_width // 2, y + node_height // 2,
                             text=song_text,
                             font=("Segoe UI", 10, "bold"),
                             fill=Theme.TEXT_PRIMARY if is_current else Theme.TEXT_SECONDARY)
            
            canvas.create_text(x + node_width // 2, y + node_height - 20,
                             text=node.data.artist[:20] + "..." if len(node.data.artist) > 20 else node.data.artist,
                             font=("Segoe UI", 9),
                             fill=Theme.TEXT_MUTED)
            
            # Lưu vị trí node
            nodes.append({
                'node': node,
                'x': x + node_width // 2,
                'y': y + node_height // 2,
                'x1': x1, 'y1': y1,
                'x2': x2, 'y2': y2
            })
            
            # Vẽ pointer next (mũi tên sang phải)
            if node.next:
                arrow_x = x2
                arrow_y = y + node_height // 2
                arrow_end_x = x + node_spacing
                arrow_end_y = arrow_y
                
                # Đường thẳng
                canvas.create_line(arrow_x, arrow_y, arrow_end_x - 20, arrow_end_y,
                                 fill=Theme.ACCENT_PRIMARY, width=2, arrow=tk.LAST)
                
                # Label "next"
                canvas.create_text((arrow_x + arrow_end_x) // 2, arrow_y - 15,
                                 text="next",
                                 font=("Segoe UI", 8),
                                 fill=Theme.ACCENT_PRIMARY)
            
            # Vẽ pointer prev (mũi tên từ phải sang trái, ở phía trên)
            if node.prev:
                arrow_x = x
                arrow_y = y - 20
                arrow_end_x = x - node_spacing + node_width
                arrow_end_y = arrow_y
                
                # Đường thẳng
                canvas.create_line(arrow_x, arrow_y, arrow_end_x + 20, arrow_end_y,
                                 fill=Theme.ACCENT_SECONDARY, width=2, arrow=tk.LAST)
                
                # Label "prev"
                canvas.create_text((arrow_x + arrow_end_x) // 2, arrow_y - 10,
                                 text="prev",
                                 font=("Segoe UI", 8),
                                 fill=Theme.ACCENT_SECONDARY)
            
            x += node_spacing
            node = node.next
            
            # Xuống dòng nếu quá rộng
            if x + node_width > 850:
                x = start_x
                y += node_height + 50
        
        # Update scroll region
        canvas.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
    
    def show_linked_list_operations(self):
        """Panel thao tác Linked List - THỂ HIỆN CÁC OPERATIONS"""
        ops_window = tk.Toplevel(self.root)
        ops_window.title("⚙️ Linked List Operations")
        ops_window.geometry("500x400")
        ops_window.configure(bg=Theme.BG_DARK)
        
        header = tk.Frame(ops_window, bg=Theme.BG_CARD, pady=15)
        header.pack(fill=tk.X, padx=10, pady=10)
        tk.Label(header, text="⚙️ LINKED LIST OPERATIONS",
                font=("Segoe UI", 16, "bold"),
                bg=Theme.BG_CARD, fg=Theme.ACCENT_PRIMARY).pack()
        tk.Label(header, text="Các thao tác cơ bản của Doubly Linked List",
                font=("Segoe UI", 10),
                bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY).pack(pady=5)
        
        content = tk.Frame(ops_window, bg=Theme.BG_DARK)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Operations list
        ops_text = """
📋 Các Operations đã implement:

✅ O(1) Operations:
   • append(song) - Thêm vào cuối
   • prepend(song) - Thêm vào đầu
   • next() - Chuyển đến node tiếp theo
   • previous() - Chuyển đến node trước
   • remove_current() - Xóa node hiện tại

✅ O(n) Operations:
   • insert_at(index, song) - Chèn tại vị trí
   • remove_at(index) - Xóa tại vị trí
   • go_to(index) - Nhảy đến index
   • find_by_title(title) - Tìm kiếm

✅ Special Features:
   • Circular mode - Lặp playlist
   • Shuffle - Xáo trộn
   • Save/Load - Lưu trữ
        """
        
        tk.Label(content, text=ops_text.strip(),
                font=("Segoe UI", 10),
                bg=Theme.BG_DARK, fg=Theme.TEXT_PRIMARY,
                justify=tk.LEFT).pack(anchor=tk.W, pady=10)
        
        # Buttons
        btn_frame = tk.Frame(content, bg=Theme.BG_DARK)
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="➕ Insert at Position",
                 command=self.insert_song_at_position,
                 bg=Theme.ACCENT_PRIMARY, fg=Theme.BG_DARK,
                 font=("Segoe UI", 10, "bold"),
                 padx=15, pady=8, border=0, cursor="hand2").pack(pady=5, fill=tk.X)
        
        tk.Button(btn_frame, text="➖ Delete at Position",
                 command=self.delete_song_at_position,
                 bg=Theme.ACCENT_SECONDARY, fg=Theme.TEXT_PRIMARY,
                 font=("Segoe UI", 10, "bold"),
                 padx=15, pady=8, border=0, cursor="hand2").pack(pady=5, fill=tk.X)
        
        tk.Button(btn_frame, text="📊 View Visualization",
                 command=self.show_linked_list_visualization,
                 bg=Theme.ACCENT_TERTIARY, fg=Theme.TEXT_PRIMARY,
                 font=("Segoe UI", 10, "bold"),
                 padx=15, pady=8, border=0, cursor="hand2").pack(pady=5, fill=tk.X)
        
        tk.Button(btn_frame, text="Close", command=ops_window.destroy,
                 bg=Theme.BG_HOVER, fg=Theme.TEXT_PRIMARY,
                 font=("Segoe UI", 10),
                 padx=15, pady=8, border=0, cursor="hand2").pack(pady=5, fill=tk.X)
    
    def show_linked_list_info(self):
        """Hiển thị thông tin chi tiết về Linked List"""
        info_window = tk.Toplevel(self.root)
        info_window.title("ℹ️ Linked List Information")
        info_window.geometry("600x500")
        info_window.configure(bg=Theme.BG_DARK)
        
        header = tk.Frame(info_window, bg=Theme.BG_CARD, pady=15)
        header.pack(fill=tk.X, padx=10, pady=10)
        tk.Label(header, text="ℹ️ LINKED LIST INFORMATION",
                font=("Segoe UI", 16, "bold"),
                bg=Theme.BG_CARD, fg=Theme.ACCENT_PRIMARY).pack()
        
        content = tk.Frame(info_window, bg=Theme.BG_CARD, padx=20, pady=20)
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Thông tin chi tiết
        current_idx = self.playlist.current_index
        head_song = self.playlist._head.data if self.playlist._head else None
        tail_song = self.playlist._tail.data if self.playlist._tail else None
        current_song = self.playlist.current_song
        
        info_text = f"""
📊 CẤU TRÚC LINKED LIST:

🔹 Size: {len(self.playlist)} nodes
🔹 Empty: {self.playlist.is_empty}
🔹 Circular Mode: {'ON' if self.playlist.circular else 'OFF'}

📍 POINTERS:
   • Head: {head_song.title if head_song else "None"} ({head_song.artist if head_song else ""})
   • Tail: {tail_song.title if tail_song else "None"} ({tail_song.artist if tail_song else ""})
   • Current: {current_song.title if current_song else "None"} (Index: {current_idx})
   • Current has next: {self.playlist.has_next()}
   • Current has prev: {self.playlist.has_previous()}

⚡ TIME COMPLEXITY:
   • next() / previous(): O(1) ✅
   • append() / prepend(): O(1) ✅
   • remove_current(): O(1) ✅
   • insert_at() / remove_at(): O(n) ⚠️
   • go_to(index): O(n) ⚠️ (tối ưu từ 2 phía)

🔗 LINKED LIST STRUCTURE:
   Node:
   ┌─────────────┐
   │   prev      │ ←─ Doubly Linked
   │   data      │
   │   next      │ →─ Doubly Linked
   └─────────────┘
        """
        
        tk.Label(content, text=info_text.strip(),
                font=("Segoe UI", 10),
                bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY,
                justify=tk.LEFT).pack(anchor=tk.W)
        
        # List all nodes
        if not self.playlist.is_empty:
            tk.Label(content, text="\n📋 ALL NODES (in order):",
                    font=("Segoe UI", 11, "bold"),
                    bg=Theme.BG_CARD, fg=Theme.ACCENT_PRIMARY).pack(anchor=tk.W, pady=(20, 10))
            
            listbox_frame = tk.Frame(content, bg=Theme.BG_CARD)
            listbox_frame.pack(fill=tk.BOTH, expand=True)
            
            scrollbar = tk.Scrollbar(listbox_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            listbox = tk.Listbox(listbox_frame,
                               bg=Theme.BG_DARK, fg=Theme.TEXT_PRIMARY,
                               font=("Segoe UI", 9),
                               yscrollcommand=scrollbar.set,
                               selectbackground=Theme.ACCENT_PRIMARY)
            scrollbar.config(command=listbox.yview)
            
            for i, song in enumerate(self.playlist):
                marker = "👉 " if i == current_idx else "   "
                listbox.insert(tk.END, f"{marker}[{i}] {song.title} - {song.artist}")
            
            listbox.pack(fill=tk.BOTH, expand=True)
        
        tk.Button(content, text="Close", command=info_window.destroy,
                 bg=Theme.BG_HOVER, fg=Theme.TEXT_PRIMARY,
                 font=("Segoe UI", 10),
                 padx=20, pady=5, border=0, cursor="hand2").pack(pady=10)
    
    def insert_song_at_position(self):
        """Insert bài hát tại vị trí cụ thể - THỂ HIỆN INSERT OPERATION"""
        if self.playlist.is_empty:
            messagebox.showinfo("Insert", "Playlist is empty. Please add songs first.")
            return
        
        # Chọn file
        files = filedialog.askopenfilenames(
            title="Select Music File to Insert",
            filetypes=[
                ("Audio/Video Files", "*.mp3 *.wav *.ogg *.flac *.mp4 *.m4a *.aac *.wma"),
                ("All Files", "*.*")
            ]
        )
        
        if not files:
            return
        
        # Nhập vị trí
        position = simpledialog.askinteger(
            "Insert at Position",
            f"Enter position (0 to {len(self.playlist)}):\n0 = đầu, {len(self.playlist)} = cuối",
            minvalue=0,
            maxvalue=len(self.playlist)
        )
        
        if position is None:
            return
        
        # Insert
        for file_path in files:
            song = Song.from_path(file_path)
            if self.playlist.insert_at(position, song):
                self._update_status(f"✅ Inserted '{song.title}' at position {position}")
                position += 1  # Tăng position cho các file tiếp theo
            else:
                self._update_status(f"❌ Failed to insert '{song.title}'")
        
        self._refresh_playlist_view()
        self._update_ll_info()
    
    def delete_song_at_position(self):
        """Delete bài hát tại vị trí cụ thể - THỂ HIỆN DELETE OPERATION"""
        if self.playlist.is_empty:
            messagebox.showinfo("Delete", "Playlist is empty.")
            return
        
        position = simpledialog.askinteger(
            "Delete at Position",
            f"Enter position to delete (0 to {len(self.playlist) - 1}):",
            minvalue=0,
            maxvalue=len(self.playlist) - 1
        )
        
        if position is None:
            return
        
        song = self.playlist.remove_at(position)
        if song:
            self._refresh_playlist_view()
            self._update_status(f"🗑️ Deleted '{song.title}' at position {position}")
            self._update_ll_info()
        else:
            self._update_status(f"❌ Failed to delete at position {position}")
    
    def run(self):
        """Chạy ứng dụng"""
        self.root.mainloop()


# ==================== MAIN ====================
if __name__ == "__main__":
    app = MelodifyApp()
    app.run()

