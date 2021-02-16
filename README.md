# cuneifyplus

This is the source code for http://cuneifyplus.arch.cam.ac.uk

It is a wrapper around Steve Tinney's 'cuneify' tool, which allows for more complex conversion of transliterated
Babylonian and Akkadian into various cuneiform fonts.

## Server

Can be deployed to e.g. Heroku as wsgi app.

Example: https://cuneify.herokuapp.com/

```bash
$ heroku create cuneify
Creating app... done, ⬢ cuneify
Created http://cuneify.herokuapp.com/ | git@heroku.com:cuneify.git

$ git push heroku master
Enumerating objects: 5, done.
Counting objects: 100% (5/5), done.
Delta compression using up to 16 threads
Compressing objects: 100% (3/3), done.
Writing objects: 100% (3/3), 287 bytes | 287.00 KiB/s, done.
Total 3 (delta 2), reused 0 (delta 0), pack-reused 0
.
.
.
remote:        https://cuneify.herokuapp.com/ deployed to Heroku
```

## Command line usage

```bash
$ python3 cuneify_interface.py test_file.txt
𒇻 𒀠 𒌨 𒆠 𒆗 𒄯 𒃻 𒀀 𒉌
𒁕
𒃮
```

```bash
$ python3 cuneify_interface.py --parse-atf test_file.atf
&P232701 = RIME 3/1.01.07.031, ex. 117
#atf: lang sux
# reconstruction
@object cone
@surface a
1. {d}nin-dar-a
# 𒀭 𒊩𒌆 𒁯 𒀀
2. lugal uru16
# 𒈗 𒂗
3. lugal-a-ni
# 𒈗 𒀀 𒉌
4. gu3-de2-a
# 𒅗 𒌤 𒀀
5. ensi2
# 𒉺𒋼𒋛
6. lagasz{ki}-ke4
# 𒉢𒁓𒆷 𒆠 𒆤
7. e2 gir2-su{ki}-ka-ni
# 𒂍 𒄈 𒋢 𒆠 𒅗 𒉌
8. mu-na-du3
# 𒈬 𒈾 𒆕
...
```
