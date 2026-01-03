# 🎵 Melodify - Music Player với Linked List

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
![DSA](https://img.shields.io/badge/Data%20Structure-Linked%20List-green)

Ứng dụng nghe nhạc Windows được xây dựng với **Doubly Linked List** - một dự án DSA (Data Structures and Algorithms).

## ✨ Tính năng

### 🎵 Cơ bản
- 🎶 Phát nhạc MP3, WAV, OGG, FLAC, **MP4, M4A, AAC, WMA**
- 🎬 **Xem video MP4** - Tự động mở cửa sổ video khi phát file MP4 có video
- 🎬 Tự động convert MP4/M4A sang WAV để phát audio (cần FFmpeg)
- 📋 Quản lý playlist với **Doubly Linked List**
- ▶️ Play, Pause, Stop, Next, Previous
- 🔀 Shuffle (xáo trộn playlist)
- 🔁 Repeat modes (Off / All / One)
- 🔊 Điều chỉnh âm lượng
- 🎨 Giao diện Cyberpunk/Neon đẹp mắt
- ⌨️ Hỗ trợ phím tắt

### 🆕 Tính năng mới
- 💾 **Auto-save/load playlist** - Tự động lưu playlist khi đóng app
- ❤️ **Favorites** - Linked List thứ 2 cho danh sách yêu thích
- 🔍 **Search** - Tìm kiếm bài hát trong playlist (Ctrl+F)
- 📊 **Statistics** - Thống kê số bài đã phát, thời gian nghe
- 💾 **Export/Import** - Xuất/nhập playlist dạng JSON
- 🖱️ **Right-click menu** - Menu context khi click phải vào bài hát

## 🔗 Cấu trúc dữ liệu Linked List

### Tại sao chọn Doubly Linked List?

| Thao tác | Độ phức tạp | Lý do |
|----------|-------------|-------|
| Next song | O(1) | Truy cập trực tiếp qua `node.next` |
| Previous song | O(1) | Truy cập trực tiếp qua `node.prev` |
| Add to end | O(1) | Có pointer `tail` |
| Remove current | O(1) | Không cần duyệt để tìm previous |
| Go to index | O(n) | Cần duyệt, nhưng tối ưu từ 2 phía |
| Circular mode | O(1) | Chỉ cần flag, không thay đổi cấu trúc |

### Các class chính

```
┌─────────────────────────────────────────────────────────────┐
│                    PlaylistLinkedList                        │
├─────────────────────────────────────────────────────────────┤
│ _head: Node          - Node đầu tiên                        │
│ _tail: Node          - Node cuối cùng                       │
│ _current: Node       - Bài hát đang phát                    │
│ _size: int           - Số lượng bài hát                     │
│ _circular: bool      - Chế độ lặp                           │
├─────────────────────────────────────────────────────────────┤
│ append(song)         - Thêm vào cuối O(1)                   │
│ prepend(song)        - Thêm vào đầu O(1)                    │
│ insert_at(i, song)   - Chèn tại vị trí O(n)                 │
│ remove_current()     - Xóa bài hiện tại O(1)                │
│ next() / previous()  - Di chuyển O(1)                       │
│ shuffle()            - Xáo trộn Fisher-Yates O(n)           │
└─────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Node 1      │◄──►│     Node 2      │◄──►│     Node 3      │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ data: Song      │    │ data: Song      │    │ data: Song      │
│ prev: None      │    │ prev: Node 1    │    │ prev: Node 2    │
│ next: Node 2    │    │ next: Node 3    │    │ next: None      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
       ▲                                              ▲
       │                                              │
     HEAD                                           TAIL
```

## 🚀 Cài đặt

### Yêu cầu
- Python 3.8+
- Windows/Linux/MacOS

### Bước 1: Clone project
```bash
cd D:\DSA_Project
```

### Bước 2: Cài đặt dependencies
```bash
pip install -r requirements.txt
```

**Lưu ý:** 
- `opencv-python` - Để xem video MP4
- `Pillow` - Hỗ trợ hiển thị video frames
- `pydub` + `FFmpeg` - Để phát audio từ MP4

### Bước 2.1: Cài đặt FFmpeg (cho MP4 support)

**Windows:**
1. Tải FFmpeg từ https://ffmpeg.org/download.html
2. Giải nén và thêm thư mục `bin` vào PATH
3. Hoặc dùng: `winget install ffmpeg` / `choco install ffmpeg`

**Linux:**
```bash
sudo apt install ffmpeg
```

**MacOS:**
```bash
brew install ffmpeg
```

### Bước 3: Chạy ứng dụng
```bash
python music_player.py
```

## 🎮 Phím tắt

| Phím | Chức năng |
|------|-----------|
| `Space` | Play / Pause |
| `←` | Bài trước |
| `→` | Bài tiếp |
| `Delete` | Xóa bài đang chọn |
| `Ctrl+F` | Tìm kiếm bài hát |
| `Double-click` | Phát bài được chọn |
| `Right-click` | Menu context (Add to Favorites, Delete...) |

## 📋 Menu Bar

- **File**
  - Save Playlist - Lưu playlist hiện tại
  - Load Playlist - Load playlist đã lưu
  - Export Playlist... - Xuất ra file JSON
  - Import Playlist... - Nhập từ file JSON
  
- **Playlist**
  - Search... - Tìm kiếm bài hát (Ctrl+F)
  - Favorites - Xem danh sách yêu thích
  - Statistics - Xem thống kê

## 📁 Cấu trúc project

```
DSA_Project/
├── music_player.py      # Ứng dụng chính với GUI
├── linked_list.py       # Implementation Doubly Linked List
├── requirements.txt     # Dependencies
└── README.md           # Documentation
```

## 🎨 Giao diện

Thiết kế theo phong cách **Cyberpunk/Neon** với:
- Background tối `#0a0a0f`
- Accent màu Cyan `#00d4ff` và Magenta `#ff006e`
- Hiệu ứng vinyl spinning khi phát nhạc
- Custom widgets (GlowButton, ModernSlider)

## 📝 Giải thích thuật toán

### 1. Shuffle (Fisher-Yates)
```python
def shuffle(self):
    songs = list(self)  # O(n) - chuyển sang array
    random.shuffle(songs)  # O(n) - Fisher-Yates
    self.clear()  # O(1)
    for song in songs:
        self.append(song)  # O(1) mỗi lần
    # Tổng: O(n)
```

### 2. Tìm node tại index (tối ưu 2 phía)
```python
def _get_node_at(self, index):
    if index <= self._size // 2:
        # Đi từ đầu nếu index ở nửa đầu
        node = self._head
        for _ in range(index):
            node = node.next
    else:
        # Đi từ cuối nếu index ở nửa sau
        node = self._tail
        for _ in range(self._size - 1 - index):
            node = node.prev
    return node
```

### 3. Circular mode (Repeat All)
```python
def next(self):
    if self._current.next:
        self._current = self._current.next
    elif self._circular:
        # Quay về đầu playlist
        self._current = self._head
```

## 🎬 Hỗ trợ MP4/Video

### Video Formats
App tự động **phát video** cho các định dạng:
- `.mp4` - Video MPEG-4 (xem video + nghe audio)
- `.webm` - WebM Video
- `.avi`, `.mkv`, `.mov` - Các định dạng video khác

Khi phát file MP4 có video, app sẽ:
1. Tự động mở cửa sổ video riêng
2. Đồng bộ audio và video (play/pause/seek)
3. Hiển thị video frames trong thời gian thực

### Audio-only Formats
App convert sang WAV để phát:
- `.m4a` - Audio MPEG-4  
- `.aac` - Advanced Audio Coding
- `.wma` - Windows Media Audio

**Yêu cầu:** 
- `opencv-python` + `Pillow` - Để xem video
- `pydub` + FFmpeg - Để phát audio từ MP4

## 💾 Lưu trữ dữ liệu

App tự động lưu dữ liệu vào thư mục `.melodify_data/`:
- `playlist.json` - Playlist hiện tại
- `favorites.json` - Danh sách yêu thích (Linked List thứ 2)
- `stats.json` - Thống kê nghe nhạc

Dữ liệu được **tự động lưu** khi đóng app và **tự động load** khi mở lại.

## 🔧 Mở rộng có thể thêm

- Thêm `mutagen` để đọc metadata chính xác (duration, album art)
- Lyrics display
- Equalizer
- Playlist folders/categories

## 👨‍💻 Tác giả

DSA Project - Data Structures and Algorithms

---

**Made with ❤️ and Linked Lists**

