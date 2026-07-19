"""
test_c8_dual_eval.py — the C8/T1 dual-evaluation layer in eval/compare_pretrains.py.

What these tests defend. T1 is the silent trap of the whole C8 approach: an
encoder trained on Goldak-generated welds learns to invert *Goldak*, not physics,
and a held-out SIMULATED test set cannot detect that because it was made by the
same equations. The mitigation is structural, not statistical, so the tests are
structural too — they check the shape of the discipline, not the value of any
statistic:

  1. The asymmetry is REAL and RECORDED. Arms that never saw Polito are scored on
     the entire corpus (79 positives); the Polito-pretrained incumbent stays on
     its held-out split (11-13). The eval-set name each arm used must be carried
     in the output, because "which arm got 79 positives" is the thing a reader has
     to be able to see.
  2. No simulated number is reportable alone. A simulated headline only ever comes
     back bound to its real partner and stamped with the T1 caveat; there is no
     path that hands one out bare.
  3. The detector's input is exposed. The sim-trained arms can be ranked on both
     evaluation sets, so a later ticket can compute the ranking disagreement that
     is the Goldak-inversion signal.

Reports are represented by small synthetic dicts wherever the statistic's value is
irrelevant — a test of the pairing discipline should not depend on a bootstrap. A
few driver tests build real sessions and a random encoder to check the eval-set
wiring end to end.
"""

import numpy as np
import pytest

from world_model.config import CHANNELS
from world_model.data.schema import SessionTensor
from world_model.eval.compare_pretrains import (
    DEPTH_KEY, LABEL_KEY, T1_CAVEAT, arm_corpus, format_t1_rows, is_sim_trained,
    polito_eval_split, report_headline, score_floor_t1, sim_headline,
    stamp_caveat, t1_rankings, t1_reports_for_encoder, t1_result)

SEED = 1337


# --------------------------------------------------------------------------
# fixtures: minimal reports and sessions
# --------------------------------------------------------------------------

def fake_binary_report(auc=0.7, n=1976, n_pos=79, macro_f1=0.5):
    """A stand-in for a rich_report on the fault bit — only the keys the T1
    layer reads are populated."""
    return {"target": "binary", "auc": auc, "macro_f1": macro_f1,
            "inside_null_auc": False, "n": n, "n_pos": n_pos}


def fake_depth_report(mae=0.3, n=1500):
    """A stand-in for a rich_report on continuous depth."""
    return {"target": "continuous", "mae": mae, "n": n}


def _fault_sessions(n=8, T=360, n_pos=3, depth=False, seed=0):
    """Real-shaped sessions with a fault bit (and optionally a depth series)."""
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        meta = {"session_id": f"s{i}", "source": "mock",
                LABEL_KEY: 1 if i < n_pos else 0}
        if depth:
            meta[DEPTH_KEY] = (2.0 + rng.normal(size=T)).astype(np.float32)
        out.append(SessionTensor(
            x=rng.random((T, len(CHANNELS))).astype(np.float32),
            mask=np.ones((T, len(CHANNELS)), dtype=bool),
            meta=meta))
    return out


# --------------------------------------------------------------------------
# 1. arm classification: the corpus field decides sim-trained vs incumbent
# --------------------------------------------------------------------------

def test_missing_corpus_is_the_polito_incumbent():
    """Polito adds nothing to the config (the C4-C7 hash invariant), so a missing
    corpus key must read as the incumbent, not as a sim arm."""
    assert arm_corpus({"config": {}}) == "polito"
    assert arm_corpus({}) == "polito"
    assert not is_sim_trained(arm_corpus({"config": {}}))


def test_any_corpus_name_is_sim_trained():
    for name in ("goldak-wide", "goldak-narrow", "spectrum-random"):
        assert arm_corpus({"config": {"corpus": name}}) == name
        assert is_sim_trained(name)
    assert not is_sim_trained("polito")


# --------------------------------------------------------------------------
# 2. the asymmetry: full Polito vs held-out split, with the name recorded
# --------------------------------------------------------------------------

def test_sim_arm_gets_full_corpus_incumbent_gets_heldout():
    full = list(range(1976))
    heldout = list(range(13))
    split_map = {"val": heldout}

    sim_sessions, sim_name = polito_eval_split("goldak-wide", full, split_map, "val")
    inc_sessions, inc_name = polito_eval_split("polito", full, split_map, "val")

    assert sim_sessions is full and sim_name == "full-polito"
    assert inc_sessions is heldout and inc_name == "held-out-val"
    # the asymmetry is a 152x difference in this fixture; the names make it legible
    assert len(sim_sessions) > len(inc_sessions)


def test_floor_corpus_is_scored_on_full_polito():
    """The untrained floor never saw Polito, so it takes the powered full set —
    the 79-positive floor T1 wants for its inside-null check."""
    full, split_map = list(range(1976)), {"val": list(range(13))}
    sessions, name = polito_eval_split("(random init)", full, split_map, "val")
    assert sessions is full and name == "full-polito"


