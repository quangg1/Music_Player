
from dataclasses import dataclass, asdict
from typing import Optional, Any, Iterator
import os
import json


@dataclass
class Song:
    """Lưu trữ thông tin bài hát"""
    title: str
    artist: str
    path: str
    duration: float = 0.0
    youtube_url: Optional[str] = None  # URL YouTube nếu có
    
    def __str__(self) -> str:
        return f"{self.title} - {self.artist}"
    
    @classmethod
    def from_path(cls, file_path: str) -> 'Song':
        """Tạo Song từ đường dẫn file"""
        filename = os.path.basename(file_path)
        name = os.path.splitext(filename)[0]
        
        # Thử parse "Artist - Title" format
        if " - " in name:
            parts = name.split(" - ", 1)
            return cls(title=parts[1], artist=parts[0], path=file_path)
        return cls(title=name, artist="Unknown Artist", path=file_path)


class Node:
    """Node trong Doubly Linked List"""
    __slots__ = ['data', 'prev', 'next']
    
    def __init__(self, data: Song):
        self.data: Song = data
        self.prev: Optional['Node'] = None
        self.next: Optional['Node'] = None


class PlaylistLinkedList:
    """
    Doubly Linked List tối ưu cho Playlist nhạc
    
    Đặc điểm:
    - Hỗ trợ circular mode (repeat all)
    - O(1) navigation next/previous
    - O(1) insert/delete tại current position
    - O(n) tìm kiếm theo index/title
    """
    
    def __init__(self):
        self._head: Optional[Node] = None
        self._tail: Optional[Node] = None
        self._current: Optional[Node] = None
        self._size: int = 0
        self._circular: bool = False  # Chế độ lặp playlist
    
    # ==================== PROPERTIES ====================
    @property
    def size(self) -> int:
        return self._size
    
    @property
    def is_empty(self) -> bool:
        return self._size == 0
    
    @property
    def current_song(self) -> Optional[Song]:
        return self._current.data if self._current else None
    
    @property
    def current_index(self) -> int:
        """Lấy index của bài hát hiện tại - O(n)"""
        if not self._current:
            return -1
        index = 0
        node = self._head
        while node and node != self._current:
            node = node.next
            index += 1
        return index
    
    @property
    def circular(self) -> bool:
        return self._circular
    
    @circular.setter
    def circular(self, value: bool):
        self._circular = value
    
    # ==================== MODIFICATION ====================    
    def append(self, song: Song) -> None:
        """Thêm bài hát vào cuối playlist - O(1)"""
        new_node = Node(song)
        
        if self.is_empty:
            self._head = self._tail = self._current = new_node
        else:
            new_node.prev = self._tail
            self._tail.next = new_node
            self._tail = new_node
        
        self._size += 1
    
    def prepend(self, song: Song) -> None:
        """Thêm bài hát vào đầu playlist - O(1)"""
        new_node = Node(song)
        
        if self.is_empty:
            self._head = self._tail = self._current = new_node
        else:
            new_node.next = self._head
            self._head.prev = new_node
            self._head = new_node
        
        self._size += 1
    
    def insert_at(self, index: int, song: Song) -> bool:
        """Chèn bài hát tại vị trí index - O(n)"""
        if index < 0 or index > self._size:
            return False
        
        if index == 0:
            self.prepend(song)
            return True
        
        if index == self._size:
            self.append(song)
            return True
        
        # Tìm node tại vị trí index
        node = self._get_node_at(index)
        if not node:
            return False
        
        new_node = Node(song)
        new_node.prev = node.prev
        new_node.next = node
        
        if node.prev:
            node.prev.next = new_node
        node.prev = new_node
        
        self._size += 1
        return True
    
    def remove_current(self) -> Optional[Song]:
        """Xóa bài hát hiện tại - O(1)"""
        if not self._current:
            return None
        
        removed = self._current.data
        
        if self._size == 1:
            self._head = self._tail = self._current = None
        else:
            prev_node = self._current.prev
            next_node = self._current.next
            
            if prev_node:
                prev_node.next = next_node
            else:
                self._head = next_node
            
            if next_node:
                next_node.prev = prev_node
            else:
                self._tail = prev_node
            
            # Di chuyển current đến bài tiếp theo hoặc trước đó
            self._current = next_node if next_node else prev_node
        
        self._size -= 1
        return removed
    
    def remove_at(self, index: int) -> Optional[Song]:
        """Xóa bài hát tại vị trí index - O(n)"""
        node = self._get_node_at(index)
        if not node:
            return None
        
        # Tạm thời set current để xóa
        old_current = self._current
        self._current = node
        removed = self.remove_current()
        
        # Khôi phục current nếu nó không phải node bị xóa
        if old_current and old_current != node:
            self._current = old_current
        
        return removed
    
    def clear(self) -> None:
        """Xóa toàn bộ playlist - O(1)"""
        self._head = self._tail = self._current = None
        self._size = 0
    
    # ==================== NAVIGATION ====================
    
    def next(self) -> Optional[Song]:
        """Chuyển đến bài tiếp theo - O(1)"""
        if not self._current:
            return None
        
        if self._current.next:
            self._current = self._current.next
        elif self._circular and self._head:
            # Circular mode: quay lại đầu
            self._current = self._head
        else:
            return None
        
        return self._current.data
    
    def previous(self) -> Optional[Song]:
        """Chuyển đến bài trước - O(1)"""
        if not self._current:
            return None
        
        if self._current.prev:
            self._current = self._current.prev
        elif self._circular and self._tail:
            # Circular mode: quay về cuối
            self._current = self._tail
        else:
            return None
        
        return self._current.data
    
    def go_to(self, index: int) -> Optional[Song]:
        """Nhảy đến bài hát tại index - O(n)"""
        node = self._get_node_at(index)
        if node:
            self._current = node
            return node.data
        return None
    
    def go_to_first(self) -> Optional[Song]:
        """Về bài đầu tiên - O(1)"""
        if self._head:
            self._current = self._head
            return self._current.data
        return None
    
    def go_to_last(self) -> Optional[Song]:
        """Đến bài cuối cùng - O(1)"""
        if self._tail:
            self._current = self._tail
            return self._current.data
        return None
    
    def has_next(self) -> bool:
        """Kiểm tra có bài tiếp theo không"""
        if not self._current:
            return False
        return self._current.next is not None or self._circular
    
    def has_previous(self) -> bool:
        """Kiểm tra có bài trước không"""
        if not self._current:
            return False
        return self._current.prev is not None or self._circular
    
    # ==================== SEARCH ====================
    
    def find_by_title(self, title: str) -> Optional[int]:
        """Tìm index bài hát theo title - O(n)"""
        index = 0
        node = self._head
        title_lower = title.lower()
        
        while node:
            if title_lower in node.data.title.lower():
                return index
            node = node.next
            index += 1
        
        return None
    
    def get_at(self, index: int) -> Optional[Song]:
        """Lấy bài hát tại index - O(n)"""
        node = self._get_node_at(index)
        return node.data if node else None
    
    # ==================== SHUFFLE ====================
    
    def shuffle(self) -> None:
        """Xáo trộn playlist (Fisher-Yates) - O(n)"""
        import random
        
        if self._size <= 1:
            return
        
        # Chuyển sang array để shuffle
        songs = list(self)
        random.shuffle(songs)
        
        # Tạo lại linked list
        current_song = self.current_song
        self.clear()
        
        for song in songs:
            self.append(song)
        
        # Khôi phục vị trí current
        if current_song:
            node = self._head
            while node:
                if node.data.path == current_song.path:
                    self._current = node
                    break
                node = node.next
    
    # ==================== HELPER METHODS ====================
    
    def _get_node_at(self, index: int) -> Optional[Node]:
        """Lấy node tại index - O(n) nhưng tối ưu từ 2 phía"""
        if index < 0 or index >= self._size:
            return None
        
        # Tối ưu: đi từ đầu hoặc cuối tùy vị trí
        if index <= self._size // 2:
            node = self._head
            for _ in range(index):
                node = node.next
        else:
            node = self._tail
            for _ in range(self._size - 1 - index):
                node = node.prev
        
        return node
    
    def to_list(self) -> list[Song]:
        """Chuyển playlist thành list - O(n)"""
        return list(self)
    
    # ==================== MAGIC METHODS ====================
    
    def __len__(self) -> int:
        return self._size
    
    def __iter__(self) -> Iterator[Song]:
        node = self._head
        while node:
            yield node.data
            node = node.next
    
    def __getitem__(self, index: int) -> Song:
        song = self.get_at(index)
        if song is None:
            raise IndexError(f"Index {index} out of range")
        return song
    
    def __contains__(self, song: Song) -> bool:
        for s in self:
            if s.path == song.path:
                return True
        return False
    
    def __repr__(self) -> str:
        songs = [str(s) for s in self]
        return f"Playlist({len(self)} songs): [{', '.join(songs[:5])}{'...' if len(songs) > 5 else ''}]"
    
    # ==================== EXPORT/IMPORT ====================
    
    def to_dict(self) -> dict:
        """Chuyển playlist thành dictionary để lưu JSON"""
        songs = [asdict(song) for song in self]
        return {
            "songs": songs,
            "current_index": self.current_index,
            "circular": self._circular
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PlaylistLinkedList':
        """Tạo playlist từ dictionary"""
        playlist = cls()
        songs_data = data.get("songs", [])
        
        for song_data in songs_data:
            song = Song(**song_data)
            playlist.append(song)
        
        # Khôi phục vị trí current
        current_idx = data.get("current_index", 0)
        if 0 <= current_idx < playlist.size:
            playlist.go_to(current_idx)
        
        playlist.circular = data.get("circular", False)
        return playlist
    
    def save_to_file(self, filepath: str) -> bool:
        """Lưu playlist vào file JSON"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving playlist: {e}")
            return False
    
    @classmethod
    def load_from_file(cls, filepath: str) -> Optional['PlaylistLinkedList']:
        """Load playlist từ file JSON"""
        try:
            if not os.path.exists(filepath):
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return cls.from_dict(data)
        except Exception as e:
            print(f"Error loading playlist: {e}")
            return None

