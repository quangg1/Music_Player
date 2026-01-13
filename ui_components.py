
import tkinter as tk
import math
from theme import Theme


class GlowButton(tk.Canvas):
    """Button với hiệu ứng glow và pulse animation"""
    
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
        self.glow_intensity = 0.0
        self.animation_id = None
        
        self._draw()
        
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
    
    def _draw(self):
        self.delete("all")
        
        # Background circle/rounded rect với glow effect
        padding = 4
        color = Theme.BG_HOVER if self.is_hovered else self.bg_color
        
        # Glow effect khi hover
        if self.is_hovered and self.glow_intensity > 0:
            glow_alpha = int(self.glow_intensity * 50)
            glow_color = self._hex_with_alpha(self.fg_color, glow_alpha)
            glow_padding = padding - int(self.glow_intensity * 3)
            
            if self.width == self.height:
                self.create_oval(glow_padding, glow_padding,
                               self.width - glow_padding, self.height - glow_padding,
                               fill="", outline=glow_color, width=3)
            else:
                self._create_rounded_rect(glow_padding, glow_padding,
                                        self.width - glow_padding, self.height - glow_padding,
                                        radius=10, fill="", outline=glow_color, width=3)
        
        if self.width == self.height:
            # Circle button với shadow
            self.create_oval(padding + 1, padding + 1, 
                           self.width - padding + 1, self.height - padding + 1,
                           fill="#000000", outline="", width=0)
            self.create_oval(padding, padding, 
                           self.width - padding, self.height - padding,
                           fill=color, outline=self.fg_color if self.is_hovered else "",
                           width=2 if self.is_hovered else 1)
        else:
            # Rounded rectangle với shadow
            self._create_rounded_rect(padding + 1, padding + 1,
                                     self.width - padding + 1, self.height - padding + 1,
                                     radius=10, fill="#000000", outline="")
            self._create_rounded_rect(padding, padding, 
                                     self.width - padding, self.height - padding,
                                     radius=10, fill=color,
                                     outline=self.fg_color if self.is_hovered else "",
                                     width=2 if self.is_hovered else 1)
        
        # Text/Icon với scale effect khi hover
        display = self.icon if self.icon else self.text
        scale = 1.1 if self.is_hovered else 1.0
        font_size = int(14 * scale)
        self.create_text(self.width // 2, self.height // 2,
                        text=display, fill=self.fg_color,
                        font=("Segoe UI Symbol", font_size, "bold"))
    
    def _hex_with_alpha(self, hex_color, alpha):
        """Convert hex color với alpha (0-255)"""
        # Tkinter không hỗ trợ alpha trực tiếp, dùng workaround
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        # Blend với background
        bg_r, bg_g, bg_b = 10, 10, 15  # BG_DARK
        new_r = int(r * (alpha/255) + bg_r * (1 - alpha/255))
        new_g = int(g * (alpha/255) + bg_g * (1 - alpha/255))
        new_b = int(b * (alpha/255) + bg_b * (1 - alpha/255))
        return f"#{new_r:02x}{new_g:02x}{new_b:02x}"
    
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
    
    def _animate_glow(self):
        """Animate glow effect"""
        if self.is_hovered:
            self.glow_intensity = min(1.0, self.glow_intensity + 0.1)
        else:
            self.glow_intensity = max(0.0, self.glow_intensity - 0.1)
        
        self._draw()
        
        if self.glow_intensity > 0 or self.is_hovered:
            self.animation_id = self.after(20, self._animate_glow)
    
    def _on_enter(self, event):
        self.is_hovered = True
        if not self.animation_id:
            self._animate_glow()
    
    def _on_leave(self, event):
        self.is_hovered = False
        if not self.animation_id:
            self._animate_glow()
    
    def _on_click(self, event):
        if self.command:
            # Pulse effect khi click
            original_glow = self.glow_intensity
            self.glow_intensity = 1.0
            self._draw()
            self.after(100, lambda: setattr(self, 'glow_intensity', original_glow) or self._draw())
            self.command()


