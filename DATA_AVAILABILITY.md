# Data availability

The 15 channel datasets required to reproduce the reported experiments are
listed in `DATASETS.csv` with their target filenames, scientific roles,
sections and SHA-256 digests. The NPZ files are intentionally excluded from
Git by `.gitignore`.

The local working copy may place the files under `data/` using exactly the
names in `DATASETS.csv`. Verify a received copy from the repository root with:

```bash
while IFS=, read -r file expected rest; do
  [ "$file" = file ] && continue
  actual=$(sha256sum "$file" | awk '{print $1}')
  [ "$actual" = "$expected" ] || echo "MISMATCH $file"
done < DATASETS.csv
```

For archival publication, upload the 15 NPZ files together with
`DATASETS.csv` and their provenance JSON files to Zenodo, then record the DOI
in this document and in the manuscript. Until a DOI is assigned, the data are
available from the authors upon reasonable request. Do not commit the NPZ
files to this repository.

The Sionna UMi datasets can also be regenerated with
`reproducibility/sionna/gen_sionna_umi.py` and the frozen protocols under
`reproducibility/sionna/protocols/`. The V12 runtime validation entry point is
`src/version_12_robust_sinr_final_validation/code/final_runtime_validation.py`.
