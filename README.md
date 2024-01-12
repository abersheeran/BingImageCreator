# BingImageCreator

High quality image generation by Microsoft. Reverse engineered API.

Inspired by [BingImageDownloader](https://github.com/yihong0618/BingImageCreator).

## Install

```bash
pip install git+https://github.com/abersheeran/BingImageCreator.git
```

## Getting authentication cookies

Browsers (Edge, Opera, Vivaldi, Brave, Firefox)

1. Go to https://www.bing.com/copilot
2. F12 to open XHR call some api to get the cookie
3. call some api to copy the cookieand use this
4. Copy the output. This is used in `-U`.

## Command line usage

```bash
python -m bingimagecreator -U "xxxxxx" "a big dog"
```

Images will be saved in `./output/`.
