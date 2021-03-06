import typing as tp
import pathlib as pl
import argparse
import tempfile
import shutil
import subprocess

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
        'album_file',
        type=pl.Path,
        help='Path to HJSON file defining album-level fields',
    )
    parser.add_argument(
        'track_file',
        type=pl.Path,
        help='Path to HJSON file defining track-level fields',
    )
    parser.add_argument(
        '--no-intermediate',
        action='store_true',
        help='Do not show intermediate information, i.e. artist/title from source files',
    )
    parser.add_argument(
        '--output_dir',
        type=pl.Path,
        default=None,
        help='Output dir path to write modified FLAC files to '
            '(defaults to the input directory)',
    )

    return parser


def collect_entries(source_dir: pl.Path) -> tp.List[Entry]:
    src_paths = list(source_dir.glob('*.flac'))

    entries = []
    expected_track_nums = set(i + 1 for i in range(len(src_paths)))

    for src_path in src_paths:
        print(f'Reading existing tags from {src_path.name}')
        flac_data = mutagen.flac.FLAC(src_path)

        tags = flac_data.tags

        assert 'tracknumber' in tags
        tn = tags['tracknumber']
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

    track_blocks = []
    for track_block_candidate in track_block_candidates:
        track_blocks.append(normalize_block_candidate(track_block_candidate))

    return track_blocks


def process_entries(
    entries: tp.Sequence[Entry],
    album_block: Block,
    track_blocks: tp.Sequence[Block],
    output_dir: pl.Path,
):
    # Check that there are equal numbers of track blocks and entries.
    assert(len(track_blocks) == len(entries))

    num_total_tracks = len(track_blocks)
    num_digits = len(str(num_total_tracks))

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Cast as a `Path`.
        tmp_dir = pl.Path(tmp_dir)

        for entry, track_block in zip(entries, track_blocks):
            flac_data = mutagen.flac.FLAC(entry.path)

            # Remove all existing tags.
            flac_data.tags.clear()

            # Remove any pictures.
            flac_data.clear_pictures()

            # Add in album block fields.
            flac_data.tags.update(album_block)

            # Add in the track block fields for this entry.
            flac_data.tags.update(track_block)

            # Add track index/count info to tags.
            flac_data.tags['tracknumber'] = [str(entry.track_num)]
            flac_data.tags['totaltracks'] = [str(num_total_tracks)]

            print(flac_data.pprint())

            flac_data.save()

            # Create temporary interim file path.
            tno = str(entry.track_num).zfill(num_digits)

            assert 'artist' in flac_data.tags
            ars = ', '.join(flac_data.tags['artist'])

            assert 'title' in flac_data.tags
            assert len(flac_data.tags['title']) == 1
            trk = flac_data.tags['title'][0]

            ext = entry.path.suffix

            interim_file_name = f'{tno}. {ars} - {trk}{ext}'
            interim_path = tmp_dir / interim_file_name

            # Move file to temporary interim location.
            shutil.move(str(entry.path), str(interim_path))

        # Run `bs1770gain`.
        # This should also copy the files to their final destination.
        args = ('bs1770gain', '--replaygain', '-irt', '--output', output_dir, tmp_dir)
        subprocess.run(args, check=True)


if __name__ == '__main__':
    parser = get_arg_parser()
    args = parser.parse_args()

    source_dir = args.source_dir
    album_file = args.album_file
    track_file = args.track_file
    no_show_inter = args.no_intermediate

    output_dir = args.output_dir
    if not output_dir:
        output_dir = source_dir

    entries = collect_entries(source_dir)

    if not no_show_inter:
        # Output intermediate data and pause for user input.
        # We care about artist and title info.
        intermediates = []
        uninteresting_tags = (
            'tracknumber',
            'comment',
            'totaltracks',
            'year',
            'date',
            'albumartist',
            'album',
        )

        for entry in entries:
            sub_tags = dict()

            for k in entry.tags.keys():
                if k.lower() not in uninteresting_tags:
                    sub_val = entry.tags[k]
                    if isinstance(sub_val, list) and len(sub_val) == 1:
                        sub_tags[k] = sub_val[0]
                    else:
                        sub_tags[k] = sub_val

            intermediates.append(sub_tags)

        print(hjson.dumps(intermediates))

        input("Press Enter to continue...")

    album_block = load_album_block(album_file)
    track_blocks = load_track_blocks(track_file)

    process_entries(
        entries=entries,
        album_block=album_block,
        track_blocks=track_blocks,
        output_dir=output_dir,
    )
