from src.utils.config import load_config, MinimapConfig


def test_minimap_config_defaults():
    cfg = MinimapConfig()
    assert cfg.region == [0, 0, 0, 0]
    assert cfg.white_threshold == 240
    assert cfg.black_threshold == 15
    assert cfg.arrival_radius == 5


def test_load_config_has_minimap(tmp_path):
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text("""
game:
  window_title: test
minimap:
  region: [1230, 30, 160, 180]
  white_threshold: 235
  arrival_radius: 8
patrol:
  waypoints: [[50, 60], [100, 80]]
""")
    cfg = load_config(str(yaml_file))
    assert cfg.minimap.region == [1230, 30, 160, 180]
    assert cfg.minimap.white_threshold == 235
    assert cfg.minimap.arrival_radius == 8
    assert cfg.patrol.waypoints == [[50, 60], [100, 80]]
