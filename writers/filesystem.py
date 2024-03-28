import os.path

from writers import IWriter


class FsWriter(IWriter):
    # Directory where to save charts
    out_dir_path: str

    def __init__(self, out_dir_path=''):
        self.out_dir_path = os.path.abspath(out_dir_path)
        if not os.path.exists(self.out_dir_path):
            os.makedirs(self.out_dir_path)

    def write(self, base: str, quote: str, message: str, image_bytes: bytes) -> None:
        out_path = os.path.join(self.out_dir_path, f'{base.lower()}-{quote.lower()}.png')
        with open(out_path, 'wb') as fd:
            fd.write(image_bytes)
