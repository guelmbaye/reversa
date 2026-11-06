from app.runner import run_world

def test_no_scenario_leak_into_agent_visible_data():
    for world in ["W1","W2","W3","W4","W5","W6"]:
        data = run_world(world)
        assert data["no_leak"]["pass"] is True
        assert data["no_leak"]["forbidden_markers_found"] == []
