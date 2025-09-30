import sys, signal
import asyncio
import threading
from PySide6.QtCore import Qt, QPoint, QThread, Signal, QTimer
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtWidgets import QApplication, QLabel, QWidget
from api import WSClient


class AsyncThread(QThread):
    """Thread to run asyncio tasks"""
    def __init__(self, coro):
        super().__init__()
        self.coro = coro
        self.loop = None
        
    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.coro)
        
    def stop(self):
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)


class StatusPopup(QLabel):
    """Status popup that appears above character"""
    def __init__(self, parent):
        super().__init__(parent)
        self.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 180);
                color: white;
                padding: 8px 16px;
                border-radius: 15px;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        self.setAlignment(Qt.AlignCenter)
        self.hide()
        
    def show_status(self, text, color="#00ff00"):
        """Show status with optional color"""
        self.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(0, 0, 0, 180);
                color: {color};
                padding: 8px 16px;
                border-radius: 15px;
                font-size: 14px;
                font-weight: bold;
                border: 2px solid {color};
            }}
        """)
        self.setText(text)
        self.show()
        self.raise_()  # Make sure it's on top
        
    def update_position(self, parent_widget):
        """Position popup above parent widget"""
        self.adjustSize()
        # Position relative to parent widget
        parent_width = parent_widget.width()
        x = (parent_width - self.width()) // 2
        y = -self.height() - 10  # Above the parent
        self.move(x, y)


class OverlaySprite(QWidget):
    def __init__(self,
                 idle_image, 
                 drag_image,
                 scale=2.0):
        super().__init__()

        # Frameless transparent always-on-top window
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # Load static images
        self.idle_image = QPixmap(idle_image)
        self.drag_image = QPixmap(drag_image)
        
        self.scale = scale
        self.current_image = self.idle_image

        # Display label
        self.label = QLabel(self)
        
        # Create status popup BEFORE calling update_image
        self.status_popup = StatusPopup(self)
        
        # Now safe to call update_image
        self.update_image(self.idle_image)
        
        # Drag states
        self.dragging = False
        self.drag_position = QPoint()

        # Single thread for combined mode
        self.active_thread = None
        self.current_mode = None
        
        # Status update timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status_animation)
        self.status_dots = 0
        self.base_status_text = ""

    def update_image(self, pixmap):
        """Update the displayed static image"""
        scaled_image = pixmap.scaled(
            int(pixmap.width() * self.scale),
            int(pixmap.height() * self.scale),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.label.setPixmap(scaled_image)
        self.label.resize(scaled_image.size())
        self.resize(scaled_image.size())
        
        # Update popup position - pass the widget, not geometry
        if hasattr(self, 'status_popup'):
            self.status_popup.update_position(self)

    def set_status(self, text, color="#00ff00", animated=False):
        """Set status text with optional animation"""
        self.base_status_text = text
        self.status_popup.show_status(text, color)
        self.status_popup.update_position(self)
        
        if animated:
            self.status_dots = 0
            self.status_timer.start(500)
        else:
            self.status_timer.stop()
            
    def update_status_animation(self):
        """Animate status text with dots"""
        self.status_dots = (self.status_dots + 1) % 4
        dots = "." * self.status_dots
        self.status_popup.setText(f"{self.base_status_text}{dots}")

    def start_mode(self, mode):
        """Start a specific mode with audio"""
        # Only stop if switching to a different mode or stopping current mode
        if self.current_mode == mode:
            # Same mode clicked - stop it
            self.stop_current_session()
            return
            
        # Stop existing session if different mode
        if self.current_mode and self.current_mode != mode:
            self.stop_current_session()
        
        # Create new WebSocket client for this mode
        ws_client = WSClient()
        
        self.current_mode = mode
        
        # Start the combined thread
        print(f"🚀 Starting {mode} mode...")
        self.active_thread = AsyncThread(ws_client.run_combined_client(mode))
        self.active_thread.start()
        
        # Set appropriate status
        if mode == "audio":
            self.set_status("🎤 Listening", "#00ff00", animated=True)
        elif mode == "screen":
            self.set_status("📺 Screen Recording", "#00ffff", animated=True)
        elif mode == "video":
            self.set_status("📹 Video Capture", "#ff00ff", animated=True)

    def stop_current_session(self):
        """Stop the current active session"""
        self.status_timer.stop()
        
        if self.active_thread and self.active_thread.isRunning():
            print(f"Stopping {self.current_mode} mode...")
            self.active_thread.stop()
            self.active_thread.wait()
            
        self.active_thread = None
        self.current_mode = None
        self.status_popup.hide()

    # ===== Click Handlers =====
    def on_double_left_click(self):
        """Start/Stop audio only mode"""
        print("🎤 Double Left-Click: Audio mode")
        self.start_mode("audio")

    def on_right_click(self):
        """Start/Stop screen recording with audio"""
        print("🖥️ Right-Click: Screen recording mode")
        self.start_mode("screen")

    def on_double_right_click(self):
        """Start/Stop video capture with audio"""
        print("📹 Double Right-Click: Video capture mode")
        self.start_mode("screen")

    # ===== Mouse Events =====
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.update_image(self.drag_image)
            
            # Update popup position while dragging
            if self.status_popup.isVisible():
                self.status_popup.update_position(self)

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            
            # Update popup position while dragging
            if self.status_popup.isVisible():
                self.status_popup.update_position(self)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.update_image(self.idle_image)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.on_double_left_click()
        elif event.button() == Qt.RightButton:
            self.on_double_right_click()


    def moveEvent(self, event):
        """Update popup position when window moves"""
        super().moveEvent(event)
        if hasattr(self, 'status_popup') and self.status_popup.isVisible():
            self.status_popup.update_position(self)

    def closeEvent(self, event):
        """Clean up when closing"""
        self.stop_current_session()
        event.accept()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    app = QApplication(sys.argv)
    
    overlay = OverlaySprite(
        idle_image="boy-01-bg.png",  # Your idle image
        drag_image="boy-02-bg.png",  # Your drag image
        scale=0.5
    )
    
    overlay.show()
    sys.exit(app.exec())