"""Write validated records to Parquet."""

from pathlib import Path
from typing import Any

import pandas as pd


def write_parquet(records: list[dict[str, Any]], output_path: Path) -> int:
    if not records:
        return 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(records)
    df.to_parquet(output_path, index=False)
    return len(records)
