# Examples

Examples for running HEP-Benchmark-Suite in different configurations. Details are in the main [README.md](../README.md#examples)

## Considerations on HPC/Cloud

### Avoiding redundant image pulls

Setting `$SINGULARITY_CACHEDIR` before submitting a slurm job with more than one node allows a single image cache to be used across all jobs, instead of every node pulling an individual copy of the workload images.

### No external connectivity on worker nodes

In the case where worker nodes do not have WAN (external) connectivity, [bmksend](../bin/bmksend) utility is provided for batch uploading of bulk reports from a node with external connectivity (login node, for example).

`bmksend -c {your config.yml with AMQ credentials} {/path/to/dir &| path/to/result.json}`

It is **HIGHLY RECOMMENDED** to use the `--dryrun` flag before sending to get an idea of what will be sent, as directories are recursively searched.

This utility looks for reports using the default name `bmkrun_report.json`. If users have renamed reports they wish to publish to their broker, you can do this via the `--force` flag, which tells the program to search using `*.json` instead.

#### Example bmksend

```sh
$ bmksend --dryrun --force -c ~/myHPCconfig.yml ~/path/to/bmkrun_report.json /cephfs/oldruns /lustre/user/interesting_crash.json
DRYRUN: Found 3 matching reports:
/home/dsouthwi/path/to/bmkrun_report.json
/cephfs/oldruns/b/c/bmkrun_report.json
/cephfs/oldruns/a/bmkrun_report.json
DRYRUN: Found 1 additional JSON:
/lustre/user/interesting_crash.json
DRYRUN: Would have transmitted 4 JSON
DRYRUN: No files have been sent.
```
