import argparse
import asyncio
import contextlib
import json
from pathlib import Path

from . import ImageGen


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cookies", "-U", help="Auth cookies from browser", type=str)
    parser.add_argument("--cookies-file", help="File containing auth cookies", type=str)
    parser.add_argument("prompt", help="Prompt to generate images for", type=str)

    parser.add_argument(
        "--output-dir", help="Output directory", type=Path, default=Path("output")
    )

    parser.add_argument(
        "--download-count",
        help="Number of images to download, value must be less than five",
        type=int,
        default=4,
    )

    args = parser.parse_args()

    # Load auth cookie
    cookies_json = None
    if args.cookies_file is not None:
        with contextlib.suppress(Exception):
            with open(args.cookies_file, encoding="utf-8") as file:
                cookies_json = json.load(file)

    if args.download_count > 4:
        raise Exception("The number of downloads must be less than five")

    args.output_dir.mkdir(exist_ok=True, parents=True)

    # Create image generator
    async with ImageGen(args.cookies, cookies_json) as image_gen:
        links = await image_gen.get_images(args.prompt)
        for i, link in enumerate(links[: args.download_count]):
            print(f"Downloading image {link}...{i}")
            filepath = args.output_dir / f"{i}.jpeg"
            filepath.write_bytes(await image_gen.download_image(link))


if __name__ == "__main__":
    asyncio.run(main())
