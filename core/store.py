import json
import os
import tempfile
from pathlib import Path
from threading import Lock


class JsonStore:

    def __init__(
        self,
        path,
        default_data
    ):

        self.path = Path(path)

        self.default_data = default_data

        self.lock = Lock()

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        if not self.path.exists():

            self.write(
                default_data
            )


    def read(self):

        with self.lock:

            with self.path.open(
                "r",
                encoding="utf-8"
            ) as file:

                return json.load(file)


    def write(
        self,
        data
    ):

        with self.lock:

            directory = (
                self.path.parent
            )

            fd, temporary_path = (
                tempfile.mkstemp(
                    prefix="myr_",
                    suffix=".json",
                    dir=directory
                )
            )

            try:

                with os.fdopen(
                    fd,
                    "w",
                    encoding="utf-8"
                ) as file:

                    json.dump(
                        data,
                        file,
                        indent=2,
                        ensure_ascii=False
                    )

                    file.flush()

                    os.fsync(
                        file.fileno()
                    )

                os.replace(
                    temporary_path,
                    self.path
                )

            finally:

                if os.path.exists(
                    temporary_path
                ):

                    os.unlink(
                        temporary_path
                    )