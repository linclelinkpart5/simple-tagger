import typing as tp
import pathlib as pl
import argparse

import mutagen.flac
import hjson

Block = tp.Mapping[str, tp.Sequence[str]]

class InvalidBlock(Exception):
    pass

class Entry(tp.NamedTuple):
    path: pl.Path
    track_num: int
    tags: tp.Mapping[str, tp.List[str]]


def get_arg_parser():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument(
        'source_dir',
        type=pl.Path,
        help='Input dir path to read FLAC files from',
    )
    parser.add_argument(
        'output_dir',
        type=pl.Path,
        help='Output dir path to write modified FLAC files to',
    )
    parser.add_argument(
        'album_file',
        type=pl.Path,
        help='Path to HJSON file defining album-level fields',
    )
    parser.add_argument(
        'track_file',
        type=pl.Path,
        help='Path to HJSON file defining track-level fields',
    )

    return parser


def collect_entries(source_dir: pl.Path) -> tp.List[Entry]:
    src_paths = list(source_dir.glob('*.flac'))

    entries = []
    expected_track_nums = set(i + 1 for i in range(len(src_paths)))

    for src_path in src_paths:
        with src_path.open(mode='rb') as fp:
            flac_data = mutagen.flac.FLAC(fp)
            tags = flac_data.tags

            assert 'TRACKNUMBER' in tags
            tn = tags['TRACKNUMBER']
            assert isinstance(tn, list)
            assert len(tn) == 1
            track_num = int(tn[0])

            expected_track_nums.remove(track_num)

            entries.append(Entry(path=src_path, tags=tags, track_num=track_num))

    assert len(expected_track_nums) == 0

    entries.sort(key=lambda e: e.track_num)

    return entries


def normalize_block_candidate(block_candidate) -> Block:
    # Ensure that we have a mapping.
    if not isinstance(block_candidate, dict):
        raise InvalidBlock('block is not a dict')

    for k in block_candidate.keys():
        # The mapping should have string keys only.
        if not isinstance(k, str):
            raise InvalidBlock('block does not have strings as keys')

        # Each value in the mapping should be either a string or a list of strings.
        v = block_candidate[k]
        if isinstance(v, str):
            # Convert into a singleton list of strings.
            block_candidate[k] = [v]
        elif isinstance(v, list):
            # Ensure each element in the list is a string.
            for sv in v:
                if not isinstance(sv, str):
                    raise InvalidBlock('block contains a non-string list as a value')
        else:
            raise InvalidBlock('block does not have strings or lists of strings as values')

    return block_candidate


def load_album_block(path: pl.Path) -> Block:
    with path.open() as fp:
        album_block_candidate = hjson.load(fp)

    album_block = normalize_block_candidate(album_block_candidate)

    return album_block


def load_track_blocks(path: pl.Path) -> tp.List[Block]:
    with path.open() as fp:
        track_block_candidates = hjson.load(fp)

    assert isinstance(track_block_candidates, list)

    for i in range(len(track_block_candidates)):
        track_block_candidates[i] = normalize_block_candidate(track_block_candidates[i])

    track_blocks = track_block_candidates

    return track_blocks


if __name__ == '__main__':
    parser = get_arg_parser()
    args = parser.parse_args()

    source_dir = args.source_dir
    album_file = args.album_file
    track_file = args.track_file

    entries = collect_entries(source_dir)

    # Output intermediate data and pause for user input.
    # We care about artist and title info.
    intermediates = []
    for entry in entries:
        sub_tags = {k: entry.tags[k] for k in ('ARTIST', 'TITLE')}
        intermediates.append(sub_tags)

    print(hjson.dumps(intermediates))

    input("Press Enter to continue...")

    album_block = load_album_block(album_file)
    track_blocks = load_track_blocks(track_file)

    # Check that there are equal numbers of track blocks and FLAC files.
    assert(len(track_blocks) == len(entries))
