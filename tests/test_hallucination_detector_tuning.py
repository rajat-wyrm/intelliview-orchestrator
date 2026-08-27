import json
from pathlib import Path

from orchestrator.hallucination_detector import HallucinationDetector

DATA_FILE = Path(__file__).parent / "data" / "hallucination_test_set.json"


def load_test_set():
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def run_evaluation(threshold=0.5):
    data = load_test_set()

    detector = HallucinationDetector(hallucination_threshold=threshold)

    results = []

    for sample in data:
        result = detector.evaluate(
            source_context=sample["source_context"],
            generated_response=sample["generated_response"],
        )

        results.append(
            {
                "id": sample["id"],
                "label": sample["label"],
                "score": result.hallucination_score,
                "predicted": result.is_hallucination,
            }
        )

    return results


def calculate_metrics(results):
    factual = [r for r in results if r["label"] == "factual"]
    hallucinated = [r for r in results if r["label"] == "hallucinated"]

    false_positives = [r for r in factual if r["predicted"]]
    true_negatives = [r for r in factual if not r["predicted"]]

    true_positives = [r for r in hallucinated if r["predicted"]]
    false_negatives = [r for r in hallucinated if not r["predicted"]]

    fp_rate = len(false_positives) / len(factual)
    tp_rate = len(true_positives) / len(hallucinated)

    return {
        "tp": len(true_positives),
        "fp": len(false_positives),
        "tn": len(true_negatives),
        "fn": len(false_negatives),
        "fpr": fp_rate,
        "tpr": tp_rate,
    }


def print_results(threshold, metrics):
    print(
        f"{threshold:.2f} | "
        f"TP={metrics['tp']} | "
        f"FP={metrics['fp']} | "
        f"TN={metrics['tn']} | "
        f"FN={metrics['fn']} | "
        f"FPR={metrics['fpr']:.2%} | "
        f"TPR={metrics['tpr']:.2%}"
    )


def main():
    print("\n===== ISSUE #50: THRESHOLD EXPERIMENT =====")

    print(
        "\nThreshold | TP | FP | TN | FN | " "False Positive Rate | True Positive Rate"
    )
    print("-" * 75)

    thresholds = [
        0.30,
        0.35,
        0.40,
        0.45,
        0.50,
        0.55,
        0.60,
    ]

    experiment_results = []

    for threshold in thresholds:
        results = run_evaluation(threshold)
        metrics = calculate_metrics(results)

        experiment_results.append(
            {
                "threshold": threshold,
                **metrics,
            }
        )

        print_results(threshold, metrics)

    print("\n===== BEST CANDIDATES =====")

    candidates = [r for r in experiment_results if r["tpr"] >= 0.90]

    if candidates:
        best = min(candidates, key=lambda r: (r["fpr"], -r["tpr"]))

        print(f"Best threshold: {best['threshold']:.2f}")
        print(f"TPR: {best['tpr']:.2%}")
        print(f"FPR: {best['fpr']:.2%}")
        print(
            f"TP: {best['tp']}, "
            f"FP: {best['fp']}, "
            f"TN: {best['tn']}, "
            f"FN: {best['fn']}"
        )

        print("\nCurrent baseline threshold: 0.50")
        print("Current baseline TPR: 90%")
        print("Selected threshold must maintain TPR >= 90%.")

    else:
        print("No threshold maintained the baseline TPR of 90%.")


if __name__ == "__main__":
    main()
