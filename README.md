# snakemake-playground

## Setup
```console
mkvirtualenv snakemake
pip install snakemake
```

## Run
### Locally
```console
snakemake -n  # dry-run
snakemake -p --cores 1
```

### Container
```console
snakemake -p --cores 1 --use-singularity
```
