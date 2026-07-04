"""
SmartData@Polito RSW loader (STEPS.md Step 1, D5) — real electrical dynamics
for encoder pre-training (Gate 0.5). Spot welding, not our process: warm start
only, modest expectations.

Format facts (verified against the CSVs on disk):
- voltage.csv / current.csv / force.csv: one weld per row; first 3 columns are
  metadata (Car Body, Welding Spot, Date); remaining columns are the series
  ("Voltage T-0", "Voltage T-1", ...), NaN-padded to the longest weld.
- labels.csv: same 3 metadata columns + Fault bit (79 faulty / 1,897 good).
- The metadata triple is NOT unique (52 rows are re-welds of the same spot on
  the same day), but row ORDER is identical across all four CSVs — so rows are
  aligned positionally, with the metadata verified equal row-by-row, and the
  row index disambiguates session_ids.
- Values arrive PRE-NORMALISED to [0, 1] by the dataset authors. Do NOT symlog
  or re-normalise them with ESP32 statistics — they are already unitless.

Channel mapping: Voltage → volts (ch 0), Current → amps (ch 1). Force has no
slot in the 6-channel contract; it rides in meta["force"] for an optional
pretrain-only extra stem. The other 4 channels are mask=False for every frame.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from world_model.config import CHANNEL_INDEX, N_CHANNELS, POLITO_DIR
from world_model.data.schema import SessionTensor

META_COLS = ["Car Body", "Welding Spot", "Date"]


def _read_csv(path: Path, limit: int | None) -> pd.DataFrame:
    df = pd.read_csv(path, nrows=limit)
    missing = [c for c in META_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name}: expected metadata columns {missing} not found")
    return df


def load_polito_sessions(data_dir: Path = POLITO_DIR,
                         limit: int | None = None) -> list[SessionTensor]:
    """One SessionTensor per weld. `limit` reads only the first N rows (tests/dev)."""
    data_dir = Path(data_dir)
    voltage = _read_csv(data_dir / "voltage.csv", limit)
    current = _read_csv(data_dir / "current.csv", limit)
    force = _read_csv(data_dir / "force.csv", limit)
    labels = _read_csv(data_dir / "labels.csv", limit)

    meta_ref = voltage[META_COLS]
    for name, df in (("current", current), ("force", force), ("labels", labels)):
        if not df[META_COLS].equals(meta_ref):
            raise ValueError(f"{name}.csv rows are not aligned with voltage.csv")

    v_arr = voltage.drop(columns=META_COLS).to_numpy(dtype=np.float32)
    i_arr = current.drop(columns=META_COLS).to_numpy(dtype=np.float32)
    f_arr = force.drop(columns=META_COLS).to_numpy(dtype=np.float32)
    fault_arr = labels["Fault"].to_numpy()

    v_col, i_col = CHANNEL_INDEX["volts"], CHANNEL_INDEX["amps"]
    sessions: list[SessionTensor] = []
    for row in range(len(meta_ref)):
        v, i, f = v_arr[row], i_arr[row], f_arr[row]

        # Rows are NaN-padded to the longest weld — trim to this weld's length.
        valid = ~(np.isnan(v) & np.isnan(i) & np.isnan(f))
        if not valid.any():
            continue
        T = int(np.flatnonzero(valid).max()) + 1
        v, i, f = v[:T], i[:T], f[:T]

        x = np.zeros((T, N_CHANNELS), dtype=np.float32)
        mask = np.zeros((T, N_CHANNELS), dtype=bool)
        for col, series in ((v_col, v), (i_col, i)):
            present = ~np.isnan(series)
            x[present, col] = series[present]
            mask[:, col] = present

        car_body, spot, date = meta_ref.iloc[row]
        sessions.append(SessionTensor(
            x=x,
            mask=mask,
            meta={
                "session_id": f"polito_{row:04d}_{car_body}_{spot}_{date}",
                "source": "polito",
                "n_frames": T,
                "car_body": car_body,
                "welding_spot": spot,
                "date": date,
                "fault": int(fault_arr[row]),
                "force": np.nan_to_num(f, nan=0.0),
                "force_mask": ~np.isnan(f),
            },
        ))
    return sessions
