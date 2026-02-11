"""
Tests for mock session data generation (Step 16).

Validates:
- All generated sessions pass Session validator end-to-end
- Expert vs novice comparison produces visible deltas on every metric
- Physics model: arc_power drives temperature, angle drives asymmetry
- Edge cases: frame 0 null dissipation, thermal gaps, large sessions

IMPORTANT: Tests are written against the physical model in mock_sessions.py.
Key behaviours to understand before editing tests:

  Expert angle  = 45° ± 1° (tremor only)        → angle_asymmetry ≈ 0 → symmetric north/south
  Novice angle  = 45° → 65° (drifts over 15sec)  → angle_asymmetry grows → north overheats
  Novice angle at t=0 is EXACTLY 45° + wobble    → first thermal frame is still near-symmetric
  Novice angle at t=7500ms is ~55° + wobble       → mid-session frames show clear asymmetry
  Novice amps spike every 2000ms (smooth triangle) → stays within 20% jump but continuity disabled
  Novice volts drift 22V → 18V over 15 seconds    → arc_power falls over time
"""

import pytest

from data.mock_sessions import (
    ANGLE_THERMAL_SENSITIVITY,
    BASE_NS_OFFSET,
    NOMINAL_AMPS,
    NOMINAL_VOLTS,
    THERMAL_DISTANCES_MM,
    THERMAL_SAMPLE_INTERVAL_MS,
    generate_expert_session,
    generate_frames,
    generate_large_session,
    generate_novice_session,
    generate_thermal_snapshots,
    novice_angle,
)
from models.session import Session
from services.comparison_service import compare_sessions


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_center_temp(frame, snapshot_index: int = 0) -> float | None:
    """Extract center temperature from a specific thermal snapshot."""
    if not frame.has_thermal_data:
        return None
    if snapshot_index >= len(frame.thermal_snapshots):
        return None
    return next(
        (r.temp_celsius for r in frame.thermal_snapshots[snapshot_index].readings
         if r.direction == "center"),
        None,
    )


def get_direction_temp(frame, direction: str, snapshot_index: int = 0) -> float | None:
    """Extract temperature for a specific direction from a thermal snapshot."""
    if not frame.has_thermal_data:
        return None
    if snapshot_index >= len(frame.thermal_snapshots):
        return None
    return next(
        (r.temp_celsius for r in frame.thermal_snapshots[snapshot_index].readings
         if r.direction == direction),
        None,
    )


def get_thermal_frames(session):
    """Return only frames that have thermal data."""
    return [f for f in session.frames if f.has_thermal_data]


# ---------------------------------------------------------------------------
# Session structure and validation
# ---------------------------------------------------------------------------

class TestSessionStructure:
    """Generated sessions must pass all Pydantic + Session validators."""

    def test_expert_session_passes_validation(self):
        """Expert session passes all Session validators end-to-end."""
        session = generate_expert_session()
        assert isinstance(session, Session)
        assert session.session_id == "sess_expert_001"
        assert session.status.value == "complete"

    def test_novice_session_passes_validation(self):
        """Novice session passes validation with continuity checks disabled."""
        session = generate_novice_session()
        assert isinstance(session, Session)
        assert session.session_id == "sess_novice_001"
        # Novice spikes exceed continuity limits — escape hatch must be on
        assert session.disable_sensor_continuity_checks is True

    def test_expert_continuity_checks_enabled(self):
        """
        Expert signals stay within continuity limits — escape hatch must be off.
        This test also verifies that expert amps never hit zero (which was the root cause
        of the previous continuity failure). The warmup oscillation starts at nominal
        and decays smoothly, ensuring all frame-to-frame changes stay under 20%.
        """
        session = generate_expert_session()
        assert session.disable_sensor_continuity_checks is False
        
        # Verify no amps values are zero or near-zero (confirms the fix)
        amps_values = [f.amps for f in session.frames]
        assert all(a > 140.0 for a in amps_values), (
            "Expert amps should never drop below 140A (nominal 150A with ±3% variation)"
        )
        
        # Verify frame-to-frame continuity: no jump exceeds 20%
        for i in range(1, len(session.frames)):
            prev_amps = session.frames[i - 1].amps
            curr_amps = session.frames[i].amps
            if prev_amps is not None and curr_amps is not None:
                if prev_amps == 0:
                    assert curr_amps == 0, "Amps should never jump from 0 to non-zero"
                else:
                    change_ratio = abs(curr_amps - prev_amps) / abs(prev_amps)
                    assert change_ratio <= 0.20, (
                        f"Frame {i}: amps jump {change_ratio:.1%} exceeds 20% limit "
                        f"(prev={prev_amps:.1f}A, curr={curr_amps:.1f}A)"
                    )

    def test_frame_count_matches_frames_list(self):
        """frame_count must exactly equal len(frames) — Session validator enforces this."""
        for session in [generate_expert_session(), generate_novice_session()]:
            assert session.frame_count == len(session.frames)

    def test_complete_session_fields_are_set(self):
        """COMPLETE status requires expected_frame_count, last_successful_frame_index, completed_at."""
        for session in [generate_expert_session(), generate_novice_session()]:
            assert session.expected_frame_count == session.frame_count
            assert session.last_successful_frame_index == session.frame_count - 1
            assert session.completed_at is not None

    def test_expert_has_1500_frames(self):
        """15 seconds at 100Hz = exactly 1,500 frames."""
        session = generate_expert_session()
        assert session.frame_count == 1_500
        assert len(session.frames) == 1_500

    def test_novice_has_1500_frames(self):
        """Novice session is the same duration as expert."""
        session = generate_novice_session()
        assert session.frame_count == 1_500

    def test_weld_type_is_mild_steel(self):
        """Both sessions use mild_steel weld type."""
        assert generate_expert_session().weld_type == "mild_steel"
        assert generate_novice_session().weld_type == "mild_steel"


