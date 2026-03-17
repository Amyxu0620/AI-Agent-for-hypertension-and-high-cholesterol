from collections import defaultdict


def detect_risks(daily_logs, metrics):
    alerts = []

    # Daily log checks
    if daily_logs:
        recent_logs = daily_logs[-3:]  # latest 3 logs

        low_sleep_days = sum(1 for log in recent_logs if log.sleep_hours < 5)
        low_steps_days = sum(1 for log in recent_logs if log.steps < 2000)
        negative_mood_days = sum(
            1 for log in recent_logs
            if any(word in (log.emotional_state or "").lower() for word in ["sad", "anxious", "depressed", "upset", "stressed"])
        )

        if low_sleep_days >= 2:
            alerts.append({
                "severity": "caution",
                "alert_type": "risk",
                "message": "Sleep has been below 5 hours on at least 2 of the last 3 recorded days."
            })

        if low_steps_days >= 3:
            alerts.append({
                "severity": "caution",
                "alert_type": "risk",
                "message": "Activity has been low for 3 consecutive recorded days."
            })

        if negative_mood_days >= 2:
            alerts.append({
                "severity": "caution",
                "alert_type": "risk",
                "message": "Emotional state appears negative on multiple recent days."
            })

    # Metric checks
    grouped = defaultdict(list)
    for m in metrics:
        grouped[m.metric_type].append(m.value)

    systolic = grouped.get("systolic_bp", [])
    diastolic = grouped.get("diastolic_bp", [])
    resting_hr = grouped.get("resting_hr", [])

    if systolic and systolic[-1] >= 180:
        alerts.append({
            "severity": "urgent",
            "alert_type": "risk",
            "message": "Latest systolic blood pressure is critically high."
        })

    if diastolic and diastolic[-1] >= 120:
        alerts.append({
            "severity": "urgent",
            "alert_type": "risk",
            "message": "Latest diastolic blood pressure is critically high."
        })

    if resting_hr and resting_hr[-1] >= 120:
        alerts.append({
            "severity": "caution",
            "alert_type": "risk",
            "message": "Latest resting heart rate is unusually high."
        })

    return alerts
