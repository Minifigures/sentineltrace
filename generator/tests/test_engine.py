import json

from synthfix.engine import generate_stream
from synthfix.labels import write_labels_jsonl


def test_stream_contains_benign_flow_and_all_five_archetypes():
    events, labels = generate_stream(seed=1, n_normal=100, abuse_count=5)
    assert len(labels) == 5
    assert {l.abuse_type for l in labels} == {
        "SPOOFING", "WASH_TRADE", "FRONT_RUNNING", "MOMENTUM_IGNITION", "MARKING_THE_CLOSE",
    }
    benign = [e for e in events if e.scenario_type is None]
    assert len(benign) == 100  # one benign order per normal step
    assert len(events) > 100  # plus the injected scenario events


def test_stream_is_time_ordered():
    events, _ = generate_stream(seed=2, n_normal=50, abuse_count=3)
    ts = [e.transact_time for e in events]
    assert ts == sorted(ts)


def test_stream_is_deterministic():
    a, la = generate_stream(seed=3, n_normal=40, abuse_count=2)
    b, lb = generate_stream(seed=3, n_normal=40, abuse_count=2)
    assert [e.to_dict() for e in a] == [e.to_dict() for e in b]
    assert [l.injected_event_ids for l in la] == [l.injected_event_ids for l in lb]


def test_injected_label_ids_reference_real_events():
    events, labels = generate_stream(seed=4, n_normal=80, abuse_count=5)
    ids = {e.cl_ord_id for e in events}
    for label in labels:
        assert set(label.injected_event_ids) <= ids


def test_label_sidecar_roundtrip(tmp_path):
    _, labels = generate_stream(seed=5, n_normal=30, abuse_count=3)
    out = tmp_path / "labels.jsonl"
    n = write_labels_jsonl(labels, out)
    lines = out.read_text().strip().splitlines()
    assert n == len(labels) == len(lines)
    rec = json.loads(lines[0])
    assert {"scenario_id", "abuse_type", "trader_id", "injected_event_ids"} <= rec.keys()
