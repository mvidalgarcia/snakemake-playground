configfile: "config.yaml"

rule all:
    input:
        "results/greetings.txt"

rule helloworld:
    input:
        helloworld="code/helloworld.py",
        inputfile="data/names.txt",
    params:
        sleeptime=config["sleeptime"]
    output:
        "results/greetings.txt"
    singularity:
        "docker://python:2.7-slim"
    shell:
        "python {input.helloworld} "
        "--inputfile {input.inputfile} "
        "--outputfile {output} "
        "--sleeptime {params.sleeptime}"
