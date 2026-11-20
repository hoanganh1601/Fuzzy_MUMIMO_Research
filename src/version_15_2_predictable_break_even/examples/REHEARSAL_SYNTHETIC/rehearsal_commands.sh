set -e
cd /home/claude/v152/Robust_MUMIMO_V15_2_20261119; D=/tmp/r152; O=$D/out
python3 code/make_synthetic.py --output $D/dev.npz --n 80 --prefix DEV --seed 101 --edge-fraction 0.4 --prior-use development
C="--development $D/dev.npz --dev-provenance $D/dev.npz.provenance.json --out-root $O"
python3 code/run_experiment.py --stage preflight $C --run-id V152_DM > $D/preflight_dev.json
python3 code/run_experiment.py --stage develop $C --run-id V152_DM
python3 code/run_experiment.py --stage lock $C --run-id V152_DM
echo "--- attempt 1: near-only candidate test set (must be REJECTED by covariates)"
python3 code/make_synthetic.py --output $D/near_test.npz --n 20 --prefix NEA --seed 404 --edge-fraction 0 --prior-use never_seen
python3 code/run_experiment.py --stage test-preflight $C --run-id V152_DM --test $D/near_test.npz | tail -2
echo "--- attempt 2: covariate-stratified DeepMIMO-like set"
python3 code/make_synthetic.py --output $D/dm_pool.npz --n 120 --prefix DMP --seed 202 --edge-fraction 0.3 --prior-use never_seen
python3 code/stratify_test_pool.py --pool $D/dm_pool.npz --pool-provenance $D/dm_pool.npz.provenance.json --manifest $O/V152_DM/CP00_manifest.json --lock $O/V152_DM/CP03_locked_cells.json --region-groups 12 --outside-groups 12 --output $D/dm_test.npz
python3 code/run_experiment.py --stage test-preflight $C --run-id V152_DM --test $D/dm_test.npz | tail -2
python3 code/run_experiment.py --stage test $C --run-id V152_DM --test $D/dm_test.npz --test-provenance $D/dm_test.npz.provenance.json
python3 code/run_experiment.py --stage report $C --run-id V152_DM
echo "--- 3GPP-like set with the same lock"
python3 code/make_synthetic.py --output $D/g3_pool.npz --n 120 --prefix GPP --seed 303 --edge-fraction 0.3 --prior-use never_seen
python3 code/stratify_test_pool.py --pool $D/g3_pool.npz --pool-provenance $D/g3_pool.npz.provenance.json --manifest $O/V152_DM/CP00_manifest.json --lock $O/V152_DM/CP03_locked_cells.json --region-groups 12 --outside-groups 12 --output $D/g3_test.npz
L="--lock-from $O/V152_DM/CP03_locked_cells.json"
python3 code/run_experiment.py --stage test-preflight $C --run-id V152_3GPP --test $D/g3_test.npz $L | tail -2
python3 code/run_experiment.py --stage test $C --run-id V152_3GPP --test $D/g3_test.npz --test-provenance $D/g3_test.npz.provenance.json $L
python3 code/run_experiment.py --stage report $C --run-id V152_3GPP
python3 code/run_experiment.py --stage combine --run-id V152_FINAL --combine-runs V152_DM,V152_3GPP --out-root $O
echo ALLDONE
