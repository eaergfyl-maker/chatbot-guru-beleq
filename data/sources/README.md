# Source documents

One notes file per source: the full reference on the first line, then what it supports, in our own words. `data/knowledge/topics.json` cites these sources by the key in each file name.

| File | Type | Used for |
|---|---|---|
| `saputra2019.md` | journal article | instruments, name, nyongkolan, uncertain history |
| `fazalani2020.md` | journal article | spelling, ceremonies, costume, war origins |
| `markarma2022.md` | journal article (abstract only) | group playing and cohesion |
| `keen2015.md` | ethnomusicology blog | instruments, nyongkolan, group size |
| `maharani2024.md` | news article | name, war origins, drum parts, group size |
| `indonesiatravel.md` | government tourism site | occasions, costume, how the drums are carried |

To add a source: create a notes file here, add it to `references` in `topics.json`, cite its key on the facts it supports, then run `python -m src.knowledge`. Summarise and cite; do not copy long passages.
