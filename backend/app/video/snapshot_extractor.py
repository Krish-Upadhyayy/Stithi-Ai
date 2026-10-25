"""OpenCV-based Video Inspection and Periodic Snapshot Extractor.

Converts recorded MP4 video feeds into periodic JPEG frames for subsequent
YOLO26 detection pipelines, avoiding high-bandwidth continuous video streaming.
"""

import os
import cv2
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class VideoProcessingError(Exception):
    """Raised when video file inspection or frame extraction fails."""
    pass


class SnapshotExtractor:
    """Manages OpenCV video inspection and seek-based periodic frame extraction."""

    def __init__(
        self,
        interval_seconds: int = 10,
        max_snapshots: int = 300,
        jpeg_quality: int = 85,
    ):
        self.interval_seconds = max(1, interval_seconds)
        self.max_snapshots = max_snapshots
        self.jpeg_quality = max(10, min(100, jpeg_quality))

    @staticmethod
    def inspect_video(video_path: str) -> Dict[str, Any]:
        """Inspects an MP4 video file using OpenCV and extracts technical properties.
        
        Args:
            video_path: Absolute or canonical path to the video file.
            
        Returns:
            Dictionary containing width, height, fps, total_frames, duration_seconds, codec.
            
        Raises:
            VideoProcessingError if the file is unreadable, corrupted, or has invalid metrics.
        """
        if not os.path.exists(video_path):
            raise VideoProcessingError(f"Video file does not exist: {video_path}")

        if os.path.getsize(video_path) == 0:
            raise VideoProcessingError("Video file is empty (0 bytes).")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            cap.release()
            raise VideoProcessingError("OpenCV failed to open video file. File may be corrupted or unsupported.")

        try:
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = float(cap.get(cv2.CAP_PROP_FPS))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))

            # Decode FOURCC codec identifier if available
            codec = "".join([chr((fourcc_int >> 8 * i) & 0xFF) for i in range(4)]).strip()

            if width <= 0 or height <= 0:
                raise VideoProcessingError(f"Invalid video dimensions: {width}x{height}")

            if fps <= 0.0 or total_frames <= 0:
                # Try reading at least the first frame to check if playable
                ret, frame = cap.read()
                if not ret or frame is None:
                    raise VideoProcessingError("Video contains 0 playable frames or invalid framerate.")
                # Fallback FPS if container did not specify
                fps = fps if fps > 0 else 25.0
                total_frames = max(total_frames, 1)

            duration_seconds = round(total_frames / fps, 2) if fps > 0 else 0.0

            return {
                "width": width,
                "height": height,
                "fps": round(fps, 2),
                "total_frames": total_frames,
                "duration_seconds": duration_seconds,
                "codec": codec or "H264",
            }
        except VideoProcessingError:
            raise
        except Exception as e:
            logger.error(f"Error inspecting video metadata for {video_path}: {e}", exc_info=True)
            raise VideoProcessingError(f"Failed to extract video metadata: {str(e)}")
        finally:
            cap.release()

    def extract_periodic_snapshots(
        self,
        video_path: str,
        output_dir: str,
    ) -> List[Dict[str, Any]]:
        """Extracts an initial frame at 00:00 and periodic frames at fixed intervals.
        
        Uses efficient frame seeking (CAP_PROP_POS_FRAMES) rather than decoding
        unnecessary intermediate frames to conserve memory and CPU.
        
        Args:
            video_path: Path to the target MP4 file.
            output_dir: Directory where JPEG snapshot files will be stored.
            
        Returns:
            List of dictionaries describing each extracted snapshot.
        """
        metadata = self.inspect_video(video_path)
        fps = metadata["fps"]
        total_frames = metadata["total_frames"]
        duration = metadata["duration_seconds"]

        os.makedirs(output_dir, exist_ok=True)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise VideoProcessingError(f"Failed to open video for extraction: {video_path}")

        extracted_records: List[Dict[str, Any]] = []

        try:
            # 1. Determine target frame indices:
            # Frame 0 is always the initial snapshot (00:00) per Prompt requirement §7
            target_timestamps: List[float] = [0.0]

            curr_time = float(self.interval_seconds)
            while curr_time < duration and len(target_timestamps) < self.max_snapshots:
                target_timestamps.append(curr_time)
                curr_time += float(self.interval_seconds)

            sequence = 1
            for t in target_timestamps:
                target_frame_num = int(round(t * fps))
                if target_frame_num >= total_frames and sequence > 1:
                    break

                # Seek directly to frame
                cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame_num)
                ret, frame = cap.read()

                if not ret or frame is None:
                    logger.warning(f"Could not read frame at timestamp {t}s (frame #{target_frame_num})")
                    continue

                actual_h, actual_w = frame.shape[:2]
                filename = f"snapshot_{sequence:06d}.jpg"
                file_path = os.path.join(output_dir, filename)

                # Write compressed JPEG
                encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
                success = cv2.imwrite(file_path, frame, encode_params)

                if not success or not os.path.exists(file_path):
                    logger.error(f"Failed to write snapshot image to {file_path}")
                    continue

                extracted_records.append({
                    "sequence_number": sequence,
                    "frame_time_seconds": round(t, 2),
                    "file_path": file_path,
                    "filename": filename,
                    "width": actual_w,
                    "height": actual_h,
                })
                sequence += 1

            if not extracted_records:
                raise VideoProcessingError("No frames could be successfully extracted from the video.")

            return extracted_records
        finally:
            cap.release()
