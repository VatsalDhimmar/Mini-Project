# api.py
import asyncio
import json
import websockets
from service import AudioHandler, ScreenHandler


class WSClient:
    def __init__(self, uri="ws://localhost:8000/ws"):
        self.uri = uri
        self.ws = None
        self.running = False
        
    async def run_combined_client(self, mode="audio"):
        """Run a combined client that handles audio + optional video/screen"""
        # Create fresh handlers for this event loop
        audio = AudioHandler()
        screen = ScreenHandler() if mode in ["screen", "video"] else None
        
        try:
            self.ws = await websockets.connect(self.uri, ping_interval=None)
            self.running = True
            print(f"✅ Connected to WebSocket for {mode} mode")

            # Create all tasks
            tasks = []
            
            # Audio tasks (always needed)
            audio_capture_task = asyncio.create_task(audio.listen_audio())
            audio_playback_task = asyncio.create_task(audio.play_audio())
            audio_receive_task = asyncio.create_task(self.receive_audio_loop(audio))
            
            tasks.extend([audio_capture_task, audio_playback_task, audio_receive_task])
            
            # Main send loop that handles all data types
            send_task = asyncio.create_task(self.main_send_loop(mode, audio, screen))
            tasks.append(send_task)
            
            # Video/Screen capture task
            if mode == "screen" and screen:
                screen_task = asyncio.create_task(screen.Screen_Capture())
                tasks.append(screen_task)
            elif mode == "video" and screen:
                video_task = asyncio.create_task(screen.Video_Capture())
                tasks.append(video_task)

            # Wait for all tasks
            await asyncio.gather(*tasks)
            
        except asyncio.CancelledError:
            print(f"{mode} client cancelled")
            self.running = False
            # Clean up all tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            # Clean up audio
            if hasattr(audio, 'cleanup'):
                audio.cleanup()
            raise
            
        except Exception as e:
            print(f"⚠️ {mode} WebSocket error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.running = False
            if self.ws:
                await self.ws.close()
            self.ws = None

    async def main_send_loop(self, mode, audio, screen):
        """Single send loop that handles all data types with fair scheduling"""
        while self.running:
            sent_something = False
            
            # Try to send audio (non-blocking)
            try:
                audio_packet = audio.out_queue.get_nowait()
                await self.send_audio_packet(audio_packet)
                sent_something = True
            except asyncio.QueueEmpty:
                pass
            
            # Try to send video/screen (non-blocking)
            if screen:
                try:
                    frame = screen.out_queue.get_nowait()
                    if mode == "screen":
                        await self.send_screen_frame(frame)
                    elif mode == "video":
                        await self.send_video_frame(frame)
                    sent_something = True
                except asyncio.QueueEmpty:
                    pass
            
            # If nothing was sent, sleep briefly to avoid busy-waiting
            if not sent_something:
                await asyncio.sleep(0.01)

    async def send_audio_packet(self, packet):
        """Send audio packet"""
        try:
            data = packet["data"]
            header = {"type": "audio", "length": len(data)}
            await self.ws.send(json.dumps(header))
            await self.ws.send(data)
            print(f"📤 Sent audio: {len(data)} bytes")
        except Exception as e:
            print(f"Error sending audio: {e}")

    async def send_screen_frame(self, frame):
        """Send screen frame"""
        try:
            message = {
                "type": "screen",
                "mime_type": frame["mime_type"],
                "data": frame["data"]
            }
            await self.ws.send(json.dumps(message))
            print("📤 Sent screen frame")
        except Exception as e:
            print(f"Error sending screen: {e}")

    async def send_video_frame(self, frame):
        """Send video frame"""
        try:
            message = {
                "type": "video",
                "mime_type": frame["mime_type"],
                "data": frame["data"]
            }
            await self.ws.send(json.dumps(message))
            print("📤 Sent video frame")
        except Exception as e:
            print(f"Error sending video: {e}")

    async def receive_audio_loop(self, audio):
        """Dedicated loop for receiving audio - runs independently"""
        print("🎧 Starting audio receive loop...")
        
        try:
            async for message in self.ws:
                if not self.running:
                    break
                    
                try:
                    if isinstance(message, bytes):
                        # Audio data from backend
                        print(f"📥 Received audio: {len(message)} bytes")
                        await audio.audio_in_queue.put(message)
                        
                    elif isinstance(message, str):
                        # JSON message
                        data = json.loads(message)
                        print(f"📥 Received message: {data}")
                except Exception as e:
                    print(f"Error processing received message: {e}")
                    
        except Exception as e:
            if self.running:
                print(f"Error in receive loop: {e}")

    # Compatibility methods
    async def run_audio_client(self):
        await self.run_combined_client("audio")
        
    async def run_screen_client(self):
        await self.run_combined_client("screen")
        
    async def run_video_client(self):
        await self.run_combined_client("video")