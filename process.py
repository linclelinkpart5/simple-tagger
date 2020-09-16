import typing as tp
import pathlib as pl

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
