# Slurm

For detailed slurm information please refer to the
[documentation](https://slurm.schedmd.com/overview.html).

## Checking Health of Slurm Cluster

[sinfo](https://slurm.schedmd.com/sinfo.html) is your bread and butter
and should be used to quickly check the health of the cluster.

```shell
sinfo
```

```
PARTITION AVAIL  TIMELIMIT  NODES  STATE NODELIST
general*     up   infinite      1    mix hpc02-test
general*     up   infinite      2   idle hpc03-test,hpc04-test
```

## Configuring/Adding Node Information

For each node create a `host_vars/<node-name>.yaml` and omit any
fields if you want to use the default value. Suppose the following
configuration for `host_vars/hpc02-test.yaml`.

```yaml
slurm_memory: 7976         # RealMemory (default 1024)
slurm_cpus: 4              # CPUs (default 1)
slurm_boards: 1            # Boards (default 1)
slurm_sockets_per_board: 4 # SocketsPerBoard (default 1)
slurm_cores_per_socket: 1  # CoresPerSocket (default 1)
slurm_threads_per_core: 1  # ThreadsPerCore (default 1)
```

Would result in the following slurm node configuration

```init
# Nodes
NodeName=hpc02-test RealMemory=7976 CPUs=4 Boards=1 SocketsPerBoard=4 CoresPerSocket=1 ThreadsPerCore=1 State=UNKNOWN
```

You can get the detailed node specs via slurmd and can be used to
easily set the node configuration. The more accurately that you set
the node information for slurm the more accurately users can target
their programs on the hardware.

```shell
slurmd -C
```

```
NodeName=hpc02-test CPUs=4 Boards=1 SocketsPerBoard=4 CoresPerSocket=1 ThreadsPerCore=1 RealMemory=7976
UpTime=0-01:46:52
```

If you have set an incorrect configuration, the nodes may enter a
DRAIN state with low cores*sockets*threads and memory error. You will
then need to modify the node state to IDLE once it is properly
configured.

## Modifying Node State

There are several common cases where one would need to manually change
the node state. All slurm managment is done via the `sacct` and
`scontrol` command. In this case we need to use `scontrol` command.

```shell
scontrol update nodename=<node-name> state=IDLE
```

This is useful if you want to resume a node for operation.

## Node States

The full list of [node
states](https://slurm.schedmd.com/sinfo.html#lbAG). Here we outline
some of the common ones.

 - ALLOCATED :: node is completely consumed
 - MIXED :: node is partially consumed
 - IDLE :: node is idle and has no running jobs
 - DRAIN :: node is unable to schedule new jobs but running jobs will finish

## Adding Slurm Partitions

Partitions in slurm can easily be created via ansible groups. Any
group start starts with `partition-`. For example

```ini
[hpc-master]
hpc01-test

[hpc-worker]
hpc02-test
hpc03-test
hpc04-test

[partition-example]
hpc02-test
hpc04-test
```

Will create the following slurm partitions

```ini
# Partitions
PartitionName=general Nodes=hpc02-test,hpc03-test,hpc04-test Default=YES MaxTime=INFINITE State=UP
PartitionName=example Nodes=hpc02-test,hpc04-test Default=NO MaxTime=INFINITE State=UP
```