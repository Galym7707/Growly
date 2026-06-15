from app.config import Settings


def test_publish_destination_flags_default_true_channel_false_group() -> None:
    s = Settings(_env_file=None)
    assert s.publish_to_channel is True
    assert s.publish_to_group is False
