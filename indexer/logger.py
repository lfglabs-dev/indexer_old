import requests
import json
import datetime


class Logger:
    def __init__(self, config):
        self.config = config
        self.app_id = config.watchtower_app_id
        self.token = config.watchtower_token
        self.endpoint = config.watchtower_endpoint
        self.types = {
            "info": config.watchtower_info,
            "warning": config.watchtower_warning,
            "severe": config.watchtower_severe,
        }

    def post_log(self, log_type, message):
        headers = {"Content-Type": "application/json"}

        data = {
            "token": self.token,
            "log": {
                "app_id": self.app_id,
                "type": self.types[log_type],
                "message": message,
                "timestamp": int(datetime.datetime.now().timestamp() * 1000),
            },
        }
        response = requests.post(self.endpoint, data=json.dumps(data), headers=headers)
        if response.status_code != 200:
            print("Failed to post log: ", response.text)

    def info(self, message):
        print("INFO: ", message)
        self.post_log("info", message)

    def warning(self, message):
        print("WARNING: ", message)
        self.post_log("warning", message)

    def severe(self, message):
        print("SEVERE: ", message)
        self.post_log("severe", message)

    def local(self, message):
        print(message)
