# LAB 7 - Socket Programming (Link-State Emulator)
---
## Description & Design choices
---
- We have chosen C++ and Python to write the oracle node and virtual node respectively.
- Oracle node prints the adjacency matrix of global map.
- Every virtual node after establishing TCP connections with oracle node, sends its local data (neighbors) over the UDP socket it set up with its neighbors via link-state flooding.
- Each virtual node periodically prints global map as an adjacency matrix again, for ease of comparison between the outputs of oracle node and virtual node(s).
- Any changes to config file will trigger oracle node which sends the updated state of global map, neighbors-wise data to every node again.
- We ignored robustness, which involves sending more than one link-state messages, but as we have no packet loss, link-state messages are limited to one copy.

---
## How to run
---
- Single make file, which can be used to start both oracle and virtual node(s). 
- To start a oracle node, run the following command

```bash
make run-on
```

- *Note*: We can override ON_IP (Oracle node IP-address) and VN_IP (Virtual node IP-address), but adding the flags in below command (even custom config file can be using *CONFIG* flag). By default, they're both set to 127.0.0.1 (which is the loop back address)

```bash
make run-on ON_IP=192.168.0.104 VN_IP=192.168.0.104
```

- Similarly, to start a virtual node, run the following command

```bash
make run-vn ON_IP=192.168.0.104 VN_IP=192.168.0.104 VN_PORT=5001
```

- *Note*: We have hard-coded the ON_PORT to be 5000 here. We must not forget that we should also set ON_IP in CLI, if it needs to be overriden.
- One more thing to take care of is that default config file is hard-coded to `config.txt`, we can also override it with `CONFIG=<filename>.txt`
- We also have to make sure that, we don't create one more virtual node process with same VN_PORT, because we simply encounter an error.
---
## Clean up
---
- To remove all object files and executables, use the following command

```bash
make clean
```
---
## Manual compilation and run
---
### Oracle node
- Compilation

```bash
g++ oraclenode.cpp -o oracle_node
```

- Running

```bash
./oracle_node <ON_IP> 5000 <CONFIG>
```
- *Note*: Port is hard-coded to 5000.

### Virtual node

- Running

```bash
python3 virtual_node.py <ON_IP> <VN_IP> <VN_PORT>
```
---


