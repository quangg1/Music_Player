# ============================================
# MUSIC ENGINE - Audio/Video Playback
# ============================================

import os
import threading
from typing import Optional

# Pygame
try:
    import pygame
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("⚠️ pygame not installed. Run: pip install pygame")

# Video support - Set environment trước khi import để tránh FFmpeg threading issues
import sys

# Suppress FFmpeg assertion errors - chúng không ảnh hưởng đến functionality
# Redirect stderr để bỏ qua assertion warnings
class SuppressFFmpegAssertion:
    def __init__(self):
        self.original_stderr = sys.stderr
    
    def write(self, text):
        # Bỏ qua assertion errors từ FFmpeg
        if 'Assertion' in text and 'async_lock' in text:
            return
        self.original_stderr.write(text)
    
    def flush(self):
        self.original_stderr.flush()

# Set environment variables
os.environ['OPENCV_FFMPEG_THREADS'] = '1'
os.environ['OPENCV_FFMPEG_READ_ATTEMPTS'] = '1'
os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'threads;1|thread_type;none'

# Suppress stderr cho FFmpeg assertions
_ffmpeg_suppressor = SuppressFFmpegAssertion()
sys.stderr = _ffmpeg_suppressor

try:
    import cv2
    import numpy as np
    from PIL import Image, ImageTk
    import tkinter as tk
    VIDEO_AVAILABLE = True
except ImportError:
    VIDEO_AVAILABLE = False
    print("⚠️ Video support not available. Install: pip install opencv-python Pillow")
finally:
    # Restore stderr
    sys.stderr = _ffmpeg_suppressor.original_stderr

# FFmpeg và pydub
FFMPEG_AVAILABLE = False
PYDUB_AVAILABLE = False

def find_ffmpeg():
    """Tìm và thêm FFmpeg vào PATH nếu cài qua winget"""
    import subprocess
    import glob
    
    # Kiểm tra FFmpeg đã có trong PATH chưa
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        if result.returncode == 0:
            return True
    except FileNotFoundError:
        pass
    
    # Tìm FFmpeg trong các đường dẫn phổ biến (Windows)
    if os.name == 'nt':
        search_paths = [
            os.path.expanduser(r"~\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg*\ffmpeg-*\bin"),
            os.path.expanduser(r"~\AppData\Local\Microsoft\WinGet\Links"),
            r"C:\ffmpeg\bin",
            r"C:\Program Files\ffmpeg\bin",
            r"C:\tools\ffmpeg\bin",
        ]
        
        for pattern in search_paths:
            matches = glob.glob(pattern)
            for path in matches:
                ffmpeg_exe = os.path.join(path, "ffmpeg.exe")
                if os.path.exists(ffmpeg_exe):
                    # Thêm vào PATH
                    os.environ["PATH"] = path + os.pathsep + os.environ.get("PATH", "")
                    print(f"📍 Found FFmpeg at: {path}")
                    return True
    
    return False

# Tìm FFmpeg trước
if find_ffmpeg():
    FFMPEG_AVAILABLE = True
    print("✅ FFmpeg detected - MP4 support enabled")
else:
    print("⚠️ FFmpeg not found. Install: winget install ffmpeg")

# Kiểm tra pydub
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
    print("✅ pydub loaded successfully")
except ImportError as e:
    print(f"⚠️ pydub import error: {e}")
except Exception as e:
    print(f"⚠️ pydub error: {e}")


