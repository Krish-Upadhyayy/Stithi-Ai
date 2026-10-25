"""Privacy and anonymization utilities.

Enforces privacy-preserving compliance:
- No biometric identity vectors
- Anonymization/blurring of detected face bounding boxes in evidence snapshots
"""

from typing import List, Tuple, Any
import numpy as np


class PrivacyEngine:
    """Provides privacy-preserving operations on images and detections."""

    @staticmethod
    def apply_face_blur(
        image: np.ndarray,
        bounding_boxes: List[Tuple[int, int, int, int]],
        blur_kernel_size: Tuple[int, int] = (51, 51)
    ) -> np.ndarray:
        """Applies Gaussian blur to detected face regions in evidence snapshots.
        
        Args:
            image: OpenCV BGR image array
            bounding_boxes: List of (x1, y1, x2, y2) coordinates
            blur_kernel_size: Size of Gaussian blur kernel
        """
        # Lazy import of cv2 to ensure lightweight utility access
        import cv2
        
        anonymized = image.copy()
        for (x1, y1, x2, y2) in bounding_boxes:
            # Bound coordinates safely
            h, w = image.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            
            if x2 > x1 and y2 > y1:
                roi = anonymized[y1:y2, x1:x2]
                blurred_roi = cv2.GaussianBlur(roi, blur_kernel_size, 30)
                anonymized[y1:y2, x1:x2] = blurred_roi
                
        return anonymized
