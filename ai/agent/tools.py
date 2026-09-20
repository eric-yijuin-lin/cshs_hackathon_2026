def get_device_status(device_id: str) -> dict:
    data = {
        "sensor-01": {
            "temperature": 38.2,
            "status": "warning",
        },
        "sensor-02": {
            "temperature": 24.7,
            "status": "normal",
        },
    }

    return data.get(
        device_id,
        {
            "error": "device not found",
        },
    )