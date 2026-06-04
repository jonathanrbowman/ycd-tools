# ycd-tools

Tools for (trying) to unpack Mina the Hollower assets from Yacht Club Games. The game stores its data in `.pak.yc` containers. It was built with a proprietary in-house engine, so the files and formats aren't documented anywhere, at least that I know of.

I've never tried reverse engineering, so this is a learning, fun project for me, but enough people asked about it for me to open this repo. It is absolutely not for any kind of profit, and I'll only be updating it as time allows. Also, AI disclaimer, since this is outside of my normal engineering wheelhouse Claude helped hold my hand through the process.

*I am not affiliated with, or own anything in any way, with Yacht Club Games, beyond loving their games*

## Requirements

- Python 3.10+
- Pillow

## Core Concepts / Thoughts so Far
Assets seem to be stored as `.anb` animation bundles, and color sets are stored as `.pal` files. I think there is also some offset/placement data in the `.anb` files that is used for composition with larger, more complicated characters, but I haven't figured that part out.

I sampled frame data in RenderDoc while fighting the space robot guy in the mirror hub, and over 3 render ops a different quad gets drawn to compose his full sprite during one attack frame. So, those must be stored separately and used in multiple animations for reusability, which makes sense, I just don't know what exactly ties them together.

Assets that are compressed were made so with the open source wfLZ compression library, so we use that to decompress them.

## Scripts

#### `tools/extract_pak.py`
Takes any pak that you suspect contains assets, like `player.pak.yc`, and splits it into its named `.anb` and `.pal` formats, along with a `manifest.json` that lists the names, locs, and offsets.
```bash
# extract_pay.py <input_pak_file> <out_dir>
python tools/extract_pak.py "path/to/player.pak.yc" ./extracted
```

#### `tools/anb_to_sheet.py`
Takes a `.anb` file and decompresses every sprite cell and renders a png with all of them in a grid. Maybe.
```bash
# anb_to_sheet.py <input_anb_file> <out_png_file> --palette <input_pal_file>
# pass it a .pal.yc file with the --palette arg, otherwise it will use minas colors by default
python tools/anb_to_sheet.py "path/to/some.anb.yc" Mina_sheet.png --palette ./extracted/player/palettes/player/default.pal.yc
```

#### `tools/read_palette.py`
Give it a `.pal` file and it prints the palette's RGBA color table and hex codes for convenience.
```bash
# read_palette.py <input_pal_file>
python tools/read_palette.py "path/to/default.pal.yc"
```
