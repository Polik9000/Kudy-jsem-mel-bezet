#!/bin/sh
# One round of the night check with every race in its own container (decision 20. 10., question 31): a heavy race
# that runs out of memory stops only itself, the others still finish. Runs the races one after another, never two
# at once. Run on the host (Git Bash) from the repository root:
#   tools/kola.sh N [race ...]        e.g. tools/kola.sh 1 msk-sprint szl-zabreh
# Without races it runs all eleven (with Bělá, data-extra/bela/). KOLO_PROTI=M compares the pictures with round M. Output: kontrola/noc4/kolo-N/<race>/ and kontrola/noc4/kolo-N.log, with the peak
# memory of every step. KOLO_ARGS="..." passes more options to run_race.py.
N="$1"; shift
[ -n "$N" ] || { echo "usage: tools/kola.sh N [race ...]"; exit 2; }
RACES="$*"
[ -n "$RACES" ] || RACES="azymut-e5 azymut-e4 pohora petrvald gps-e2 gps-e3 gps-e4 msk-sprint szl-zabreh zebricek-b bela"
mkdir -p kontrola/noc4
LOG="kontrola/noc4/kolo-$N.log"
for r in $RACES; do
  echo "== $(date +%H:%M:%S) $r" | tee -a "$LOG"
  ( MSYS_NO_PATHCONV=1 docker compose -p obdev -f docker-compose.yml -f docker-compose.dev.yml run --rm --no-deps -T \
      -e KOLO_ARGS="$KOLO_ARGS" -e KOLO_PROTI="$KOLO_PROTI" web sh /app/kontrola/noc4/run.sh "$N" "$r"
    echo "   container exit $? (137 = stopped for lack of memory)" ) 2>&1 \
    | grep -v "level=warning\|Container obdev" | tee -a "$LOG"
done