class MusicEngine:
    """Engine phát nhạc sử dụng pygame với hỗ trợ MP4"""
    
    # Định dạng cần convert (video formats)
    VIDEO_FORMATS = {'.mp4', '.webm', '.avi', '.mkv', '.mov'}
    AUDIO_ONLY_FORMATS = {'.m4a', '.aac', '.wma'}
    CONVERT_FORMATS = VIDEO_FORMATS | AUDIO_ONLY_FORMATS
    
    def __init__(self):
        self.is_playing = False
        self.is_paused = False
        self.current_pos = 0.0
        self.duration = 0.0
        self._volume = 0.7
        self._temp_file = None  # File tạm cho convert
        self._temp_dir = os.path.join(os.path.dirname(__file__), '.temp_audio')
        self._youtube_dir = os.path.join(os.path.dirname(__file__), '.youtube_downloads')
        self._video_path = None  # Path to video file
        self._has_video = False  # Whether current file has video
        self._is_youtube = False  # Whether current file is from YouTube
        self._convert_lock = threading.Lock()  # Lock cho FFmpeg convert
        
        # Tracking position sau khi seek
        self._play_start_time = None
        self._play_start_pos = 0.0
        
        # Tạo thư mục temp
        if not os.path.exists(self._temp_dir):
            os.makedirs(self._temp_dir)
        if not os.path.exists(self._youtube_dir):
            os.makedirs(self._youtube_dir)
        
        if PYGAME_AVAILABLE:
            pygame.mixer.music.set_volume(self._volume)
    
    def has_video_stream(self, path: str) -> bool:
        """Kiểm tra file có video stream không"""
        if not VIDEO_AVAILABLE:
            return False
        
        try:
            cap = cv2.VideoCapture(path)
            has_video = cap.isOpened() and cap.get(cv2.CAP_PROP_FRAME_COUNT) > 0
            cap.release()
            return has_video
        except:
            return False
    
    def load(self, path: str) -> bool:
        """Load file nhạc - tự động convert MP4/M4A nếu cần"""
        if not PYGAME_AVAILABLE:
            return False
        
        try:
            ext = os.path.splitext(path)[1].lower()
            
            # Kiểm tra có video không
            self._has_video = ext in self.VIDEO_FORMATS and self.has_video_stream(path)
            
            if self._has_video:
                # Giữ video path để phát video
                self._video_path = path
                # Extract audio để phát
                converted_path = self._convert_to_wav(path)
                if converted_path:
                    path = converted_path
                else:
                    return False
            elif ext in self.AUDIO_ONLY_FORMATS:
                # Chỉ audio, convert như bình thường
                converted_path = self._convert_to_wav(path)
                if converted_path:
                    path = converted_path
            else:
                # Không phải video format, dùng trực tiếp
                self._video_path = None
                self._has_video = False
            
            pygame.mixer.music.load(path)
            self.duration = self._get_duration(path)
            self.current_pos = 0
            # Lưu lại path để có thể reload khi seek
            self._current_loaded_path = path
            return True
        except Exception as e:
            print(f"Error loading: {e}")
            return False
    
    def _convert_to_wav(self, path: str) -> Optional[str]:
        """Convert MP4/M4A sang WAV để pygame phát được - Thread-safe với FFmpeg"""
        if not PYDUB_AVAILABLE:
            print("⚠️ pydub not installed. Run: pip install pydub")
            return None
        
        if not FFMPEG_AVAILABLE:
            print("⚠️ FFmpeg not found. Please restart terminal or add FFmpeg to PATH.")
            return None
        
        try:
            from pydub import AudioSegment
            import subprocess
            
            with self._convert_lock:  # Thread-safe convert - chỉ một process tại một thời điểm
                # Tạo tên file temp
                filename = os.path.basename(path)
                temp_path = os.path.join(self._temp_dir, f"{os.path.splitext(filename)[0]}.wav")
                
                # Kiểm tra file đã tồn tại chưa
                if os.path.exists(temp_path):
                    print(f"✅ Using cached: {filename}")
                    return temp_path
                
                print(f"🔄 Converting {filename}...")
                
                # Convert - đảm bảo thread-safe
                ext = os.path.splitext(path)[1].lower()
                if ext == '.mp4' or ext == '.m4a':
                    audio = AudioSegment.from_file(path, format="mp4")
                elif ext == '.webm':
                    audio = AudioSegment.from_file(path, format="webm")
                else:
                    audio = AudioSegment.from_file(path)
                
                # Export với thread-safe settings để tránh async_lock assertion
                # Sử dụng subprocess trực tiếp thay vì qua pydub để kiểm soát tốt hơn
                try:
                    import subprocess
                    import shutil
                    
                    # Tìm ffmpeg path
                    ffmpeg_path = shutil.which("ffmpeg")
                    if not ffmpeg_path:
                        # Fallback về pydub nếu không tìm thấy ffmpeg trực tiếp
                        raise FileNotFoundError("FFmpeg not in PATH")
                    
                    # Sử dụng subprocess trực tiếp với các tham số an toàn
                    cmd = [
                        ffmpeg_path,
                        "-i", path,
                        "-threads", "1",           # Single thread
                        "-thread_type", "none",    # Disable threading để tránh assertion
                        "-acodec", "pcm_s16le",   # PCM 16-bit
                        "-ar", "44100",            # Sample rate
                        "-ac", "2",                # Stereo
                        "-y",                       # Overwrite output
                        temp_path
                    ]
                    
                    # Chạy với timeout và không hiển thị output
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        timeout=300,  # 5 phút timeout
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                    )
                    
                    if result.returncode == 0 and os.path.exists(temp_path):
                        self._temp_file = temp_path
                        print(f"✅ Converted successfully!")
                        return temp_path
                    else:
                        raise Exception(f"FFmpeg error: {result.stderr.decode('utf-8', errors='ignore')}")
                        
                except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
                    # Fallback về pydub nếu subprocess thất bại
                    print(f"⚠️ Subprocess failed, using pydub: {e}")
                    export_params = [
                        "-threads", "1",           # Single thread
                        "-thread_type", "none",    # Disable threading
                    ]
                    audio.export(temp_path, format="wav", parameters=export_params)
                self._temp_file = temp_path
                
                print(f"✅ Converted successfully!")
                return temp_path
        except Exception as e:
            print(f"❌ Convert error: {e}")
            # Thử cleanup nếu có lỗi
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except:
                pass
            return None
    
    def cleanup_temp(self):
        """Dọn dẹp file tạm"""
        if self._temp_file and os.path.exists(self._temp_file):
            try:
                os.remove(self._temp_file)
            except:
                pass
    
    def play(self, start_pos: float = 0.0) -> None:
        """Play nhạc, có thể bắt đầu từ vị trí start_pos (giây)"""
        if not PYGAME_AVAILABLE:
            return
        
        import time
        
        if self.is_paused:
            # Resume từ pause - lấy position hiện tại và tiếp tục từ đó
            pygame.mixer.music.unpause()
            # Nếu có _play_start_pos đã được lưu khi pause, dùng nó
            if hasattr(self, '_play_start_pos'):
                current_pos = self._play_start_pos
            else:
                current_pos = self.current_pos
            self._play_start_time = time.time()
            self._play_start_pos = current_pos
        else:
            # Play mới
            if start_pos > 0:
                # Với MP3/MP4, pygame không hỗ trợ start position tốt
                # Cần track position thủ công
                pygame.mixer.music.play()
                self._play_start_time = time.time()
                self._play_start_pos = start_pos
                # Thử seek (có thể không hoạt động)
                try:
                    pygame.mixer.music.set_pos(start_pos)
                except:
                    pass
            else:
                # Play từ đầu - set tracking ngay
                pygame.mixer.music.play()
                import time
                self._play_start_time = time.time()
                self._play_start_pos = 0.0
                # Đảm bảo current_pos được set
                self.current_pos = 0.0
        
        self.is_playing = True
        self.is_paused = False
        
        # Set current_pos dựa trên trạng thái
        if self.is_paused:  # Resume từ pause
            self.current_pos = self._play_start_pos
        else:  # Play mới
            self.current_pos = start_pos
        
        # Đảm bảo tracking variables được set (fallback)
        if not hasattr(self, '_play_start_time') or self._play_start_time is None:
            import time
            self._play_start_time = time.time()
            self._play_start_pos = start_pos if start_pos > 0 else 0.0
    
    def pause(self) -> None:
        if not PYGAME_AVAILABLE:
            return
        # Chỉ pause nếu đang playing
        if self.is_playing and not self.is_paused:
            pygame.mixer.music.pause()
            self.is_paused = True
            # Lưu lại position hiện tại khi pause
            if hasattr(self, '_play_start_time') and self._play_start_time is not None:
                import time
                elapsed = time.time() - self._play_start_time
                self._play_start_pos = self._play_start_pos + elapsed
                self._play_start_time = None  # Reset để không tính elapsed khi pause
    
    def stop(self) -> None:
        if not PYGAME_AVAILABLE:
            return
        pygame.mixer.music.stop()
        self.is_playing = False
        self.is_paused = False
        self.current_pos = 0
        self._video_path = None
        self._has_video = False
        # Reset tracking
        self._play_start_time = None
        self._play_start_pos = 0.0
        self.cleanup_temp()
    
    def seek(self, position: float) -> None:
        """Seek đến vị trí (giây) - chỉ update current_pos, không thực sự seek"""
        # Giới hạn position trong khoảng hợp lệ
        position = max(0, min(position, self.duration))
        self.current_pos = position
        
        # pygame.mixer.music.set_pos() không hoạt động tốt với MP3/MP4
        # Cần reload file và play từ vị trí mới (được xử lý ở music_player.py)
        if not PYGAME_AVAILABLE:
            return
        
        # Thử seek nếu đang playing (có thể không hoạt động với MP3/MP4)
        if self.is_playing:
            try:
                pygame.mixer.music.set_pos(position)
            except:
                # Không hỗ trợ seek, cần reload (sẽ được xử lý ở music_player.py)
                pass
    
    def play_from_pos(self, position: float) -> None:
        """Play từ vị trí cụ thể (giây) - reload và play"""
        if not PYGAME_AVAILABLE:
            return
        
        # Giới hạn position
        position = max(0, min(position, self.duration))
        self.current_pos = position
        
        # Stop hiện tại
        if self.is_playing:
            pygame.mixer.music.stop()
        
        # Reload và play từ vị trí mới
        # Lưu lại path hiện tại
        current_path = None
        if hasattr(self, '_current_loaded_path'):
            current_path = self._current_loaded_path
        
        if current_path and os.path.exists(current_path):
            # Reload file
            try:
                pygame.mixer.music.load(current_path)
                # Play từ vị trí mới (có thể không hoạt động với MP3/MP4)
                try:
                    pygame.mixer.music.play(start=position)
                except:
                    # Fallback: play từ đầu
                    pygame.mixer.music.play()
                    try:
                        pygame.mixer.music.set_pos(position)
                    except:
                        pass
                self.is_playing = True
                self.is_paused = False
            except Exception as e:
                print(f"Error seeking: {e}")
    
    @property
    def volume(self) -> float:
        return self._volume
    
    @volume.setter
    def volume(self, value: float) -> None:
        self._volume = max(0.0, min(1.0, value))
        if PYGAME_AVAILABLE:
            pygame.mixer.music.set_volume(self._volume)
    
    def get_pos(self) -> float:
        """Lấy vị trí hiện tại (giây) - track thủ công nếu đã seek"""
        if not PYGAME_AVAILABLE:
            return self.current_pos
        
        # Nếu đang playing và không pause, luôn dùng manual tracking nếu có
        if self.is_playing and not self.is_paused:
            # Ưu tiên: dùng manual tracking nếu có _play_start_time
            if (hasattr(self, '_play_start_time') and hasattr(self, '_play_start_pos') and 
                self._play_start_time is not None):
                import time
                elapsed = time.time() - self._play_start_time
                calculated_pos = self._play_start_pos + elapsed
                
                # Giới hạn trong duration
                if self.duration > 0:
                    calculated_pos = min(calculated_pos, self.duration)
                
                # Đảm bảo không âm
                calculated_pos = max(0, calculated_pos)
                
                # Cập nhật current_pos
                self.current_pos = calculated_pos
                return calculated_pos
            else:
                # Nếu không có tracking, set tracking ngay từ đầu
                import time
                if not hasattr(self, '_play_start_time') or self._play_start_time is None:
                    self._play_start_time = time.time()
                    self._play_start_pos = 0.0
                    self.current_pos = 0.0
                    return 0.0
            
            # Fallback: dùng pygame position và set tracking nếu chưa có
            pygame_pos = pygame.mixer.music.get_pos() / 1000.0
            # pygame_pos có thể là 0 ngay sau khi play, nhưng vẫn cần set tracking
            if pygame_pos >= 0:
                # Nếu chưa có tracking, set tracking từ pygame position
                if not hasattr(self, '_play_start_time') or self._play_start_time is None:
                    import time
                    self._play_start_time = time.time()
                    self._play_start_pos = max(0, pygame_pos)
                    return max(0, pygame_pos)
                else:
                    # Đã có tracking, dùng manual tracking
                    import time
                    elapsed = time.time() - self._play_start_time
                    calculated_pos = self._play_start_pos + elapsed
                    if self.duration > 0:
                        calculated_pos = min(calculated_pos, self.duration)
                    calculated_pos = max(0, calculated_pos)
                    self.current_pos = calculated_pos
                    return calculated_pos
        
        # Nếu không playing hoặc đang pause, trả về current_pos
        return max(0, self.current_pos)
    
    def is_active(self) -> bool:
        if not PYGAME_AVAILABLE:
            return False
        return pygame.mixer.music.get_busy()
    
    def _get_duration(self, path: str) -> float:
        """Lấy duration chính xác từ file - sử dụng FFmpeg/pydub"""
        # Thử dùng pydub để lấy duration chính xác
        if PYDUB_AVAILABLE:
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_file(path)
                duration_seconds = len(audio) / 1000.0  # pydub trả về milliseconds
                if duration_seconds > 0:
                    return duration_seconds
            except Exception as e:
                print(f"Warning: Could not get duration with pydub: {e}")
        
        # Thử dùng FFmpeg để lấy duration
        if FFMPEG_AVAILABLE:
            try:
                import subprocess
                import shutil
                import json
                
                ffprobe_path = shutil.which("ffprobe")
                if not ffprobe_path:
                    # Thử tìm ffprobe trong cùng thư mục với ffmpeg
                    ffmpeg_path = shutil.which("ffmpeg")
                    if ffmpeg_path:
                        ffprobe_path = os.path.join(os.path.dirname(ffmpeg_path), "ffprobe.exe")
                        if not os.path.exists(ffprobe_path):
                            ffprobe_path = None
                
                if ffprobe_path:
                    cmd = [
                        ffprobe_path,
                        "-v", "quiet",
                        "-print_format", "json",
                        "-show_format",
                        path
                    ]
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=10,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                    )
                    
                    if result.returncode == 0:
                        data = json.loads(result.stdout)
                        if 'format' in data and 'duration' in data['format']:
                            duration_seconds = float(data['format']['duration'])
                            if duration_seconds > 0:
                                return duration_seconds
            except Exception as e:
                print(f"Warning: Could not get duration with ffprobe: {e}")
        
        # Thử dùng OpenCV cho video files
        if VIDEO_AVAILABLE:
            try:
                cap = cv2.VideoCapture(path)
                if cap.isOpened():
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                    cap.release()
                    if fps > 0 and frame_count > 0:
                        duration_seconds = frame_count / fps
                        if duration_seconds > 0:
                            return duration_seconds
            except Exception as e:
                print(f"Warning: Could not get duration with OpenCV: {e}")
        
        # Fallback: estimate from file size (không chính xác)
        try:
            size = os.path.getsize(path)
            # Giả sử bitrate 192kbps cho audio, hoặc ước tính cho video
            ext = os.path.splitext(path)[1].lower()
            if ext in self.VIDEO_FORMATS:
                # Video thường có bitrate cao hơn
                estimated_bitrate = 2000 * 1000 / 8  # 2Mbps
            else:
                estimated_bitrate = 192 * 1000 / 8  # 192kbps
            return size / estimated_bitrate
        except:
            return 180.0  # Default 3 phút


