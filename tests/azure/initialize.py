import json
import paramiko
import yaml


def get_master_connection(host_dict, master_hostname):
    """
    Returns a paramiko client object based on the master hostname and input inventory dict
    """
    master_public_addr = host_dict["hosts"][master_hostname]["ansible_host"]
    master_user = host_dict["hosts"][master_hostname]["ansible_user"]

    ssh_key_filename = host_dict["hosts"][master_hostname][
        "ansible_ssh_private_key_file"
    ]

    master = paramiko.SSHClient()
    master.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    master.connect(
        master_public_addr, username=master_user, key_filename=ssh_key_filename
    )

    return master


def get_worker_connection_via_master(
    host_dict, master_connection, master_hostname, worker_hostname
):
    """
    Returns a paramiko connection for a worker given a worker hostname and
    master client object
    """
    master_transport = master_connection.get_transport()
    master_public_addr = host_dict["hosts"][master_hostname]["ansible_host"]
    worker_addr = host_dict["hosts"][worker_hostname]["ansible_host"]

    src_addr = (master_public_addr, 22)
    dest_addr = (worker_addr, 22)
    ssh_key_filename = host_dict["hosts"][master_hostname][
        "ansible_ssh_private_key_file"
    ]
    worker_user = host_dict["hosts"][worker_hostname]["ansible_user"]

    master_channel = master_transport.open_channel("direct-tcpip", dest_addr, src_addr)

    worker = paramiko.SSHClient()
    worker.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    worker.connect(
        worker_addr,
        username=worker_user,
        key_filename=ssh_key_filename,
        sock=master_channel,
    )

    return worker


def get_cpus_dict(worker_connection):
    """
    Returns a dictionary that is the output of the `lscpu` command in a dictionary
    """
    stdin, stdout, stderr = worker_connection.exec_command("lscpu --json")

    lscpu_dict = {}

    for i in json.loads(stdout.read().decode("utf-8"))["lscpu"]:
        lscpu_dict[i["field"]] = i["data"]

    return lscpu_dict


def get_slurm_memory(worker_connection, slurm_multiplier=0.95):
    """
    Returns the slurm memory in MB after multiplying by a scaling factory to
    allow for the overhead of slurm processes
    """
    stdin, stdout, stderr = worker_connection.exec_command(
        "grep MemTotal /proc/meminfo"
    )
    lines = stdout.read()

    mem_KB = int("".join([_ for _ in lines.decode("utf-8") if _.isnumeric()]))
    mem_MB = int(mem_KB / 1000)
    slurm_memory = int(mem_MB * slurm_multiplier)

    return slurm_memory


def write_host_vars_file(
    worker_hostname, lscpu_dict, slurm_memory, relative_directory="../../host_vars/"
):
    """
    Writes out the worker configuration files into host_vars
    """
    with open(f"{relative_directory}/{worker_hostname}.yaml", "w") as f:
        f.write(
            f"""slurm_cpus: {
            int(lscpu_dict['Socket(s):']) *
            int(lscpu_dict['Core(s) per socket:']) *
            int(lscpu_dict['Thread(s) per core:'])
            }
slurm_sockets_per_board: {lscpu_dict['Socket(s):']}
slurm_cores_per_socket: {lscpu_dict['Core(s) per socket:']}
slurm_threads_per_core: {lscpu_dict['Thread(s) per core:']}
slurm_memory: {slurm_memory}
"""
        )

    print(f"Wrote configuration for {worker_hostname}")
    return None


def main():
    with open("inventory", "r") as f:
        host_dict = yaml.safe_load(f.read())["all"]

    master_hostname = list(host_dict["children"]["hpc-master"]["hosts"].keys())[0]
    worker_hosts = [host for host in host_dict["hosts"] if host != master_hostname]

    master = get_master_connection(host_dict, master_hostname)

    for worker_hostname in worker_hosts:
        worker = get_worker_connection_via_master(
            host_dict, master, master_hostname, worker_hostname
        )
        slurm_memory = get_slurm_memory(worker)
        lscpu_dict = get_cpus_dict(worker)

        write_host_vars_file(worker_hostname, lscpu_dict, slurm_memory)
        worker.close()

    master.close()


if __name__ == "__main__":
    main()
