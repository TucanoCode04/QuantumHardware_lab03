from qiskit import QuantumCircuit

qc = QuantumCircuit.from_qasm_file("../qasm_files/adder_small.qasm")
print(qc)

from qiskit_ibm_runtime.fake_provider import FakeGuadalupeV2

backend = FakeGuadalupeV2()
coupling_map = [list(edge) for edge in backend.coupling_map.get_edges()]
native_gates = backend.operation_names
print("Coupling map:", coupling_map)
print("Native gates (basis gates):", native_gates)

from qiskit.providers.basic_provider import BasicProvider
from itertools import product

qc_m = qc.copy()
qc_m.measure_all()

simulator = BasicProvider().get_backend("basic_simulator")
result = simulator.run(qc_m).result()
counts = result.get_counts()
print("Counts:", counts)
num_qubits = qc.num_qubits
# Generate all possible binary outcomes for num_qubits
all_states = [''.join(state) for state in product('01', repeat=num_qubits)]

# Calculate probabilities, including zero counts
total_shots = sum(counts.values())
probabilities = [counts.get(state, 0) / total_shots for state in all_states]
print(probabilities)

from compiler_basic import compile_circuit

qc_c, swaps = compile_circuit(qc_m, coupling_map, backend.num_qubits)
ops = dict(qc_c.count_ops())
measures = ops.pop("measure", 0)
barriers = ops.pop("barrier", 0)
print("Depth:", qc_c.depth())
print("Gate count:", sum(ops.values()), ops, "measure:", measures, "barrier:", barriers)
print("Swaps added:", swaps)

print("Only native gates:", all(gate in native_gates for gate in ops))
cx_pairs = [[qc_c.find_bit(q).index for q in inst.qubits] for inst in qc_c.data if inst.operation.name == "cx"]
print("All cx on connected qubits:", all(pair in coupling_map for pair in cx_pairs))

import numpy as np


def Fidelity(psi, phi):
    F = np.abs(np.vdot(psi, phi))**2
    return float(np.clip(F, 0.0, 1.0))


counts = simulator.run(qc_c).result().get_counts()
total_shots = sum(counts.values())
probabilities_c = [counts.get(state, 0) / total_shots for state in all_states]
print("Fidelity (ideal simulation):", Fidelity(probabilities, probabilities_c))

counts = backend.run(qc_c).result().get_counts()
total_shots = sum(counts.values())
probabilities_c = [counts.get(state, 0) / total_shots for state in all_states]
print("Fidelity (FakeGuadalupeV2):", Fidelity(probabilities, probabilities_c))
