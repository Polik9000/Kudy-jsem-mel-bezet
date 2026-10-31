# Race inputs

Empty in the public copy: maps and runs are not shared (see the main README). To run the scripts or the slow
tests on your own races, put each race in its own folder here:

| file | what |
|---|---|
| `course.kmz` | Livelox export with the course printed |
| `maponly.kmz` | Livelox export of the map only |
| `run.fit` | your Garmin activity of the race |

```
python3 run_race.py data/RACE/course.kmz data/RACE/maponly.kmz data/RACE/run.fit races/RACE/out --title "Race name"
```

The tests (`tests/races.py`) expect the four reference races of the author (`azymut-e5`, `azymut-e4`, `pohora`,
`petrvald`) and their outputs in `tests/golden`; without them those tests are skipped.
