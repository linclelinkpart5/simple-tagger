import typing as tp
import pathlib as pl
import argparse

import mutagen
import hjson

Block = tp.Mapping[str, tp.Sequence[str]]

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

    flac_files = sorted(source_dir.glob('*.flac'))

    # Check that there are equal numbers of track blocks and FLAC files.
    assert(len(track_field_blocks) == len(flac_files))

    for flac_file in flac_files:
        print(flac_file)
