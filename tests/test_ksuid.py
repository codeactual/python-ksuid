import json
import os
import typing as t
from datetime import datetime, timedelta, timezone

import pytest

from baseconv import base62

from ksuid.ksuid import (
    ByteArrayLengthException,
    EPOCH_STAMP,
    Ksuid,
    KsuidMs,
)

EMPTY_KSUID_PAYLOAD = bytes([0] * Ksuid.PAYLOAD_LENGTH_IN_BYTES)

TESTS_DIR = os.path.dirname(os.path.realpath(__file__))

TEST_ITEMS_COUNT = 10


def test_create():
    # Arrange
    ksuid = Ksuid()

    # Assert
    assert ksuid.timestamp is not None
    assert len(str(ksuid)) == Ksuid.BASE62_LENGTH


def test_create_from_timestamp():
    # Arrange
    now = datetime.now(tz=timezone.utc)
    ksuid = Ksuid(datetime=now)
    now_seconds = now.replace(microsecond=0)

    # Assert
    assert ksuid.datetime == now_seconds
    assert ksuid.timestamp == now_seconds.timestamp()


def test_create_from_payload():
    # Arrange
    payload = os.urandom(Ksuid.PAYLOAD_LENGTH_IN_BYTES)
    ksuid = Ksuid(payload=payload)

    # Assert
    assert ksuid.payload == payload


def test_create_from_payload_and_timestamp():
    # Arrange
    payload = os.urandom(Ksuid.PAYLOAD_LENGTH_IN_BYTES)
    now = datetime.now(tz=timezone.utc)
    now_seconds = now.replace(microsecond=0)
    ksuid = Ksuid(payload=payload, datetime=now)

    # Assert
    assert ksuid.payload == payload
    assert ksuid.datetime == now_seconds
    assert ksuid.timestamp == now_seconds.timestamp()


def test_create_with_naive_datetime():
    # Arrange
    naive_time = datetime.now()

    # Assert
    ksuid = Ksuid(datetime=naive_time)
    assert ksuid.datetime.tzinfo == timezone.utc


def test_to_from_base62():
    # Arrange
    ksuid = Ksuid()
    base62 = str(ksuid)

    # Act
    ksuid_from_base62 = ksuid.from_base62(base62)

    # Assert
    assert ksuid == ksuid_from_base62


def test_to_from_bytes():
    # Arrange
    ksuid = Ksuid()

    # Act
    ksuid_from_bytes = ksuid.from_bytes(bytes(ksuid))

    # Assert
    assert ksuid == ksuid_from_bytes

    with pytest.raises(ByteArrayLengthException):
        ksuid.from_bytes(int.to_bytes(10, 2, "big"))


def test_from_base62_empty():
    # Assert
    with pytest.raises(ValueError):
        Ksuid.from_base62("")


def test_from_base62_invalid():
    # Assert
    with pytest.raises(ValueError):
        Ksuid.from_base62("invalid*base62")


def test_from_base62_out_of_range():
    # Arrange
    oversized = int.to_bytes(1 << (Ksuid.BYTES_LENGTH * 8), Ksuid.BYTES_LENGTH + 1, "big")
    oversized_base62 = base62.encode(int.from_bytes(oversized, "big"))

    # Assert
    with pytest.raises(ValueError):
        Ksuid.from_base62(oversized_base62)


def test_get_payload():
    # Arrange
    ksuid = Ksuid()

    # Assert
    assert ksuid.payload == bytes(ksuid)[Ksuid.TIMESTAMP_LENGTH_IN_BYTES :]


def test_compare():
    # Arrange
    now = datetime.now()
    ksuid = Ksuid(now)
    ksuid_older = Ksuid(now - timedelta(hours=1))

    # Assert
    assert ksuid > ksuid_older
    assert not ksuid_older > ksuid
    assert ksuid != ksuid_older
    assert not ksuid == ksuid_older


def test_compare_to_other_type():
    # Arrange
    ksuid = Ksuid()

    # Assert
    assert (ksuid == "not-a-ksuid") is False


def test_compare_lt_other_type():
    # Arrange
    ksuid = Ksuid()

    # Assert
    with pytest.raises(TypeError):
        _ = ksuid < "not-a-ksuid"


def test_uniqueness():
    # Arrange
    ksuids_set = set()
    for _ in range(TEST_ITEMS_COUNT):
        ksuids_set.add(Ksuid())

    # Assert
    assert len(ksuids_set) == TEST_ITEMS_COUNT


