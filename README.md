# CBZ Comic Downloader

Moved to <https://gitlab.com/taikedz/cbz-downloader>

Download comics from the web and save them as CBZ files for reading. Ideal for loading up a tablet and offline reading.

CBZ Downloader is a lightly extensible comic downloader, that can assemble comic pages by chapter into CBZ files for use in comic readers, available for [desktop](https://lifehacker.com/5858906/five-best-desktop-comic-book-readers) and [mobile](https://thedroidguy.com/2018/01/5-best-comic-book-reader-apps-android-device-2018-1069923).

## Features

* Extensible base to operate on many web comic hosting sites
	* base object's API provides a number of convenience functions for parsing HTML source
* Creates standardized ZIP/deflate-based CBZ files for individual chapters
* Suport for installation and use on [Termux](https://termux.com/) GNU/Linux environment for Android

### Supported sites

This is the list of sites cbzdl knows how to download from. The author's main interest is manga hence the heavy manga-oriented support, but any comic hosting site should be supportable.

* MangaFox (fanfox.net)
* MangaHere (mangahere.cc)
* MangaLivre (mangalivre.blog)

## Installing

You will need [Python 3](https://www.python.org/) and `pip3`

### Linux, Mac

On *nix systems, open a Terminal session and run

	git clone https://github.com/taikedz/cbz-downloader
	cd cbz-downloader

	./install.sh all
	. ~/.bashrc

and the `cbzdl` command will be available to you.

You can update the engine or modules individually by running one of

	./install engine
	./install modules

### Windows

These are instructions for setting up a CygWin *nix compatbility layer and installing `cbzdl` to that. Using native Windows python and creating a globally usable command is beyond this author's knowledge.

Install [cygwin](https://www.cygwin.com/) with the following packages

* python3
* pip/setup tools
* git

Then open a cygwin session and run

	git clone https://github.com/taikedz/cbz-downloader
	cd cbz-downloader
	./install.sh

You should now be able to use `cbzdl` from the cygwin command line, whilst in any folder.

## Using

### Commands

	cbzdl URL                      Download a comic (all chapters)
	cbzdl COMICDIR                 Resume a comic download from the last successful chapter
	cbzdl URL -f                   Show which chapters failed on the last run, then exit
	cbzdl URL -l                   Show the last successfully downloaded chapter, then exit
	cbzdl URL -c                   Count chapters available on the site, then exit (no download)
	cbzdl modules                  List installed site modules, then exit
	cbzdl catalog:MODULE           Scan a site's listing pages for titles (+ chapter, where the site shows it), no download

`URL` can be literally a URL, or the folder of a comic previously downloaded (to resume it). `MODULE` is a module name as printed by `cbzdl modules` (e.g. `MangaLivre`).

### Flags

Flag | Applies to | Meaning
---|---|---
`-s, --start START` | download | Minimum chapter to start from (int or float)
`-e, --end END` | download | Maximum chapter to include (int or float, up to 9000)
`-d, --delay DELAY` | download, catalog | Seconds to wait between requests (default: module's recommended delay, usually 1-2s)
`-w, --workers WORKERS` | download | Pages to download concurrently per chapter (default: 5)
`-o, --output-dir DIR` | download, catalog | Where to create the comic folder / save `catalog_MODULE.json` (default: current directory)
`-v, --verbose` | all | Verbose/debug output
`--max-pages N` | catalog | Stop scanning after N listing pages
`--full` | catalog | Print the entire catalog instead of just new/updated titles

### Examples

Download a comic:

	cbzdl https://mangalivre.blog/manga/the-beginning-after-the-end/

Download only chapters 1 to 2:

	cbzdl https://mangalivre.blog/manga/the-beginning-after-the-end/ -s 1 -e 2

Download into a specific folder:

	cbzdl https://mangalivre.blog/manga/the-beginning-after-the-end/ -o ~/Comics

If you have already downloaded the comic and don't specify a start chapter, `cbzdl` resumes from the last chapter successfully downloaded - resume also skips pages already on disk within an interrupted chapter, and retries a page that fails a couple of times before giving up.

Scan a site's catalog for new/updated titles (saves to `catalog_MODULE.json`, only prints what changed since the last scan):

	cbzdl catalog:MangaLivre

Scan just the first 2 listing pages, and print the whole catalog (not just the diff):

	cbzdl catalog:MangaFox --max-pages 2 --full

## Extending

See [module writing notes](writing_modules.md)