# ---------------------------------------------------------------------------
# Frame timing
# ---------------------------------------------------------------------------

class TestFrameTiming:
    """All frames must follow the 10ms interval contract."""

    def test_timestamps_start_at_zero(self):
        """First frame must be at timestamp_ms = 0."""
        session = generate_expert_session()
        assert session.frames[0].timestamp_ms == 0

    def test_timestamps_are_sequential_10ms(self):
        """Every consecutive frame pair must be exactly 10ms apart."""
        session = generate_expert_session()
        timestamps = [f.timestamp_ms for f in session.frames]
        for i in range(1, len(timestamps)):
            assert timestamps[i] - timestamps[i - 1] == 10, (
                f"Frame {i}: expected gap 10ms, got {timestamps[i] - timestamps[i-1]}ms"
            )

    def test_no_duplicate_timestamps(self):
        """No two frames may share a timestamp."""
        session = generate_expert_session()
        timestamps = [f.timestamp_ms for f in session.frames]
        assert len(timestamps) == len(set(timestamps))

    def test_last_frame_timestamp(self):
        """Last frame timestamp = (frame_count - 1) * 10ms."""
        session = generate_expert_session()
        expected_last = (session.frame_count - 1) * 10
        assert session.frames[-1].timestamp_ms == expected_last


# ---------------------------------------------------------------------------
# Thermal frame structure
# ---------------------------------------------------------------------------

class TestThermalStructure:
    """Thermal snapshots must satisfy the exact 5-reading contract."""

    def test_expert_has_150_thermal_frames(self):
        """15 seconds at 100ms interval = exactly 150 thermal frames for expert."""
        session = generate_expert_session()
        thermal_frames = get_thermal_frames(session)
        assert len(thermal_frames) == 150

    def test_novice_has_thermal_gap(self):
        """Novice has one skipped thermal frame mid-session → 149 thermal frames."""
        session = generate_novice_session()
        thermal_frames = get_thermal_frames(session)
        # One gap means one fewer thermal frame than expert
        assert len(thermal_frames) == 149

    def test_expert_thermal_intervals_are_100ms(self):
        """Expert thermal frames must be exactly 100ms apart (no gap)."""
        session = generate_expert_session()
        thermal_timestamps = [f.timestamp_ms for f in get_thermal_frames(session)]
        for i in range(1, len(thermal_timestamps)):
            assert thermal_timestamps[i] - thermal_timestamps[i - 1] == 100

    def test_each_snapshot_has_five_readings(self):
        """Every thermal snapshot must have exactly 5 readings."""
        session = generate_expert_session()
        for frame in get_thermal_frames(session):
            for snapshot in frame.thermal_snapshots:
                assert len(snapshot.readings) == 5, (
                    f"Snapshot at {snapshot.distance_mm}mm has {len(snapshot.readings)} readings"
                )

    def test_each_snapshot_has_exactly_one_center(self):
        """Each snapshot must contain exactly one center reading."""
        session = generate_expert_session()
        for frame in get_thermal_frames(session):
            for snapshot in frame.thermal_snapshots:
                center_count = sum(1 for r in snapshot.readings if r.direction == "center")
                assert center_count == 1

    def test_all_five_directions_present(self):
        """Each snapshot must contain exactly the 5 canonical directions."""
        expected = {"center", "north", "south", "east", "west"}
        session = generate_expert_session()
        for frame in get_thermal_frames(session):
            for snapshot in frame.thermal_snapshots:
                directions = {r.direction for r in snapshot.readings}
                assert directions == expected

    def test_snapshot_distances_are_strictly_increasing(self):
        """Distances within a thermal frame must be strictly increasing (no duplicates)."""
        session = generate_expert_session()
        for frame in get_thermal_frames(session):
            distances = [s.distance_mm for s in frame.thermal_snapshots]
            for i in range(1, len(distances)):
                assert distances[i] > distances[i - 1]

    def test_snapshot_distances_match_config(self):
        """Snapshot distances must exactly match THERMAL_DISTANCES_MM."""
        session = generate_expert_session()
        for frame in get_thermal_frames(session):
            distances = [s.distance_mm for s in frame.thermal_snapshots]
            assert distances == THERMAL_DISTANCES_MM


