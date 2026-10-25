"""Configurable Inventory to AI Detection Class Mapping Layer.

Decouples centre-specific inventory item naming (e.g. 'Desktop Computer', 'Executive Chair')
from trained YOLO26 object detection classes (e.g. 'computer', 'chair').
Strict Constraint: If an inventory item has no trained AI class, it is flagged as
'AI detection not configured' to avoid erroneous classification.
"""

from typing import Dict, List, Optional, Set


# Canonical supported YOLO26 infrastructure detection classes
DEFAULT_SUPPORTED_AI_CLASSES: List[str] = [
    "chair",
    "computer",
    "projector",
    "sewing machine",
    "workbench",
]

# Configurable mapping rules: normalized inventory name substring / key -> AI class
DEFAULT_INVENTORY_TO_AI_CLASS_MAP: Dict[str, str] = {
    # Computers / Computing assets
    "computer": "computer",
    "desktop computer": "computer",
    "desktop": "computer",
    "pc": "computer",
    "laptop": "computer",
    "workstation": "computer",

    # Chairs / Seating assets
    "chair": "chair",
    "office chair": "chair",
    "student chair": "chair",
    "revolving chair": "chair",
    "plastic chair": "chair",
    "bench": "chair",

    # Presentation / AV equipment
    "projector": "projector",
    "digital projector": "projector",
    "multimedia projector": "projector",

    # Vocational / Training machines
    "sewing machine": "sewing machine",
    "industrial sewing machine": "sewing machine",
    "stitching machine": "sewing machine",

    # Workbenches / Workshop tables
    "workbench": "workbench",
    "work bench": "workbench",
    "workshop table": "workbench",
    "training table": "workbench",
}


class InventoryClassMapper:
    """Manages mapping between Sanctioned Inventory Items and trained AI Detection Classes."""

    def __init__(
        self,
        supported_classes: Optional[List[str]] = None,
        custom_mappings: Optional[Dict[str, str]] = None,
    ):
        self.supported_classes: List[str] = supported_classes or list(DEFAULT_SUPPORTED_AI_CLASSES)
        self.mapping_dict: Dict[str, str] = dict(DEFAULT_INVENTORY_TO_AI_CLASS_MAP)
        if custom_mappings:
            self.mapping_dict.update(custom_mappings)

    def normalize_name(self, name: str) -> str:
        return name.strip().lower()

    def map_inventory_to_class(self, item_name: str) -> Optional[str]:
        """Maps an inventory item name to a supported AI class, or None if not configured."""
        if not item_name:
            return None

        norm = self.normalize_name(item_name)

        # 1. Exact match in mapping dictionary
        if norm in self.mapping_dict:
            target_class = self.mapping_dict[norm]
            if target_class in self.supported_classes:
                return target_class

        # 2. Substring matching for compound names (longest key match first)
        for key in sorted(self.mapping_dict.keys(), key=len, reverse=True):
            if key in norm:
                target_class = self.mapping_dict[key]
                if target_class in self.supported_classes:
                    return target_class

        # No trained detector configured for this item
        return None

    def get_status_for_item(self, item_name: str) -> str:
        """Returns the configuration status message for an inventory item."""
        mapped = self.map_inventory_to_class(item_name)
        if mapped is not None:
            return f"Configured ({mapped})"
        return "AI detection not configured"

    def is_ai_detection_configured(self, item_name: str) -> bool:
        """Returns True if the inventory item maps to a trained AI class."""
        return self.map_inventory_to_class(item_name) is not None


# Global singleton instance
default_mapper = InventoryClassMapper()
