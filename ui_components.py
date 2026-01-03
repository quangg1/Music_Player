# ============================================
# UI COMPONENTS - Custom Widgets
# ============================================

import tkinter as tk
from theme import Theme


class GlowButton(tk.Canvas):
    """Button với hiệu ứng glow"""
    
    def __init__(self, parent, text="", icon="", command=None, 
                 width=50, height=50, bg=Theme.BG_CARD, 
                 fg=Theme.ACCENT_PRIMARY, **kwargs):
        super().__init__(parent, width=width, height=height, 
                        bg=Theme.BG_DARK, highlightthickness=0, **kwargs)
        
        self.command = command
        self.fg_color = fg
        self.bg_color = bg
        self.text = text
        self.icon = icon
        self.width = width
        self.height = height
        self.is_hovered = False
        
        self._draw()
        
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
    
    def _draw(self):
        self.delete("all")
        
        # Background circle/rounded rect
        padding = 4
        color = Theme.BG_HOVER if self.is_hovered else self.bg_color
        
        if self.width == self.height:
            # Circle button
            self.create_oval(padding, padding, 
                           self.width - padding, self.height - padding,
                           fill=color, outline=self.fg_color if self.is_hovered else "",
                           width=2)
        else:
            # Rounded rectangle
            self._create_rounded_rect(padding, padding, 
                                     self.width - padding, self.height - padding,
                                     radius=10, fill=color,
                                     outline=self.fg_color if self.is_hovered else "")
        
        # Text/Icon
        display = self.icon if self.icon else self.text
        self.create_text(self.width // 2, self.height // 2,
                        text=display, fill=self.fg_color,
                        font=("Segoe UI Symbol", 14, "bold"))
    
    def _create_rounded_rect(self, x1, y1, x2, y2, radius=10, **kwargs):
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)
    
    def _on_enter(self, event):
        self.is_hovered = True
        self._draw()
    
    def _on_leave(self, event):
        self.is_hovered = False
        self._draw()
    
    def _on_click(self, event):
        if self.command:
            self.command()


class ModernSlider(tk.Canvas):
    """Slider với thiết kế hiện đại"""
    
    def __init__(self, parent, width=300, height=20, 
                 min_val=0, max_val=100, value=0,
                 command=None, **kwargs):
        super().__init__(parent, width=width, height=height,
                        bg=Theme.BG_DARK, highlightthickness=0, **kwargs)
        
        self.min_val = min_val
        self.max_val = max_val
        self._value = value
        self.command = command
        self.width = width
        self.height = height
        
        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        
        self._draw()
    
    @property
    def value(self) -> float:
        return self._value
    
    @value.setter
    def value(self, val: float):
        self._value = max(self.min_val, min(self.max_val, val))
        self._draw()
    
    def _draw(self):
        self.delete("all")
        
        padding = 8
        track_height = 6
        track_y = self.height // 2 - track_height // 2
        
        # Track background
        self.create_rectangle(padding, track_y, 
                            self.width - padding, track_y + track_height,
                            fill=Theme.BG_HOVER, outline="")
        
        # Progress
        progress_ratio = (self._value - self.min_val) / (self.max_val - self.min_val) if self.max_val > self.min_val else 0
        progress_width = (self.width - 2 * padding) * progress_ratio
        
        if progress_width > 0:
            # Gradient effect với nhiều rectangles
            self.create_rectangle(padding, track_y,
                                padding + progress_width, track_y + track_height,
                                fill=Theme.ACCENT_PRIMARY, outline="")
        
        # Knob
        knob_x = padding + progress_width
        knob_radius = 8
        self.create_oval(knob_x - knob_radius, self.height // 2 - knob_radius,
                        knob_x + knob_radius, self.height // 2 + knob_radius,
                        fill=Theme.ACCENT_PRIMARY, outline=Theme.TEXT_PRIMARY, width=2)
    
    def _on_click(self, event):
        self._update_value(event.x)
    
    def _on_drag(self, event):
        self._update_value(event.x)
    
    def _update_value(self, x):
        padding = 8
        ratio = (x - padding) / (self.width - 2 * padding)
        ratio = max(0, min(1, ratio))
        self._value = self.min_val + ratio * (self.max_val - self.min_val)
        self._draw()
        
        if self.command:
            self.command(self._value)