# --------------------------------------------------------------------------
# 3. the caveat: fixed, stamped, and non-empty
# --------------------------------------------------------------------------

def test_stamp_caveat_marks_report_simulated():
    rep = fake_depth_report()
    stamped = stamp_caveat(rep)
    assert stamped is rep                      # in place
    assert stamped["t1_caveat"] == T1_CAVEAT
    assert stamped["domain"] == "simulated"
    assert "SIMULATED" in T1_CAVEAT and T1_CAVEAT.strip()


# --------------------------------------------------------------------------
# 4. t1_result: real is always present; sim only for a sim-trained arm, and only
#    ever bound inside the pair with the caveat stamped on it
# --------------------------------------------------------------------------

def test_incumbent_result_is_real_only():
    res = t1_result(arm="masked_recon", checkpoint="a.pt", corpus="polito",
                    real_report=fake_binary_report(n=13, n_pos=1),
                    real_eval="held-out-val")
    assert res["sim"] is None and res["paired"] is False
    assert res["sim_trained"] is False
    assert res["real"]["n_pos"] == 1 and res["real"]["eval"] == "held-out-val"


def test_sim_arm_result_pairs_and_stamps():
    sim_rep = fake_depth_report()
    res = t1_result(arm="jepa", checkpoint="g.pt", corpus="goldak-wide",
                    real_report=fake_binary_report(), real_eval="full-polito",
                    sim_report=sim_rep, sim_eval="held-out-sim")
    assert res["paired"] is True and res["sim_trained"] is True
    # the caveat is carried by the number, not a paragraph
    assert res["sim"]["report"]["t1_caveat"] == T1_CAVEAT
    assert res["sim"]["caveat"] == T1_CAVEAT
    assert res["real"]["n_pos"] == 79 and res["real"]["eval"] == "full-polito"


# --------------------------------------------------------------------------
# 5. no simulated number is reportable alone
# --------------------------------------------------------------------------

def test_sim_headline_returns_the_real_partner_too():
    res = t1_result(arm="jepa", checkpoint="g.pt", corpus="goldak-wide",
                    real_report=fake_binary_report(auc=0.72),
                    real_eval="full-polito",
                    sim_report=fake_depth_report(mae=0.3), sim_eval="held-out-sim")
    h = sim_headline(res)
    assert set(h) == {"sim", "sim_eval", "real", "real_eval", "caveat"}
    assert h["caveat"] == T1_CAVEAT
    assert h["real"] == report_headline(res["real"]["report"])   # never sim alone
    assert h["sim"] == report_headline(res["sim"]["report"])


def test_sim_headline_refuses_when_there_is_no_pair():
    res = t1_result(arm="masked_recon", checkpoint="a.pt", corpus="polito",
                    real_report=fake_binary_report(n=13, n_pos=1),
                    real_eval="held-out-val")
    with pytest.raises(ValueError):
        sim_headline(res)


# --------------------------------------------------------------------------
# 6. rankings: sim-trained arms on both sets, incumbent excluded
# --------------------------------------------------------------------------

def _sim_result(arm, real_auc, sim_mae):
    return t1_result(arm=arm, checkpoint=f"{arm}.pt", corpus="goldak-wide",
                     real_report=fake_binary_report(auc=real_auc),
                     real_eval="full-polito",
                     sim_report=fake_depth_report(mae=sim_mae),
                     sim_eval="held-out-sim")


def test_rankings_cover_both_sets_and_exclude_the_incumbent():
    incumbent = t1_result(arm="incumbent", checkpoint="p.pt", corpus="polito",
                          real_report=fake_binary_report(auc=0.9, n=13, n_pos=1),
                          real_eval="held-out-val")
    # arm A wins on real (higher AUC) but loses on sim (higher MAE) — disagreement
    a = _sim_result("A", real_auc=0.80, sim_mae=0.40)
    b = _sim_result("B", real_auc=0.60, sim_mae=0.10)
    r = t1_rankings([incumbent, a, b])

    assert set(r["arms"]) == {"A", "B"}          # incumbent not ranked
    assert [arm for arm, _ in r["real"]] == ["A", "B"]   # AUC: bigger is better
    assert [arm for arm, _ in r["sim"]] == ["B", "A"]    # -MAE: B has lower error
    assert r["disagreement_computable"] is True


def test_disagreement_not_computable_with_one_arm():
    r = t1_rankings([_sim_result("A", 0.7, 0.3)])
    assert r["disagreement_computable"] is False


# --------------------------------------------------------------------------
# 7. the printed block records the caveat and the asymmetry
# --------------------------------------------------------------------------

