import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT / "data"

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)


AUTHORITY_REGISTRY_PATH = (
    DATA_DIR
    / "authority_registry.json"
)


GOVBANK_PATH = (
    DATA_DIR
    / "govbank.json"
)


DEFAULT_PUBLIC_SEED_PATH = (
    ROOT.parent
    / "mali-ya-rona"
    / "data"
    / "demo.json"
)


PUBLIC_SEED_PATH = Path(
    os.getenv(
        "MALI_SEED_PATH",
        str(DEFAULT_PUBLIC_SEED_PATH)
    )
).expanduser().resolve()


APP_ENV = os.getenv(
    "MYR_ENV",
    "development"
).lower()


DEV_MODE = (
    os.getenv(
        "MYR_DEV_MODE",
        "0"
    )
    == "1"
)


# A developer bypass must never silently work
# outside a development environment.
if DEV_MODE and APP_ENV != "development":

    raise RuntimeError(
        "MYR_DEV_MODE may only be used "
        "when MYR_ENV=development."
    )
