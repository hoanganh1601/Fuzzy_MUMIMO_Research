$ErrorActionPreference='Stop'
python code/make_synthetic.py --n 12 --prefix DEV --seed 12 --output data/smoke_dev.npz
if ($LASTEXITCODE -ne 0) { throw 'Generate development failed' }
python code/make_synthetic.py --n 8 --prefix TEST --seed 34 --output data/smoke_test.npz
if ($LASTEXITCODE -ne 0) { throw 'Generate test failed' }
python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
python code/run_experiment.py --stage all --development data/smoke_dev.npz --test data/smoke_test.npz --ks 4,6,8 --beam-counts 3 --repeats 2 --bootstrap 100 --smoke --limit 4 --min-cell-groups 1 --run-id V15_SMOKE
if ($LASTEXITCODE -ne 0) { throw 'Smoke pipeline failed' }