def test_payload_uniqueness():
    # Arrange
    now = datetime.now()
    timestamp = now.replace(microsecond=0).timestamp()
    ksuids_set: t.Set[Ksuid] = set()
    for i in range(TEST_ITEMS_COUNT):
        ksuids_set.add(Ksuid(datetime=now))

    # Assert
    assert len(ksuids_set) == TEST_ITEMS_COUNT
    for ksuid in ksuids_set:
        assert ksuid.timestamp == timestamp


def test_timestamp_uniqueness():
    # Arrange
    time = datetime.now()
    ksuids_set: t.Set[Ksuid] = set()
    for i in range(TEST_ITEMS_COUNT):
        ksuids_set.add(Ksuid(datetime=time, payload=EMPTY_KSUID_PAYLOAD))
        time += timedelta(seconds=1)

    # Assert
    assert len(ksuids_set) == TEST_ITEMS_COUNT


def test_ms_mode_datetime():
    # Arrange
    time = datetime.now()
    for i in range(TEST_ITEMS_COUNT):
        ksuid = KsuidMs(datetime=time)
        # Test the values are correct rounded to 4 ms accuracy

        assert round(time.timestamp() * 256) == round(ksuid.datetime.timestamp() * 256)
        time += timedelta(milliseconds=5)


def test_ms_from_bytes_round_trip():
    # Arrange
    ksuid = KsuidMs()

    # Act
    ksuid_from_bytes = KsuidMs.from_bytes(bytes(ksuid))

    # Assert
    assert ksuid == ksuid_from_bytes


def test_ms_payload_length_validation():
    # Arrange
    payload = os.urandom(KsuidMs.PAYLOAD_LENGTH_IN_BYTES + 1)

    # Assert
    with pytest.raises(ByteArrayLengthException):
        KsuidMs(payload=payload)


def test_timestamp_out_of_range():
    # Arrange
    too_early = datetime.fromtimestamp(EPOCH_STAMP - 1, tz=timezone.utc)
    too_late = datetime.fromtimestamp(EPOCH_STAMP + (1 << 32), tz=timezone.utc)

    # Assert
    with pytest.raises(ValueError):
        Ksuid(datetime=too_early)
    with pytest.raises(ValueError):
        Ksuid(datetime=too_late)


def test_ms_timestamp_out_of_range():
    # Arrange
    too_early = datetime.fromtimestamp(EPOCH_STAMP - 1, tz=timezone.utc)
    too_late = datetime.fromtimestamp(EPOCH_STAMP + (1 << 40) / KsuidMs.TIMESTAMP_MULTIPLIER, tz=timezone.utc)

    # Assert
    with pytest.raises(ValueError):
        KsuidMs(datetime=too_early)
    with pytest.raises(ValueError):
        KsuidMs(datetime=too_late)


def test_golib_interop():
    tf_path = os.path.join(TESTS_DIR, "test_kuids.txt")

    with open(tf_path, "r") as test_kuids:
        lines = test_kuids.readlines()
        for ksuid_json in lines:
            test_data = json.loads(ksuid_json)
            ksuid = Ksuid(datetime.fromtimestamp(test_data["timestamp"]), payload=bytes.fromhex(test_data["payload"]))
            assert test_data["ksuid"] == str(ksuid)
            ksuid = Ksuid.from_base62(test_data["ksuid"])
            assert test_data["ksuid"] == str(ksuid)


def test_golib_interop_ms_mode():
    tf_path = os.path.join(TESTS_DIR, "test_kuids.txt")

    with open(tf_path, "r") as test_kuids:
        lines = test_kuids.readlines()
        for ksuid_json in lines:
            test_data = json.loads(ksuid_json)
            ksuid = Ksuid(datetime.fromtimestamp(test_data["timestamp"]), payload=bytes.fromhex(test_data["payload"]))
            ksuid_ms = KsuidMs(ksuid.datetime, ksuid.payload[: KsuidMs.PAYLOAD_LENGTH_IN_BYTES])
            assert ksuid_ms.datetime == ksuid.datetime
            ksuid_ms_from = KsuidMs(ksuid_ms.datetime, ksuid_ms.payload)
            assert ksuid_ms.payload == ksuid_ms_from.payload
            assert ksuid_ms.timestamp == ksuid_ms_from.timestamp

            ksuid_ms = KsuidMs.from_base62(test_data["ksuid"])
            assert timedelta(seconds=-1) < ksuid.datetime - ksuid_ms.datetime < timedelta(seconds=1)
            assert test_data["ksuid"] == str(ksuid_ms)
