# snakemake-playground

## Setup
```console
mkvirtualenv snakemake
pip install -r requirements.txt
```

## Run
### CLI
#### Locally
```console
cd helloworld
snakemake -np  # dry-run
snakemake -p --cores 1
cat results/greetings.txt
```
#### Container
```console
# singularity must be installed
cd helloworld
snakemake -np  # dry-run
snakemake -p --cores 1 --use-singularity
cat results/greetings.txt
```

### Python
#### Locally
```console
cd helloworld
python ../run.py
```
#### k8s
```console
cd helloworld
kind create cluster --config kind-config.yaml
python ../run_k8s.py
```
