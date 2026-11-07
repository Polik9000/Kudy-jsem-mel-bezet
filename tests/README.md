# Testy

```
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -m "not slow"        # rychlé testy, pár minut
```

## Skutečné závody a umělé závody

Skutečné závody (cizí mapy z Livelox, vlastní běhy z hodinek, zlaté soubory) v repu nejsou, jen v soukromé kopii.
Testy je hledají ve složce `data/` a `tests/golden/`, nebo ve složce, kterou řekne proměnná `OB_TEST_DATA`
(uvnitř složky závodů `pohora/`, `petrvald/`, `azymut-e4/`, `azymut-e5/`, každá s `course.kmz`, `maponly.kmz`
a `run.fit`, a `golden/` se zlatými soubory):

```
OB_TEST_DATA=/cesta/k/datum python -m pytest          # i pomalé testy, přes hodinu
```

Bez nich:
- testy, které potřebují jen „nějaký závod s mapami a během“, použijí **umělé závody** z `tests/synthetic.py`
  (bílá mapa s fialovou tratí a běh přesně v oficiálním čase, na stejném místě a ve stejnou dobu jako skutečný závod,
  takže se běh spáruje podle dne, startu a místa);
- testy, které kontrolují skutečné výsledky (časy, trasy, zlaté soubory, čtení skutečných map z fotek a snímků),
  jsou označené `needs_data` nebo `slow` a přeskočí se.

Nový test, který nepotřebuje skutečný výsledek, napiš s `inputs("pohora")` z `tests/races.py` a nic neznač: s daty
poběží na skutečném závodě, bez nich na umělém.
