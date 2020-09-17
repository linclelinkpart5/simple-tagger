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


def collect_entries(source_dir: pl.Path):
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

    # Now actually load the album and track data.
    with album_file.open() as fp:
        album_fields = hjson.load(fp)

    with track_file.open() as fp:
        track_field_blocks = hjson.load(fp)

    # Check that there are equal numbers of track blocks and FLAC files.
    assert(len(track_field_blocks) == len(entries))
