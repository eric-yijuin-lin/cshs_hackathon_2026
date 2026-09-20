TOOLS = [
    {
        "type": "function",
        "name": "get_device_status",
        "description": "Get the current status of a device by its device ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "The ID of the device, for example sensor-01.",
                }
            },
            "required": ["device_id"],
            "additionalProperties": False,
        },
        "strict": True,
    }
]