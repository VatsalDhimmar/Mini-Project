# service.py
import pyaudio, asyncio
import mss, cv2, base64, io
import PIL.Image
import time

class AudioHandler:
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    SEND_SAMPLE_RATE = 16000
    RECEIVE_SAMPLE_RATE = 24000
    CHUNK_SIZE = 512

    def __init__(self):
        self.pya = pyaudio.PyAudio()
        self.audio_in_queue = asyncio.Queue()
        self.out_queue = asyncio.Queue(maxsize=5)
        self.audio_stream = None
        self.playback_stream = None

    async def listen_audio(self):
        print("🎤 Starting audio listening...")
        try:
            mic_info = self.pya.get_default_input_device_info()
            self.audio_stream = await asyncio.to_thread(
                self.pya.open,
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.SEND_SAMPLE_RATE,
                input=True,
                input_device_index=mic_info["index"],
                frames_per_buffer=self.CHUNK_SIZE,
            )
            
            kwargs = {"exception_on_overflow": False} if __debug__ else {}
            
            while True:
                data = await asyncio.to_thread(self.audio_stream.read, self.CHUNK_SIZE, **kwargs)
                await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})
                
        except asyncio.CancelledError:
            print("Audio listening cancelled")
            if self.audio_stream:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            raise
        except Exception as e:
            print(f"Audio capture error: {e}")
            raise

    async def play_audio(self):
        print("🔊 Starting audio playback...")
        try:
            self.playback_stream = await asyncio.to_thread(
                self.pya.open,
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RECEIVE_SAMPLE_RATE,
                output=True,
                frames_per_buffer=self.CHUNK_SIZE,
            )
            
            while True:
                # Get audio from queue
                audio_data = await self.audio_in_queue.get()
                
                if audio_data:
                    print(f"🔊 Playing audio: {len(audio_data)} bytes")
                    await asyncio.to_thread(self.playback_stream.write, audio_data)
                    
        except asyncio.CancelledError:
            print("Audio playback cancelled")
            if self.playback_stream:
                self.playback_stream.stop_stream()
                self.playback_stream.close()
            raise
        except Exception as e:
            print(f"Audio playback error: {e}")
            raise

    def cleanup(self):
        """Clean up audio resources"""
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
        if self.playback_stream:
            self.playback_stream.stop_stream()
            self.playback_stream.close()
        self.pya.terminate()

class ScreenHandler:
    def __init__(self):
        self.out_queue = asyncio.Queue(maxsize=5)  # Keep small
        self.cap = None
        self.last_frame_time = 0
        self.min_frame_interval = 0.5  # Start with 2 FPS
        self.max_frame_interval = 2.0  # Minimum 0.5 FPS
        
    def _get_Screen(self):
        sct = mss.mss()
        monitor = sct.monitors[0]
        i = sct.grab(monitor)

        mime_type = "image/jpeg"
        image_bytes = mss.tools.to_png(i.rgb, i.size)
        img = PIL.Image.open(io.BytesIO(image_bytes))
        
        # MORE AGGRESSIVE COMPRESSION
        # Resize more aggressively based on queue status
        queue_size = self.out_queue.qsize()
        if queue_size > 3:
            # Queue is getting full, use lower quality
            img.thumbnail([1280, 720])
            quality = 60
        elif queue_size > 1:
            img.thumbnail([1600, 900])
            quality = 70
        else:
            img.thumbnail([1920, 1080])
            quality = 80
        
        image_io = io.BytesIO()
        img.save(image_io, format="jpeg", quality=quality)
        image_io.seek(0)

        image_bytes = image_io.read()
        return {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode()}
    
    async def Screen_Capture(self):
        print("🖥️ Starting adaptive screen capture...")
        try:
            while True:
                start_time = time.time()
                
                # Check queue pressure
                queue_ratio = self.out_queue.qsize() / self.out_queue.maxsize
                
                # Adaptive frame rate based on queue pressure
                if queue_ratio > 0.8:
                    # Queue almost full, slow down significantly
                    self.min_frame_interval = min(self.min_frame_interval * 1.5, self.max_frame_interval)
                    print(f"⚠️ Queue pressure high ({queue_ratio:.0%}), reducing to {1/self.min_frame_interval:.1f} FPS")
                elif queue_ratio < 0.3 and self.min_frame_interval > 0.5:
                    # Queue has room, speed up slightly
                    self.min_frame_interval *= 0.9
                    
                # Capture frame
                frame = await asyncio.to_thread(self._get_Screen)
                if frame is None:
                    break
                    
                # Try to add to queue, skip if full
                try:
                    self.out_queue.put_nowait(frame)
                    print(f"📸 Screen captured (queue: {self.out_queue.qsize()}/{self.out_queue.maxsize})")
                except asyncio.QueueFull:
                    print("⚠️ Skipping screen frame - queue full")
                    
                # Adaptive delay
                elapsed = time.time() - start_time
                delay = max(self.min_frame_interval - elapsed, 0.1)
                await asyncio.sleep(delay)
                
        except asyncio.CancelledError:
            print("Screen capture cancelled")
            raise

    async def Video_Capture(self):
        print("📹 Starting adaptive video capture...")
        self.cap = await asyncio.to_thread(cv2.VideoCapture, 0)
        self.min_frame_interval = 0.1  # Higher FPS for video
        
        try:
            while True:
                start_time = time.time()
                
                # Check queue pressure
                queue_ratio = self.out_queue.qsize() / self.out_queue.maxsize
                
                # Skip frames if queue is getting full
                if queue_ratio > 0.6:
                    # Read and discard frame to keep camera buffer clear
                    await asyncio.to_thread(self.cap.read)
                    await asyncio.sleep(0.1)
                    continue
                
                frame = await asyncio.to_thread(self._get_video, self.cap)
                if frame is None:
                    break
                    
                try:
                    self.out_queue.put_nowait(frame)
                except asyncio.QueueFull:
                    print("⚠️ Skipping video frame - queue full")
                    
                # Minimum delay between captures
                elapsed = time.time() - start_time
                delay = max(0.033 - elapsed, 0.01)  # Target ~30 FPS max
                await asyncio.sleep(delay)
                
        except asyncio.CancelledError:
            print("Video capture cancelled")
            raise
        finally:
            if self.cap:
                self.cap.release()
                self.cap = None

    def _get_video(self, cap):
        ret, frame = cap.read()
        if not ret:
            return None
        
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = PIL.Image.fromarray(frame_rgb)
        
        # Adaptive quality based on queue
        queue_size = self.out_queue.qsize()
        if queue_size > 3:
            img.thumbnail([480, 360])
            quality = 60
        else:
            img.thumbnail([640, 480])
            quality = 75

        image_io = io.BytesIO()
        img.save(image_io, format="jpeg", quality=quality)
        image_io.seek(0)

        mime_type = "image/jpeg"
        image_bytes = image_io.read()
        return {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode("utf-8")}