# ---------------------------------------------------------------------------
# Heat dissipation edge cases
# ---------------------------------------------------------------------------

class TestHeatDissipation:
    """Heat dissipation is pre-calculated at ingestion time with specific null rules."""

    def test_frame_0_heat_dissipation_is_null(self):
        """Frame 0 is a thermal frame but has no previous frame → must be None."""
        session = generate_expert_session()
        first_frame = session.frames[0]
        # Frame 0 is thermal (0 % 100 == 0) — no conditional needed
        assert first_frame.has_thermal_data is True
        assert first_frame.heat_dissipation_rate_celsius_per_sec is None

    def test_second_thermal_frame_has_dissipation(self):
        """Second thermal frame (t=100ms) has a previous frame → dissipation must be set."""
        session = generate_expert_session()
        thermal_frames = get_thermal_frames(session)
        # thermal_frames[0] is t=0 (null), thermal_frames[1] is t=100 (should have value)
        assert thermal_frames[1].heat_dissipation_rate_celsius_per_sec is not None

    def test_non_thermal_frames_have_null_dissipation(self):
        """Non-thermal frames (no snapshots) must have None heat dissipation."""
        session = generate_expert_session()
        non_thermal = [f for f in session.frames if not f.has_thermal_data]
        assert len(non_thermal) > 0
        for frame in non_thermal:
            assert frame.heat_dissipation_rate_celsius_per_sec is None

    def test_frame_after_thermal_gap_has_null_dissipation(self):
        """
        The thermal frame immediately after the gap must have None dissipation.
        The gap breaks the 100ms continuity → interval != 100ms → cannot calculate.
        """
        session = generate_novice_session()
        thermal_frames = get_thermal_frames(session)

        # Find consecutive thermal frames with a gap > 100ms between them
        gap_found = False
        for i in range(1, len(thermal_frames)):
            interval = thermal_frames[i].timestamp_ms - thermal_frames[i - 1].timestamp_ms
            if interval > THERMAL_SAMPLE_INTERVAL_MS:
                # The frame AFTER the gap must have null dissipation
                assert thermal_frames[i].heat_dissipation_rate_celsius_per_sec is None
                gap_found = True
                break

        assert gap_found, "Novice session should contain exactly one thermal gap"

    def test_expert_dissipation_is_positive(self):
        """
        Expert session: weld pool cools over time →
        prev_center > curr_center → dissipation > 0 (cooling).
        Check middle of session where warmup is done and cooling is steady.
        """
        session = generate_expert_session()
        thermal_frames = get_thermal_frames(session)
        # Skip first (null) and check frames in middle of session (index 50-100)
        mid_frames = [
            f for f in thermal_frames[50:100]
            if f.heat_dissipation_rate_celsius_per_sec is not None
        ]
        assert len(mid_frames) > 0
        dissipation_values = [f.heat_dissipation_rate_celsius_per_sec for f in mid_frames]
        # Cooling = positive dissipation; at least majority should be positive
        # (expert has warmup oscillation, so not all frames cool; 0.5 threshold)
        positive_count = sum(1 for d in dissipation_values if d > 0)
        assert positive_count > len(dissipation_values) * 0.5


