# snakemake-playground

## Setup
```console
mkvirtualenv snakemake
pip install snakemake
```

## Run
### Locally
```console
snakemake -np  # dry-run
snakemake -p --cores 1
cat results/greetings.txt
```

### Container
```console
snakemake -np  # dry-run
snakemake -p --cores 1 --use-singularity
cat results/greetings.txt
```
