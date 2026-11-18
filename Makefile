CXX      := g++
CXXFLAGS := -std=c++17 -O2

ON_SRC   := oraclenode.cpp
ON_BIN   := oracle_node
VN_SRC   := virtual_node.py

# Run-time parameters; override with e.g.  make run-vn VN_PORT=6002
ON_IP    ?= 127.0.0.1
ON_PORT  ?= 5000
CONFIG   ?= config.txt
VN_IP    ?= 127.0.0.1
VN_PORT  ?= 6001

.PHONY: all clean run-on run-vn

all: $(ON_BIN)

$(ON_BIN): $(ON_SRC)
	$(CXX) $(CXXFLAGS) -o $@ $<

run-on: $(ON_BIN)
	./$(ON_BIN) $(ON_IP) $(ON_PORT) $(CONFIG)

run-vn:
	python3 $(VN_SRC) $(ON_IP) $(VN_IP) $(VN_PORT)

clean:
	rm -f $(ON_BIN)
