set -e
cd /home/claude/v16/Robust_MUMIMO_V16_20261120; D=/tmp/nat; O=/tmp/r152/out; V=/tmp/v16o
python3 code/lock_transfer.py --stage transfer --manifest $O/V152_DM/CP00_manifest.json --lock $O/V152_DM/CP03_locked_cells.json --development /tmp/r152/dev.npz --dev-provenance /tmp/r152/dev.npz.provenance.json --new-run-id NAT_T --out-root $O | tail -2
M=$O/NAT_T/CP00_manifest.json; LK=$O/NAT_T/CP03T_transferred_lock.json
python3 code/natural_prevalence.py --stage protocol --run-id NP_DM --out-root $V --manifest $M --lock $LK --pool $D/nat_pool.npz --n-groups 30 | tail -1
python3 code/natural_prevalence.py --stage sample --run-id NP_DM --out-root $V --pool $D/nat_pool.npz --pool-provenance $D/nat_pool.npz.provenance.json --output $D/nat_sample.npz
C="--development /tmp/r152/dev.npz --dev-provenance /tmp/r152/dev.npz.provenance.json --out-root $O"
python3 code/run_experiment.py --stage test-preflight $C --run-id NAT_T --test $D/nat_sample.npz --lock-from $LK | tail -1
python3 code/run_experiment.py --stage test $C --run-id NAT_T --test $D/nat_sample.npz --test-provenance $D/nat_sample.npz.provenance.json --lock-from $LK --allow-small-region
python3 code/compiled_benchmark.py --data $D/nat_sample.npz --manifest $M --lock $LK --run-id C16_NAT --out-root $V --python-run $O/NAT_T --repeats 3 | tail -3
python3 code/natural_prevalence.py --stage analyze --run-id NP_DM --out-root $V --v152-run $O/NAT_T --compiled-run $V/C16_NAT
echo ALLDONE
