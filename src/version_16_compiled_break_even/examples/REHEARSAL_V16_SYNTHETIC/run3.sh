set -e
cd /home/claude/v16/Robust_MUMIMO_V16_20261120; O=/tmp/r152/out; V=/tmp/v16o
M=$O/NAT_T/CP00_manifest.json; LK=$O/NAT_T/CP03T_transferred_lock.json
rm -rf $V/C16_DM
python3 code/compiled_benchmark.py --data /tmp/r152/dev.npz --manifest $M --lock $LK --run-id C16_DEV --out-root $V --repeats 3 | tail -2
python3 code/compiled_benchmark.py --data /tmp/r152/dm_test.npz --manifest $M --lock $LK --run-id C16_DM --out-root $V --python-run $O/V152_DM --repeats 3 | tail -16
python3 code/compiled_benchmark.py --data /tmp/r152/g3_test.npz --manifest $M --lock $LK --run-id C16_3GPP --out-root $V --python-run $O/V152_3GPP --repeats 3 | tail -2
python3 code/breakeven_model.py --manifest $M --run-id M16_C --out-root $V --fit /tmp/r152/dev.npz $V/C16_DEV --validate DM /tmp/r152/dm_test.npz $V/C16_DM --validate 3GPP /tmp/r152/g3_test.npz $V/C16_3GPP | tail -8
echo ALLDONE
