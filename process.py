import typing as tp
import pathlib as pl
import argparse

import mutagen

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
        'music_dir',
        metavar='SOURCE DIR',
        type=pl.Path,
        help='The input directory to read FLAC files from',
    )
    parser.add_argument(
        '--album-file',
        type=pl.Path,
        help='File defining album-level fields',
    )
    parser.add_argument(
        '--track-file',
        type=pl.Path,
        help='File defining track-level fields',
    )

    args = parser.parse_args()

    return args
