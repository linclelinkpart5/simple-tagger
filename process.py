import typing as tp
import pathlib as pl
import argparse

import mutagen.flac
import hjson

Block = tp.Mapping[str, tp.Sequence[str]]

class Entry(tp.NamedTuple):
    path: pl.Path
    track_num: int
    tags: tp.Mapping[str, tp.List[str]]

class Processor:
    @staticmethod
    def process(
        dir: pl.Path,
        album_fields: Block,
        track_fields: tp.Iterable[Block],
    ):
        pass


def get_arg_parser():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument(
        'source_dir',
        type=pl.Path,
        help='Input dir path to read FLAC files from',
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


if __name__ == '__main__':
    parser = get_arg_parser()
    args = parser.parse_args()

    source_dir = args.source_dir
    album_file = args.album_file
    track_file = args.track_file

    with album_file.open() as fp:
        album_fields = hjson.load(fp)

    with track_file.open() as fp:
        track_field_blocks = hjson.load(fp)

    src_paths = list(source_dir.glob('*.flac'))

    # Check that there are equal numbers of track blocks and FLAC files.
    assert(len(track_field_blocks) == len(src_paths))

    entries = []
    expected_track_nums = set(i + 1 for i in range(len(track_field_blocks)))

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

    def sort_key(entry):
        return (entry.track_num, entry.path.name)

    entries.sort(key=sort_key)

    for entry in entries:
        print(entry)
