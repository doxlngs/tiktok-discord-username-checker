# sniper

Interactive + CLI username availability checker for Discord and TikTok, with built-in free-proxy scraping/validation and multithreaded checking.

## Features

- Check usernames on **Discord** or **TikTok**
- Generate candidates (3/4-letter or alphanumeric) or load a wordlist
- Scrape and validate free proxies from public sources
- Multithreaded, configurable threads/delay
- Interactive menu or scriptable CLI
- Hits saved to file automatically

## Requirements

Python 3.8+

## Install

```bash
git clone https://github.com/doxlngs/tiktok-discord-username-checker.git
cd sniper
pip install -r requirements.txt
```

### Linux

```bash
git clone https://github.com/doxlngs/tiktok-discord-username-checker.git
cd sniper
python3 -m venv venv && source venv/bin/activate
pip3 install -r requirements.txt
chmod +x sniper.py   # optional, run as ./sniper.py
```

Debian/Ubuntu missing venv: `sudo apt install -y python3-venv python3-pip`

## Usage

### Interactive

```bash
python3 sniper.py
```

### CLI

```bash
python3 sniper.py -g 4L -P discord
python3 sniper.py -w names.txt -P tiktok -p proxies.txt
python3 sniper.py -g 3L 3C -P discord -s -v
python3 sniper.py -w names.txt -t 10 -d 1.5 -o hits.txt
```

| Flag | Description |
|---|---|
| `-P` | `discord` or `tiktok` (default `discord`) |
| `-g` | Generate usernames: `3L` `3C` `4L` `4C` |
| `-w` | Wordlist file path |
| `-p` | Proxy list file path |
| `-s` | Scrape fresh proxies first |
| `-v` | Validate scraped proxies (with `-s`) |
| `-o` | Output file (default `hits.txt`) |
| `-t` | Thread count (default `5`) |
| `-d` | Delay in seconds (default `1.2`) |

`-g` and `-w` are mutually exclusive.

## Notes

- Free proxy lists vary in reliability — use `-v` to filter.
- Subject to each platform's Terms of Service.

## License

MIT — see [LICENSE](LICENSE).

**doxlngs** · [github.com/doxlngs](https://github.com/doxlngs) · `@doxings`
