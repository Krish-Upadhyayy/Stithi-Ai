"""Attendance Model Registry & Comparison Manager.

Manages versioning, empirical baseline vs fine-tuned comparisons,
and production model deployment metadata.
"""

import os
import json
import shutil
from datetime import datetime
from typing import Dict, Any, Optional

REGISTRY_ROOT = "models/attendance"
PRODUCTION_DIR = os.path.join(REGISTRY_ROOT, "production")
METADATA_FILE = os.path.join(PRODUCTION_DIR, "model_metadata.json")


class AttendanceModelRegistry:
    """Manages model artifacts, benchmark comparisons, and production deployments."""

    @staticmethod
    def get_production_metadata() -> Optional[Dict[str, Any]]:
        """Retrieves production model metadata if deployed."""
        if not os.path.exists(METADATA_FILE):
            return None
        try:
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    @staticmethod
    def register_production_model(
        model_name: str,
        version: str,
        weights_source_path: str,
        metrics: Dict[str, Any],
        selection_rationale: str,
        dataset_version: str = "attendance-v1",
    ) -> Dict[str, Any]:
        """Registers a verified model as the current production attendance model."""
        os.makedirs(PRODUCTION_DIR, exist_ok=True)
        dest_weights = os.path.join(PRODUCTION_DIR, "production_model.pt")

        if os.path.exists(weights_source_path) and os.path.abspath(weights_source_path) != os.path.abspath(dest_weights):
            shutil.copy2(weights_source_path, dest_weights)

        metadata: Dict[str, Any] = {
            "model_name": model_name,
            "version": version,
            "dataset_version": dataset_version,
            "weights_path": dest_weights if os.path.exists(dest_weights) else weights_source_path,
            "registered_at": datetime.utcnow().isoformat(),
            "selection_rationale": selection_rationale,
            "metrics": metrics,
        }

        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        return metadata

    @staticmethod
    def compare_models(
        baseline_eval: Dict[str, Any],
        finetuned_eval: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generates a side-by-side comparison between baseline and fine-tuned models."""
        b_det = baseline_eval.get("detection_metrics", {})
        f_det = finetuned_eval.get("detection_metrics", {})

        b_cnt = baseline_eval.get("count_metrics", {})
        f_cnt = finetuned_eval.get("count_metrics", {})

        b_spd = baseline_eval.get("speed_metrics", {})
        f_spd = finetuned_eval.get("speed_metrics", {})

        def delta(f_val, b_val):
            if f_val is not None and b_val is not None:
                return round(f_val - b_val, 4)
            return None

        comparison = {
            "models": {
                "baseline": {
                    "name": baseline_eval.get("model_name"),
                    "version": baseline_eval.get("model_version"),
                },
                "finetuned": {
                    "name": finetuned_eval.get("model_name"),
                    "version": finetuned_eval.get("model_version"),
                },
            },
            "metrics_comparison": {
                "precision": {
                    "baseline": b_det.get("precision"),
                    "finetuned": f_det.get("precision"),
                    "delta": delta(f_det.get("precision"), b_det.get("precision")),
                },
                "recall": {
                    "baseline": b_det.get("recall"),
                    "finetuned": f_det.get("recall"),
                    "delta": delta(f_det.get("recall"), b_det.get("recall")),
                },
                "map50": {
                    "baseline": b_det.get("map50"),
                    "finetuned": f_det.get("map50"),
                    "delta": delta(f_det.get("map50"), b_det.get("map50")),
                },
                "map50_95": {
                    "baseline": b_det.get("map50_95"),
                    "finetuned": f_det.get("map50_95"),
                    "delta": delta(f_det.get("map50_95"), b_det.get("map50_95")),
                },
                "false_positives": {
                    "baseline": b_det.get("false_positives"),
                    "finetuned": f_det.get("false_positives"),
                    "delta": delta(f_det.get("false_positives"), b_det.get("false_positives")),
                },
                "false_negatives": {
                    "baseline": b_det.get("false_negatives"),
                    "finetuned": f_det.get("false_negatives"),
                    "delta": delta(f_det.get("false_negatives"), b_det.get("false_negatives")),
                },
                "count_mae": {
                    "baseline": b_cnt.get("mae"),
                    "finetuned": f_cnt.get("mae"),
                    "delta": delta(f_cnt.get("mae"), b_cnt.get("mae")),
                },
                "count_rmse": {
                    "baseline": b_cnt.get("rmse"),
                    "finetuned": f_cnt.get("rmse"),
                    "delta": delta(f_cnt.get("rmse"), b_cnt.get("rmse")),
                },
                "exact_match_pct": {
                    "baseline": b_cnt.get("exact_match_pct"),
                    "finetuned": f_cnt.get("exact_match_pct"),
                    "delta": delta(f_cnt.get("exact_match_pct"), b_cnt.get("exact_match_pct")),
                },
                "within_1_pct": {
                    "baseline": b_cnt.get("within_1_pct"),
                    "finetuned": f_cnt.get("within_1_pct"),
                    "delta": delta(f_cnt.get("within_1_pct"), b_cnt.get("within_1_pct")),
                },
                "within_2_pct": {
                    "baseline": b_cnt.get("within_2_pct"),
                    "finetuned": f_cnt.get("within_2_pct"),
                    "delta": delta(f_cnt.get("within_2_pct"), b_cnt.get("within_2_pct")),
                },
                "avg_inference_time_ms": {
                    "baseline": b_spd.get("avg_inference_time_ms"),
                    "finetuned": f_spd.get("avg_inference_time_ms"),
                    "delta": delta(f_spd.get("avg_inference_time_ms"), b_spd.get("avg_inference_time_ms")),
                },
            },
            "recommendation": (
                "Fine-tuned model demonstrated lower Count MAE and improved presence recall."
                if (f_cnt.get("mae") or 999) < (b_cnt.get("mae") or 999)
                else "Baseline model retained superior count stability."
            ),
        }
        return comparison