class VideoPlayer:
    """Video player hiển thị trong Canvas chính"""
    
    def __init__(self, canvas):
        self.canvas = canvas  # Canvas để hiển thị video (vinyl)
        self.video_cap = None
        self.is_playing = False
        self.is_paused = False
        self.fps = 30
        self.video_path = None
        self.update_id = None
        self.video_image_id = None
        self.start_time = None  # Thời gian bắt đầu phát
        self.seek_offset = 0.0  # Offset khi seek
        self.last_sync_time = 0.0  # Thời gian sync cuối cùng
        self._cap_lock = threading.Lock()  # Lock để tránh xung đột khi truy cập video_cap
    
    def open(self, video_path: str):
        """Mở video với error suppression cho FFmpeg assertions và threading lock"""
        if not VIDEO_AVAILABLE or not self.canvas:
            return
        
        # Đóng video cũ nếu có
        self.stop()
        
        self.video_path = video_path
        
        # Suppress stderr hoàn toàn để bỏ qua FFmpeg assertion errors
        original_stderr = sys.stderr
        sys.stderr = _ffmpeg_suppressor
        
        try:
            with self._cap_lock:
                # Load video với backend và tham số an toàn
                try:
                    # Thử dùng backend DirectShow trên Windows để tránh FFmpeg threading
                    if os.name == 'nt':
                        self.video_cap = cv2.VideoCapture(video_path, cv2.CAP_DSHOW)
                    else:
                        self.video_cap = cv2.VideoCapture(video_path)
                    
                    # Set properties để tránh threading issues
                    if self.video_cap.isOpened():
                        # Disable threading trong OpenCV
                        self.video_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        self.fps = self.video_cap.get(cv2.CAP_PROP_FPS) or 30
                    else:
                        # Fallback: thử lại với backend mặc định
                        if self.video_cap:
                            self.video_cap.release()
                        self.video_cap = cv2.VideoCapture(video_path)
                        if self.video_cap.isOpened():
                            self.video_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                            self.fps = self.video_cap.get(cv2.CAP_PROP_FPS) or 30
                        else:
                            print("Error opening video")
                            self.video_cap = None
                            return
                except Exception as e:
                    print(f"Error opening video: {e}")
                    self.video_cap = None
                    return
            
            # Play sau khi mở thành công
            if self.video_cap:
                self.play()
        finally:
            # Restore stderr
            sys.stderr = original_stderr
    
    def play(self):
        """Phát video"""
        if self.video_cap is None:
            return
        
        self.is_playing = True
        self.is_paused = False
        # Reset start time khi bắt đầu play
        import time
        self.start_time = time.time() - self.seek_offset
        self.last_sync_time = self.seek_offset
        self._update_frame()
    
    def pause(self):
        """Tạm dừng video"""
        self.is_paused = True
        if self.update_id:
            self.canvas.after_cancel(self.update_id)
            self.update_id = None
    
    def resume(self):
        """Tiếp tục video"""
        if self.is_paused:
            self.is_paused = False
            self._update_frame()
    
    def stop(self):
        """Dừng video"""
        self.is_playing = False
        if self.update_id:
            try:
                self.canvas.after_cancel(self.update_id)
            except:
                pass
            self.update_id = None
        
        # Suppress stderr khi release
        original_stderr = sys.stderr
        sys.stderr = _ffmpeg_suppressor
        
        try:
            with self._cap_lock:
                if self.video_cap:
                    self.video_cap.release()
                    self.video_cap = None
        finally:
            sys.stderr = original_stderr
        
        # Xóa video image khỏi canvas
        if self.video_image_id:
            self.canvas.delete(self.video_image_id)
            self.video_image_id = None
    
    def seek(self, position: float):
        """Nhảy đến vị trí (giây)"""
        if not self.video_cap or not self.canvas:
            return
        
        # Suppress stderr khi seek để bỏ qua assertion errors
        original_stderr = sys.stderr
        sys.stderr = _ffmpeg_suppressor
        
        try:
            # Hủy scheduled update hiện tại
            if self.update_id:
                try:
                    self.canvas.after_cancel(self.update_id)
                except:
                    pass
                self.update_id = None
            
            # Cập nhật seek offset
            self.seek_offset = position
            if self.is_playing:
                import time
                self.start_time = time.time() - position
                self.last_sync_time = position
            
            # Seek và đọc frame với lock
            ret = False
            frame = None
            with self._cap_lock:
                if self.video_cap and self.video_cap.isOpened():
                    # Seek đến frame mới
                    frame_number = int(position * self.fps)
                    self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, frame_number))
                    ret, frame = self.video_cap.read()
            
            if ret and frame is not None:
                # Convert BGR to RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Lấy kích thước canvas thực tế
                canvas_width = self.canvas.winfo_width() if self.canvas.winfo_width() > 1 else 380
                canvas_height = self.canvas.winfo_height() if self.canvas.winfo_height() > 1 else 380
                frame = cv2.resize(frame, (canvas_width, canvas_height))
                
                # Convert to PhotoImage
                image = Image.fromarray(frame)
                photo = ImageTk.PhotoImage(image=image)
                
                # Xóa image cũ nếu có
                if self.video_image_id:
                    self.canvas.delete(self.video_image_id)
                
                # Hiển thị image ở giữa canvas
                self.video_image_id = self.canvas.create_image(
                    canvas_width // 2, canvas_height // 2,
                    image=photo, anchor=tk.CENTER
                )
                self.canvas.photo = photo  # Keep a reference
                
                # Tiếp tục update nếu đang playing
                if self.is_playing and not self.is_paused:
                    delay = int(1000 / self.fps)
                    self.update_id = self.canvas.after(delay, self._update_frame)
        except Exception as e:
            print(f"Video seek error: {e}")
        finally:
            sys.stderr = original_stderr
    
    def sync_with_audio(self, audio_position: float):
        """Sync video với audio position"""
        if not self.video_cap or not self.is_playing:
            return
        
        # Suppress stderr khi sync để bỏ qua assertion errors
        original_stderr = sys.stderr
        sys.stderr = _ffmpeg_suppressor
        
        try:
            # Tính toán vị trí video nên ở đâu
            video_position = audio_position
            
            # Nếu lệch quá nhiều (>0.5s), seek lại
            if abs(video_position - self.last_sync_time) > 0.5:
                with self._cap_lock:
                    if self.video_cap and self.video_cap.isOpened():
                        frame_number = int(video_position * self.fps)
                        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, frame_number))
                self.seek_offset = video_position
                import time
                self.start_time = time.time() - video_position
                self.last_sync_time = video_position
        finally:
            sys.stderr = original_stderr
    
    def _update_frame(self):
        """Cập nhật frame video trên Canvas - sync với audio"""
        if not self.is_playing or self.is_paused or not self.canvas:
            return
        
        # Suppress stderr khi đọc frame để bỏ qua assertion errors
        original_stderr = sys.stderr
        sys.stderr = _ffmpeg_suppressor
        
        ret = False
        frame = None
        try:
            # Đọc frame với lock để tránh xung đột
            with self._cap_lock:
                if self.video_cap is None or not self.video_cap.isOpened():
                    return
                
                # Tính toán vị trí video dựa trên thời gian
                import time
                if self.start_time:
                    current_time = time.time()
                    video_position = current_time - self.start_time
                    expected_frame = int(video_position * self.fps)
                    
                    # Lấy frame hiện tại của video
                    current_frame = int(self.video_cap.get(cv2.CAP_PROP_POS_FRAMES))
                    
                    # Nếu lệch quá nhiều (>2 frames), sync lại
                    if abs(expected_frame - current_frame) > 2:
                        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, expected_frame))
                
                ret, frame = self.video_cap.read()
        finally:
            sys.stderr = original_stderr
        
        if ret and frame is not None:
            # Convert BGR to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Lấy kích thước canvas thực tế
            canvas_width = self.canvas.winfo_width() if self.canvas.winfo_width() > 1 else 380
            canvas_height = self.canvas.winfo_height() if self.canvas.winfo_height() > 1 else 380
            frame = cv2.resize(frame, (canvas_width, canvas_height))
            
            # Convert to PhotoImage
            image = Image.fromarray(frame)
            photo = ImageTk.PhotoImage(image=image)
            
            # Xóa image cũ nếu có
            if self.video_image_id:
                self.canvas.delete(self.video_image_id)
            
            # Hiển thị image ở giữa canvas
            self.video_image_id = self.canvas.create_image(
                canvas_width // 2, canvas_height // 2,
                image=photo, anchor=tk.CENTER
            )
            self.canvas.photo = photo  # Keep a reference
            
            # Schedule next frame
            delay = int(1000 / self.fps)
            self.update_id = self.canvas.after(delay, self._update_frame)
        else:
            # Video ended
            self.stop()
    
    def close(self):
        """Đóng video"""
        self.stop()