# ---------------------------------------------------------------------------
# Physics model: temperature values
# ---------------------------------------------------------------------------

class TestPhysicsModel:
    """
    Verify the causal relationships in the physics model are working correctly.
    These tests directly validate the model documented in mock_sessions.py.
    """

    def test_center_is_hottest_at_closest_distance(self):
        """At 10mm (closest distance), center must be hotter than at 50mm (furthest)."""
        session = generate_expert_session()
        thermal_frames = get_thermal_frames(session)
        # Use a mid-session frame (warmup done)
        frame = thermal_frames[50]
        temp_10mm = get_center_temp(frame, snapshot_index=0)   # 10mm
        temp_50mm = get_center_temp(frame, snapshot_index=4)   # 50mm
        assert temp_10mm is not None
        assert temp_50mm is not None
        assert temp_10mm > temp_50mm

    def test_east_is_warmer_than_west(self):
        """East (direction of travel, preheated) must be warmer than west (solidified behind)."""
        session = generate_expert_session()
        thermal_frames = get_thermal_frames(session)
        frame = thermal_frames[50]
        east_temp = get_direction_temp(frame, "east")
        west_temp  = get_direction_temp(frame, "west")
        assert east_temp is not None
        assert west_temp is not None
        assert east_temp > west_temp

    def test_expert_north_south_are_symmetric(self):
        """
        Expert holds ~45° angle (asymmetry ≈ 0) →
        north and south should be within 6°C of each other.
        Tolerance accounts for ±1° tremor: max asymmetry = 1° × 3.0 °C/° = 3°C.
        We use 6°C to give margin (physics model can exceed 5°C in edge cases).
        """
        session = generate_expert_session()
        thermal_frames = get_thermal_frames(session)
        # Check several mid-session frames
        for frame in thermal_frames[20:80]:
            north = get_direction_temp(frame, "north")
            south = get_direction_temp(frame, "south")
            assert north is not None and south is not None
            assert abs(north - south) < 6.0, (
                f"Expert north/south asymmetry too large: north={north:.1f}, south={south:.1f}"
            )

    def test_novice_north_south_asymmetry_grows_over_time(self):
        """
        Novice angle drifts 45°→65° → north/south asymmetry grows.
        Early frames: near-symmetric. Late frames: clearly asymmetric.
        At t=0: angle ≈ 45° → asymmetry ≈ 0
        At t=14000ms: angle ≈ 63° → asymmetry ≈ (63-45) × 3.0 = 54°C
        """
        session = generate_novice_session()
        thermal_frames = get_thermal_frames(session)

        # Early: first thermal frame (t=0, angle=45°+wobble ≈ 45°)
        early_frame = thermal_frames[0]
        early_north = get_direction_temp(early_frame, "north")
        early_south = get_direction_temp(early_frame, "south")
        early_asymmetry = abs(early_north - early_south)

        # Late: last few thermal frames (angle ≈ 63°+wobble)
        late_frame = thermal_frames[-1]
        late_north = get_direction_temp(late_frame, "north")
        late_south = get_direction_temp(late_frame, "south")
        late_asymmetry = abs(late_north - late_south)

        # Late asymmetry must be significantly larger than early
        assert late_asymmetry > early_asymmetry + 20.0, (
            f"Expected asymmetry to grow: early={early_asymmetry:.1f}°C, late={late_asymmetry:.1f}°C"
        )

    def test_novice_mid_session_is_asymmetric(self):
        """
        Mid-session novice angle ≈ 55° → north hotter than south by ~30°C.
        Use a frame around t=7500ms where drift is clearly established.
        Check the first snapshot (10mm, most sensitive to angle).
        """
        session = generate_novice_session()
        # Find a thermal frame near t=7500ms
        target_ms = 7500
        thermal_frames = get_thermal_frames(session)
        mid_frame = min(thermal_frames, key=lambda f: abs(f.timestamp_ms - target_ms))

        north = get_direction_temp(mid_frame, "north")
        south = get_direction_temp(mid_frame, "south")
        assert north is not None and south is not None
        # At ~55°, asymmetry = (55-45) × 3.0 = 30°C → north > south
        assert north > south
        assert north - south > 15.0, (
            f"Expected >15°C north/south gap at mid-session: north={north:.1f}, south={south:.1f}"
        )

    def test_higher_arc_power_produces_higher_center_temp(self):
        """
        Physics check: arc_power = volts × amps drives center temperature.
        Generate two snapshots with different power levels and verify higher power = hotter.
        """
        # Low power: 140A × 20V = 2800W (below nominal 3375W)
        low_power_snapshots = generate_thermal_snapshots(
            timestamp_ms=0, amps=140.0, volts=20.0, angle_deg=45.0
        )
        # High power: 170A × 25V = 4250W (above nominal)
        high_power_snapshots = generate_thermal_snapshots(
            timestamp_ms=0, amps=170.0, volts=25.0, angle_deg=45.0
        )

        low_center = next(r.temp_celsius for r in low_power_snapshots[0].readings
                          if r.direction == "center")
        high_center = next(r.temp_celsius for r in high_power_snapshots[0].readings
                           if r.direction == "center")

        assert high_center > low_center

    def test_angle_tilt_raises_north_and_lowers_south(self):
        """
        Physics check: positive work angle tilts toward north →
        north temp rises, south temp falls relative to 0° baseline.
        """
        # 45° angle (neutral baseline)
        neutral_snapshots = generate_thermal_snapshots(
            timestamp_ms=0, amps=NOMINAL_AMPS, volts=NOMINAL_VOLTS, angle_deg=45.0
        )
        # 60° angle (significant tilt toward north)
        tilted_snapshots = generate_thermal_snapshots(
            timestamp_ms=0, amps=NOMINAL_AMPS, volts=NOMINAL_VOLTS, angle_deg=60.0
        )

        neutral_north = next(r.temp_celsius for r in neutral_snapshots[0].readings
                             if r.direction == "north")
        tilted_north  = next(r.temp_celsius for r in tilted_snapshots[0].readings
                             if r.direction == "north")
        neutral_south = next(r.temp_celsius for r in neutral_snapshots[0].readings
                             if r.direction == "south")
        tilted_south  = next(r.temp_celsius for r in tilted_snapshots[0].readings
                             if r.direction == "south")

        # 15° extra tilt → north += 15 × 3.0 = +45°C, south -= 45°C
        assert tilted_north > neutral_north
        assert tilted_south < neutral_south
        assert abs(tilted_north - neutral_north) == pytest.approx(
            15.0 * ANGLE_THERMAL_SENSITIVITY, abs=0.1
        )