class ModernSlider(tk.Canvas):
    """Slider với thiết kế hiện đại và gradient animation"""
    
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
        self.is_dragging = False
        self.gradient_offset = 0.0
        
        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        
        self._animate_gradient()
        self._draw()
    
    @property
    def value(self) -> float:
        return self._value
    
    @value.setter
    def value(self, val: float):
        self._value = max(self.min_val, min(self.max_val, val))
        self._draw()
    
    def _animate_gradient(self):
        """Animate gradient effect"""
        self.gradient_offset = (self.gradient_offset + 0.02) % (2 * math.pi)
        if not self.is_dragging:
            self._draw()
        self.after(30, self._animate_gradient)
    
    def _draw(self):
        self.delete("all")
        
        padding = 8
        track_height = 8
        track_y = self.height // 2 - track_height // 2
        
        # Track background với shadow
        self.create_rectangle(padding + 1, track_y + 1, 
                            self.width - padding + 1, track_y + track_height + 1,
                            fill="#000000", outline="")
        self.create_rectangle(padding, track_y, 
                            self.width - padding, track_y + track_height,
                            fill=Theme.BG_HOVER, outline="")
        
        # Progress với gradient animation
        progress_ratio = (self._value - self.min_val) / (self.max_val - self.min_val) if self.max_val > self.min_val else 0
        progress_width = (self.width - 2 * padding) * progress_ratio
        
        if progress_width > 0:
            # Gradient effect với animation
            segments = 20
            segment_width = progress_width / segments
            for i in range(segments):
                x1 = padding + i * segment_width
                x2 = padding + (i + 1) * segment_width
                
                # Gradient từ cyan đến pink
                t = (i / segments + self.gradient_offset / (2 * math.pi)) % 1.0
                r1, g1, b1 = 0, 212, 255  # Cyan
                r2, g2, b2 = 255, 0, 110  # Pink
                r = int(r1 + (r2 - r1) * t)
                g = int(g1 + (g2 - g1) * t)
                b = int(b1 + (b2 - b1) * t)
                color = f"#{r:02x}{g:02x}{b:02x}"
                
                self.create_rectangle(x1, track_y, x2, track_y + track_height,
                                     fill=color, outline="")
        
        # Knob với glow effect
        knob_x = padding + progress_width
        knob_radius = 10 if self.is_dragging else 8
        
        # Glow effect
        if self.is_dragging:
            for r in range(12, 16):
                alpha = 1.0 - (r - 12) / 4.0
                glow_color = self._hex_with_alpha(Theme.ACCENT_PRIMARY, int(alpha * 100))
                self.create_oval(knob_x - r, self.height // 2 - r,
                               knob_x + r, self.height // 2 + r,
                               fill="", outline=glow_color, width=1)
        
        # Knob shadow
        self.create_oval(knob_x - knob_radius + 1, self.height // 2 - knob_radius + 1,
                        knob_x + knob_radius + 1, self.height // 2 + knob_radius + 1,
                        fill="#000000", outline="")
        # Knob
        self.create_oval(knob_x - knob_radius, self.height // 2 - knob_radius,
                        knob_x + knob_radius, self.height // 2 + knob_radius,
                        fill=Theme.ACCENT_PRIMARY, outline=Theme.TEXT_PRIMARY, width=2)
    
    def _hex_with_alpha(self, hex_color, alpha):
        """Convert hex color với alpha (0-255)"""
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        bg_r, bg_g, bg_b = 18, 18, 30  # BG_HOVER
        new_r = int(r * (alpha/255) + bg_r * (1 - alpha/255))
        new_g = int(g * (alpha/255) + bg_g * (1 - alpha/255))
        new_b = int(b * (alpha/255) + bg_b * (1 - alpha/255))
        return f"#{new_r:02x}{new_g:02x}{new_b:02x}"
    
    def _on_click(self, event):
        self.is_dragging = True
        self._update_value(event.x)
    
    def _on_drag(self, event):
        self._update_value(event.x)
    
    def _on_release(self, event):
        self.is_dragging = False
        self._draw()
    
    def _on_enter(self, event):
        pass
    
    def _on_leave(self, event):
        self.is_dragging = False
    
    def _update_value(self, x):
        padding = 8
        ratio = (x - padding) / (self.width - 2 * padding)
        ratio = max(0, min(1, ratio))
        self._value = self.min_val + ratio * (self.max_val - self.min_val)
        self._draw()
        
        if self.command:
            self.command(self._value)


