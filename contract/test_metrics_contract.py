def test_metrics_contract(client):
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    data = response.json()
    
    # Validation
    expected_keys = [
        "search_latency_p50_ms",
        "search_latency_p95_ms",
        "cache_hit_rate",
        "index_size",
        "mappings_count",
        "state_hash",
        "last_refreshed",
        "index_rebuild_total",
        "last_rebuild_timestamp",
        "snapshot_load_failures",
        "using_ann",
        "queue_depth",
        "queue_fill_ratio",
        "total_events",
        "dropped_events",
        "drop_rate",
        "worker_flush_latency_ms"
    ]
    
    for key in expected_keys:
        assert key in data, f"Missing key {key} in /metrics response"
        
    assert isinstance(data["search_latency_p50_ms"], float)
    assert isinstance(data["cache_hit_rate"], float)
    assert isinstance(data["index_size"], int)
