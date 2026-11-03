from collections import deque

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.quantum_info import Operator

NATIVE_GATES = ["id", "rz", "sx", "x", "cx"]
KEEP = NATIVE_GATES + ["measure", "barrier"]


# 1. Unroll: everything into 1-qubit gates + cx
def unroll(qc):
    out = qc.copy_empty_like()
    for inst in qc.data:
        op, q = inst.operation, inst.qubits
        if op.name == "ccx":
            c1, c2, t = q
            out.h(t)
            out.cx(c2, t)
            out.tdg(t)
            out.cx(c1, t)
            out.t(t)
            out.cx(c2, t)
            out.tdg(t)
            out.cx(c1, t)
            out.t(c2)
            out.t(t)
            out.h(t)
            out.cx(c1, c2)
            out.t(c1)
            out.tdg(c2)
            out.cx(c1, c2)
        elif op.name == "swap":
            a, b = q
            out.cx(a, b)
            out.cx(b, a)
            out.cx(a, b)
        elif op.num_qubits == 1 or op.name in ("cx", "measure", "barrier"):
            out.append(inst)
        else:  # any other gate: use its definition
            out.compose(unroll(op.definition), qubits=q, inplace=True)
    return out


# 2. Mapping + routing
def shortest_path(edges, start, end):
    neighbors = {}
    for a, b in edges:
        neighbors.setdefault(a, set()).add(b)
        neighbors.setdefault(b, set()).add(a)
    previous = {start: None}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        if node == end:
            break
        for n in neighbors[node]:
            if n not in previous:
                previous[n] = node
                queue.append(n)
    path = [end]
    while path[-1] != start:
        path.append(previous[path[-1]])
    return path[::-1]


def route(qc, edges, num_physical):
    edges = [tuple(e) for e in edges]
    out = QuantumCircuit(QuantumRegister(num_physical, "q"), *qc.cregs)
    layout = list(range(qc.num_qubits))  # trivial mapping: logical i -> physical i
    swaps = 0

    def add_cx(c, t):
        if (c, t) in edges:
            out.cx(c, t)
        else:  # only the opposite direction exists: flip it with Hadamards
            out.h(c)
            out.h(t)
            out.cx(t, c)
            out.h(c)
            out.h(t)

    for inst in qc.data:
        op = inst.operation
        logical = [qc.find_bit(q).index for q in inst.qubits]
        if op.name == "cx":
            path = shortest_path(edges, layout[logical[0]], layout[logical[1]])
            # move the control along the path until it is next to the target
            for p1, p2 in zip(path[:-2], path[1:-1]):
                add_cx(p1, p2)
                add_cx(p2, p1)
                add_cx(p1, p2)
                swaps += 1
                for i, p in enumerate(layout):
                    if p == p1:
                        layout[i] = p2
                    elif p == p2:
                        layout[i] = p1
            add_cx(path[-2], path[-1])
        else:
            out.append(op, [layout[i] for i in logical], inst.clbits)
    return out, swaps


# 3. Translation of the 1-qubit gates into rz, sx, x
def u_angles(m):
    theta = 2 * np.arctan2(abs(m[1, 0]), abs(m[0, 0]))
    if np.isclose(np.sin(theta / 2), 0):
        return 0.0, 0.0, np.angle(m[1, 1]) - np.angle(m[0, 0])
    if np.isclose(np.cos(theta / 2), 0):
        return theta, np.angle(m[1, 0]) - np.angle(-m[0, 1]), 0.0
    phi = np.angle(m[1, 0]) - np.angle(m[0, 0])
    lam = np.angle(-m[0, 1]) - np.angle(m[0, 0])
    return theta, phi, lam


def translate(qc):
    out = qc.copy_empty_like()
    for inst in qc.data:
        op, q = inst.operation, inst.qubits
        if op.name in KEEP:
            out.append(inst)
            continue
        theta, phi, lam = u_angles(Operator(op).data)
        if np.isclose(theta, 0):
            out.rz(phi + lam, q)
        else:  # U(theta, phi, lam) = rz(lam) sx rz(theta + pi) sx rz(phi + pi), up to a global phase
            out.rz(lam, q)
            out.sx(q)
            out.rz(theta + np.pi, q)
            out.sx(q)
            out.rz(phi + np.pi, q)
    return out


def compile_circuit(qc, coupling_map, num_physical):
    qc_r, swaps = route(unroll(qc), coupling_map, num_physical)
    return translate(qc_r), swaps
