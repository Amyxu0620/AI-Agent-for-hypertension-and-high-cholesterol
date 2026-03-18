import os
from collections import defaultdict
import matplotlib.pyplot as plt

CHART_DIR = "charts"
os.makedirs(CHART_DIR, exist_ok=True)

def generate_weekly_charts(metrics, patient_id: int):
    grouped = defaultdict(list)
    for item in metrics:
        grouped[item.metric_type].append((item.recorded_at, item.value))
    chart_paths = []
    for metric_type, values in grouped.items():
        values.sort(key=lambda x: x[0])
        x = [dt.strftime("%m-%d") for dt, _ in values]
        y = [val for _, val in values]
        plt.figure()
        plt.plot(x, y, marker="o")
        plt.title(f"{metric_type} - Last 7 Days")
        plt.xlabel("Date")
        plt.ylabel(metric_type)
        plt.xticks(rotation=45)
        plt.tight_layout()
        filepath = os.path.join(CHART_DIR, f"patient_{patient_id}_{metric_type}.png")
        plt.savefig(filepath)
        plt.close()
        chart_paths.append(filepath)

    return chart_paths
