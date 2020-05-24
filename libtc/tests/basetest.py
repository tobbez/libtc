import hashlib
import pytest
import shutil
import tempfile
import time

from pathlib import Path

from libtc import bdecode, bencode, TorrentData, TorrentState

@pytest.fixture
def testfiles():
    with tempfile.TemporaryDirectory() as tmp_path:
        tmp_path = Path(tmp_path)
        testfiles = Path(__file__).parent / "testfiles"
        shutil.copytree(testfiles, tmp_path / "testfiles")
        yield tmp_path / "testfiles"


def test_test_connection(client):
    assert client.test_connection()


def test_list(client):
    assert client.list() == []


def verify_torrent_state(client, states):
    hard_states = set([
        "infohash",
        "name",
    ])
    for _ in range(50):
        found_invalid_state = False
        time.sleep(0.1)

        torrent_list = client.list()
        if len(torrent_list) != len(states):
            continue

        for td, state in zip(torrent_list, states):
            assert isinstance(td, TorrentData)
            for k, v in state.items():
                td_v = getattr(td, k)
                if k in hard_states:
                    print(k, v, td_v)
                    assert v == td_v
                elif v != td_v:
                    print(f"Invalid state {k} is {td_v} should be {v}")
                    found_invalid_state = True
                    break
        if not found_invalid_state:
            return
    else:
        pytest.fail("Torrent states was never correctly added")


def test_add_torrent_multifile(client, testfiles):
    torrent = testfiles / 'Some-Release.torrent'
    torrent_data = bdecode(torrent.read_bytes())
    infohash = hashlib.sha1(bencode(torrent_data[b'info'])).hexdigest()
    client.add(torrent_data, testfiles, fast_resume=False)

    verify_torrent_state(client, [{
        "infohash": infohash,
        "name": "Some-Release",
        "state": TorrentState.ACTIVE,
        "progress": 100.0,
    }])
    client.remove(infohash)
    verify_torrent_state(client, [])
    assert (Path(testfiles) / "Some-Release").exists()


def test_add_torrent_singlefile(client, testfiles):
    torrent = testfiles / 'test_single.torrent'
    torrent_data = bdecode(torrent.read_bytes())
    infohash = hashlib.sha1(bencode(torrent_data[b'info'])).hexdigest()
    client.add(torrent_data, testfiles, fast_resume=False)

    verify_torrent_state(client, [{
        "infohash": infohash,
        "name": "file_a.txt",
        "state": TorrentState.ACTIVE,
        "progress": 100.0,
    }])

    client.remove(infohash)
    verify_torrent_state(client, [])
    assert (Path(testfiles) / "file_a.txt").exists()


def test_add_torrent_multifile_no_add_name_to_folder(client, testfiles):
    torrent = testfiles / 'Some-Release.torrent'
    torrent_data = bdecode(torrent.read_bytes())
    infohash = hashlib.sha1(bencode(torrent_data[b'info'])).hexdigest()
    client.add(torrent_data, testfiles / "Some-Release", fast_resume=False, add_name_to_folder=False)

    verify_torrent_state(client, [{
        "infohash": infohash,
        "state": TorrentState.ACTIVE,
        "progress": 100.0,
    }])
    client.remove(infohash)
    verify_torrent_state(client, [])
    assert (Path(testfiles) / "Some-Release").exists()


def test_add_torrent_singlefile_no_add_name_to_folder(client, testfiles):
    torrent = testfiles / 'test_single.torrent'
    torrent_data = bdecode(torrent.read_bytes())
    infohash = hashlib.sha1(bencode(torrent_data[b'info'])).hexdigest()
    client.add(torrent_data, testfiles, fast_resume=False, add_name_to_folder=False)

    verify_torrent_state(client, [{
        "infohash": infohash,
        "state": TorrentState.ACTIVE,
        "progress": 100.0,
    }])

    client.remove(infohash)
    verify_torrent_state(client, [])
    assert (Path(testfiles) / "file_a.txt").exists()


def test_add_torrent_singlefile_no_data(client, testfiles, tmp_path):
    torrent = testfiles / 'test_single.torrent'
    torrent_data = bdecode(torrent.read_bytes())
    infohash = hashlib.sha1(bencode(torrent_data[b'info'])).hexdigest()
    client.add(torrent_data, tmp_path, fast_resume=False, add_name_to_folder=False)

    verify_torrent_state(client, [{
        "infohash": infohash,
        "state": TorrentState.ACTIVE,
        "progress": 0.0,
    }])

    client.remove(infohash)
    verify_torrent_state(client, [])
    assert (Path(testfiles) / "file_a.txt").exists()


def test_retrieve_torrent(client, testfiles):
    torrent = testfiles / 'test_single.torrent'
    torrent_data = bdecode(torrent.read_bytes())
    infohash = hashlib.sha1(bencode(torrent_data[b'info'])).hexdigest()
    client.add(torrent_data, testfiles, fast_resume=False)

    verify_torrent_state(client, [{
        "infohash": infohash,
    }])
    retrieved_torrent_data = bdecode(client.retrieve_torrentfile(infohash))
    assert hashlib.sha1(bencode(retrieved_torrent_data[b'info'])).hexdigest() == infohash

    client.remove(infohash)