def test_format_states_asymmetry_and_prints_caveat_once():
    incumbent = t1_result(arm="incumbent", checkpoint="p.pt", corpus="polito",
                          real_report=fake_binary_report(auc=0.55, n=13, n_pos=1),
                          real_eval="held-out-val")
    a = _sim_result("A", 0.80, 0.40)
    b = _sim_result("B", 0.60, 0.10)
    results = [incumbent, a, b]
    text = format_t1_rows(results, t1_rankings(results))

    assert T1_CAVEAT in text                       # the caveat is printed
    assert "asymmetry" in text.lower()
    assert "79 positives" in text                  # sim arms' powered count
    assert "1 positives" in text or "1/" in text   # incumbent's held-out count
    assert "full-polito" in text and "held-out-val" in text
    assert "†" in text                             # simulated numbers are marked


def test_format_flags_pending_sim_half_when_no_sim_eval():
    """A sim-trained arm with no simulated eval set supplied has no sim number —
    the block must say the real score stands alone by design, not by pairing."""
    a = t1_result(arm="A", checkpoint="g.pt", corpus="goldak-wide",
                  real_report=fake_binary_report(), real_eval="full-polito")
    text = format_t1_rows([a], t1_rankings([a]))
    assert "PENDING" in text


# --------------------------------------------------------------------------
# 8. driver wiring: the encoder is scored on the eval set its corpus dictates
# --------------------------------------------------------------------------

def test_driver_scores_sim_arm_on_full_and_incumbent_on_heldout():
    full = _fault_sessions(n=10, n_pos=4, seed=1)
    heldout = full[:3]        # a strict, smaller "held-out" slice for the test
    from world_model.architecture.trunk import StemTrunkEncoder
    from world_model.pretraining.masked_recon import PRETRAIN_CHANNELS
    enc = StemTrunkEncoder(PRETRAIN_CHANNELS)

    sim = t1_reports_for_encoder(
        enc, arm="jepa", checkpoint="g.pt", corpus="goldak-wide",
        real_full=full, real_heldout=heldout, sim_sessions=None,
        split="val", n_boot=20, n_perm=10)
    inc = t1_reports_for_encoder(
        enc, arm="masked_recon", checkpoint="p.pt", corpus="polito",
        real_full=full, real_heldout=heldout, sim_sessions=None,
        split="val", n_boot=20, n_perm=10)

    assert sim["real"]["eval"] == "full-polito"
    assert sim["real"]["n"] == len(full)
    assert inc["real"]["eval"] == "held-out-val"
    assert inc["real"]["n"] == len(heldout)
    # neither has a sim half: no simulated eval corpus was supplied
    assert sim["sim"] is None and inc["sim"] is None


def test_driver_pairs_when_a_sim_eval_set_is_supplied():
    full = _fault_sessions(n=10, n_pos=4, seed=2)
    sim_sessions = _fault_sessions(n=8, n_pos=0, depth=True, seed=3)
    from world_model.architecture.trunk import StemTrunkEncoder
    from world_model.pretraining.masked_recon import PRETRAIN_CHANNELS
    enc = StemTrunkEncoder(PRETRAIN_CHANNELS)

    res = t1_reports_for_encoder(
        enc, arm="jepa", checkpoint="g.pt", corpus="goldak-wide",
        real_full=full, real_heldout=full[:3], sim_sessions=sim_sessions,
        split="val", n_boot=20, n_perm=10)

    assert res["paired"] is True
    assert res["sim"]["eval"] == "held-out-sim"
    assert res["sim"]["report"]["t1_caveat"] == T1_CAVEAT
    assert res["sim"]["report"]["target"] == "continuous"   # depth, not fault
    assert res["real"]["report"]["target"] == "binary"


def test_driver_incumbent_ignores_a_supplied_sim_set():
    """A sim eval set is meaningless for the incumbent — it has no simulator to be
    paired against — so it must stay real-only even if one is passed."""
    full = _fault_sessions(n=10, n_pos=4, seed=4)
    sim_sessions = _fault_sessions(n=8, n_pos=0, depth=True, seed=5)
    from world_model.architecture.trunk import StemTrunkEncoder
    from world_model.pretraining.masked_recon import PRETRAIN_CHANNELS
    enc = StemTrunkEncoder(PRETRAIN_CHANNELS)

    res = t1_reports_for_encoder(
        enc, arm="masked_recon", checkpoint="p.pt", corpus="polito",
        real_full=full, real_heldout=full[:3], sim_sessions=sim_sessions,
        split="val", n_boot=20, n_perm=10)
    assert res["sim"] is None and res["paired"] is False


def test_score_floor_is_full_polito_and_unpaired():
    full = _fault_sessions(n=10, n_pos=4, seed=6)
    res = score_floor_t1(real_full=full, real_heldout=full[:3], split="val",
                         n_boot=20, n_perm=10)
    assert res["is_floor"] is True
    assert res["real"]["eval"] == "full-polito"
    assert res["real"]["n"] == len(full)
    assert res["sim"] is None            # the floor is a real-domain baseline
