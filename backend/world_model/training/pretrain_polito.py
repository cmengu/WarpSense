"""
Deprecated location shim — Step 6 Polito pretraining moved to
world_model/pretraining/masked_recon.py when pretraining objectives were
consolidated under pretraining/ (one shared encoder, one checkpoint contract).

Kept so the documented CLI keeps working:
  python -m world_model.training.pretrain_polito --tiny
New code should import from world_model.pretraining.masked_recon directly.
"""

from world_model.pretraining.masked_recon import *  # noqa: F401,F403
from world_model.pretraining.masked_recon import (  # noqa: F401
    _mask_timesteps,
    _two_channel_batch,
    main,
)

if __name__ == "__main__":
    main()
