import os
import shlex
from collections import namedtuple

from snakemake import snakemake
from snakemake.common import get_uuid
from snakemake.exceptions import WorkflowError
from snakemake.executors import KubernetesExecutor
from snakemake.logging import logger

KUBERNETES_NAMESPACE = "default"

KubernetesJob = namedtuple(
    "KubernetesJob", "job jobid callback error_callback kubejob jobscript"
)


class MyKubernetesExecutor(KubernetesExecutor):
    def run(self, job, callback=None, submit_callback=None, error_callback=None):
        import kubernetes.client

        super()._run(job)
        exec_job = self.format_job(
            self.exec_job,
            job,
            _quote_all=True,
            use_threads="--force-use-threads" if not job.is_group() else "",
        )
        # Kubernetes silently does not submit a job if the name is too long
        # therefore, we ensure that it is not longer than snakejob+uuid.
        jobid = "snakejob-{}".format(
            get_uuid("{}-{}-{}".format(self.run_namespace, job.jobid, job.attempt))
        )

        body = kubernetes.client.V1Pod()
        body.metadata = kubernetes.client.V1ObjectMeta(labels={"app": "snakemake"})

        body.metadata.name = jobid

        # container
        container = kubernetes.client.V1Container(name=jobid)
        container.image = self.container_image
        container.command = shlex.split("/bin/sh")
        container.args = ["-c", exec_job]
        container.working_dir = "/workdir"
        container.volume_mounts = [
            kubernetes.client.V1VolumeMount(name="workdir", mount_path="/workdir"),
            kubernetes.client.V1VolumeMount(name="source", mount_path="/source"),
            # XXX: New volume mount
            kubernetes.client.V1VolumeMount(
                name="results", mount_path="/workdir/results"
            ),
        ]

        body.spec = kubernetes.client.V1PodSpec(containers=[container])
        # fail on first error
        body.spec.restart_policy = "Never"

        # source files as a secret volume
        # we copy these files to the workdir before executing Snakemake
        too_large = [
            path
            for path in self.secret_files.values()
            if os.path.getsize(path) > 1000000
        ]
        if too_large:
            raise WorkflowError(
                "The following source files exceed the maximum "
                "file size (1MB) that can be passed from host to "
                "kubernetes. These are likely not source code "
                "files. Consider adding them to your "
                "remote storage instead or (if software) use "
                "Conda packages or container images:\n{}".format("\n".join(too_large))
            )
        secret_volume = kubernetes.client.V1Volume(name="source")
        secret_volume.secret = kubernetes.client.V1SecretVolumeSource()
        secret_volume.secret.secret_name = self.run_namespace
        secret_volume.secret.items = [
            kubernetes.client.V1KeyToPath(key=key, path=path)
            for key, path in self.secret_files.items()
        ]
        # workdir as an emptyDir volume of undefined size
        workdir_volume = kubernetes.client.V1Volume(name="workdir")
        workdir_volume.empty_dir = kubernetes.client.V1EmptyDirVolumeSource()
        # body.spec.volumes = [secret_volume, workdir_volume]

        # XXX: NEW results volume
        results_volume = kubernetes.client.V1Volume(name="results")
        results_volume.host_path = kubernetes.client.V1HostPathVolumeSource(
            path="/results"
        )

        body.spec.volumes = [secret_volume, workdir_volume, results_volume]

        # env vars
        container.env = []
        for key, e in self.secret_envvars.items():
            envvar = kubernetes.client.V1EnvVar(name=e)
            envvar.value_from = kubernetes.client.V1EnvVarSource()
            envvar.value_from.secret_key_ref = kubernetes.client.V1SecretKeySelector(
                key=key, name=self.run_namespace
            )
            container.env.append(envvar)

        # request resources
        container.resources = kubernetes.client.V1ResourceRequirements()
        container.resources.requests = {}
        container.resources.requests["cpu"] = job.resources["_cores"]
        if "mem_mb" in job.resources.keys():
            container.resources.requests["memory"] = "{}M".format(
                job.resources["mem_mb"]
            )

        # capabilities
        if job.needs_singularity and self.workflow.use_singularity:
            # TODO this should work, but it doesn't currently because of
            # missing loop devices
            # singularity inside docker requires SYS_ADMIN capabilities
            # see https://groups.google.com/a/lbl.gov/forum/#!topic/singularity/e9mlDuzKowc
            # container.capabilities = kubernetes.client.V1Capabilities()
            # container.capabilities.add = ["SYS_ADMIN",
            #                               "DAC_OVERRIDE",
            #                               "SETUID",
            #                               "SETGID",
            #                               "SYS_CHROOT"]

            # Running in priviledged mode always works
            container.security_context = kubernetes.client.V1SecurityContext(
                privileged=True
            )

        pod = self._kubernetes_retry(
            lambda: self.kubeapi.create_namespaced_pod(self.namespace, body)
        )

        logger.info(
            "Get status with:\n"
            "kubectl describe pod {jobid}\n"
            "kubectl logs {jobid}".format(jobid=jobid)
        )
        self.active_jobs.append(
            KubernetesJob(job, jobid, callback, error_callback, pod, None)
        )


# Monkeypatch KubernetesExecutor class in `scheduler` module
from snakemake import scheduler

scheduler.KubernetesExecutor = MyKubernetesExecutor

# uses snakemake/snakemake:v6.4.1 (with conda) by default.
snakemake("./Snakefile", printshellcmds=True, kubernetes=KUBERNETES_NAMESPACE)