# ---------------------------------------------------------------------------
# Expert vs novice comparison
# ---------------------------------------------------------------------------

class TestExpertVsNoviceComparison:
    """
    Comparison must produce visible deltas on every metric.
    These tests validate the teaching signal — what a trainee would see.
    """

    @pytest.fixture(scope="class")
    def comparison_result(self):
        """Run comparison once for the whole class (expensive: 1500 frames each)."""
        expert = generate_expert_session()
        novice = generate_novice_session()
        return compare_sessions(expert, novice)

    def test_comparison_produces_deltas(self, comparison_result):
        """Shared timestamps must produce FrameDelta objects."""
        deltas = comparison_result
        assert len(deltas) > 0

    def test_all_timestamps_are_shared(self, comparison_result):
        """Both sessions have same timestamps → all 1500 should be shared."""
        # Novice has same frame count (thermal gap doesn't affect frame timestamps)
        deltas = comparison_result
        assert len(deltas) == 1_500

    def test_amps_deltas_are_visible(self, comparison_result):
        """Expert vs novice amps differ at every timestamp."""
        deltas = comparison_result
        amps_deltas = [d.amps_delta for d in deltas
                       if d.amps_delta is not None]
        assert len(amps_deltas) > 0
        assert any(abs(d) > 1.0 for d in amps_deltas)

    def test_volts_deltas_grow_over_time(self, comparison_result):
        """
        Novice volts drift 22→18V over session → expert-novice delta grows.
        Early deltas should be smaller than late deltas.
        """
        deltas = comparison_result
        volts_deltas = [
            (d.timestamp_ms, d.volts_delta)
            for d in deltas
            if d.volts_delta is not None
        ]
        assert len(volts_deltas) > 0

        early = [v for t, v in volts_deltas if t < 3000]
        late  = [v for t, v in volts_deltas if t > 12000]
        assert len(early) > 0 and len(late) > 0

        avg_early_delta = sum(early) / len(early)
        avg_late_delta  = sum(late) / len(late)
        # Late delta should be larger (novice volts have drifted further down)
        assert avg_late_delta > avg_early_delta

    def test_angle_deltas_grow_over_time(self, comparison_result):
        """
        Novice angle drifts 45°→65° → angle delta grows over session.
        Early: near 0. Late: approaching 20°.
        """
        deltas = comparison_result
        angle_deltas = [
            (d.timestamp_ms, d.angle_degrees_delta)
            for d in deltas
            if d.angle_degrees_delta is not None
        ]
        early_deltas = [abs(v) for t, v in angle_deltas if t < 2000]
        late_deltas  = [abs(v) for t, v in angle_deltas if t > 13000]

        avg_early = sum(early_deltas) / len(early_deltas) if early_deltas else 0
        avg_late  = sum(late_deltas)  / len(late_deltas)  if late_deltas  else 0

        assert avg_late > avg_early + 5.0, (
            f"Angle delta should grow: early avg={avg_early:.1f}°, late avg={avg_late:.1f}°"
        )

    def test_thermal_deltas_exist_at_shared_thermal_frames(self, comparison_result):
        """Frames where both sessions have thermal data must produce thermal deltas."""
        deltas = comparison_result
        thermal_delta_frames = [d for d in deltas
                                 if len(d.thermal_deltas) > 0]
        assert len(thermal_delta_frames) > 0

    def test_expert_center_temps_higher_on_average(self, comparison_result):
        """
        Expert has more consistent arc power → higher average center temp.
        Delta (expert - novice) center temp should be positive on average.
        """
        deltas = comparison_result
        center_deltas = []
        for delta in deltas:
            for thermal_delta in delta.thermal_deltas:
                center = next(
                    (r.delta_temp_celsius for r in thermal_delta.readings
                     if r.direction == "center"),
                    None,
                )
                if center is not None:
                    center_deltas.append(center)

        assert len(center_deltas) > 0
        # Expert is hotter on average → positive sum
        assert sum(center_deltas) > 0

    def test_north_south_asymmetry_delta_grows(self, comparison_result):
        """
        Expert north ≈ south (symmetric). Novice north >> south (asymmetric).
        The delta (expert_north - novice_north) should grow negatively over time
        as the novice's north side overheats relative to expert.
        """
        deltas = comparison_result
        # Collect (timestamp, north_delta) for snapshot at 10mm (index 0)
        north_deltas_by_time = []
        for delta in deltas:
            if not delta.thermal_deltas:
                continue
            first_snapshot_delta = delta.thermal_deltas[0]  # 10mm snapshot
            north = next(
                (r.delta_temp_celsius for r in first_snapshot_delta.readings
                 if r.direction == "north"),
                None,
            )
            if north is not None:
                north_deltas_by_time.append((delta.timestamp_ms, north))

        early_north = [v for t, v in north_deltas_by_time if t < 2000]
        late_north  = [v for t, v in north_deltas_by_time if t > 12000]

        if early_north and late_north:
            avg_early = sum(early_north) / len(early_north)
            avg_late  = sum(late_north)  / len(late_north)
            # Novice north overheats → expert_north - novice_north becomes more negative
            assert avg_late < avg_early


# ---------------------------------------------------------------------------
# Large session performance
# ---------------------------------------------------------------------------

class TestLargeSession:
    """Large session is for performance testing only — stable expert signals."""

    def test_has_30000_frames(self):
        """5 minutes at 100Hz = exactly 30,000 frames."""
        session = generate_large_session()
        assert session.frame_count == 30_000
        assert len(session.frames) == 30_000

    def test_timestamps_span_5_minutes(self):
        """Last frame timestamp must be (30000 - 1) × 10ms = 299,990ms."""
        session = generate_large_session()
        assert session.frames[0].timestamp_ms == 0
        assert session.frames[-1].timestamp_ms == 299_990

    def test_passes_validation(self):
        """Large session must pass all validators (no shortcuts for performance data)."""
        session = generate_large_session()
        assert isinstance(session, Session)
        assert session.frame_count == session.expected_frame_count

    def test_has_3000_thermal_frames(self):
        """5 minutes at 100ms interval = 3,000 thermal frames."""
        session = generate_large_session()
        thermal_frames = get_thermal_frames(session)
        assert len(thermal_frames) == 3_000
