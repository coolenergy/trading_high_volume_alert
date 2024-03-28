import os.path

import requests

from writers import IWriter


class SlackWriter(IWriter):
    # We need a token with file:write priviledge
    slack_token: str
    channel_id: str

    def __init__(self, slack_token: str, channel_id: str):
        self.slack_token = slack_token
        self.channel_id = channel_id

    def write(self, base: str, quote: str, message: str, image_bytes: bytes) -> None:
        response: requests.Response

        response = requests.post('https://slack.com/api/files.upload', data={
            'token': self.slack_token,
            'title': 'Image',
            'filename': 'image.png',
            'filetype': 'auto',
            'channels': self.channel_id,
            'initial_comment': message,
        }, files=[('file', image_bytes)])

        if response.status_code != 200:
            raise ValueError(f'An error occurred sending {base}/{quote} {response.json()}')
