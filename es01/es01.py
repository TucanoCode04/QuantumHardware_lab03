import numpy as np
import pandas as pd
from itertools import product
from qiskit import QuantumCircuit, transpile
from qiskit.providers.basic_provider import BasicProvider
from qiskit.quantum_info import Statevector
from qiskit_ibm_runtime.fake_provider import FakeGuadalupeV2


def Fidelity(psi, phi):
    F = np.abs(np.vdot(psi, phi))**2
    return float(np.clip(F, 0.0, 1.0))


results = []

qc = QuantumCircuit.from_qasm_file("../qasm_files/adder_small.qasm")
print(qc)

sv = Statevector(qc)
print(sv.probabilities_dict())

qc_m = qc.copy()
qc_m.measure_all()

backend = BasicProvider().get_backend("basic_simulator")
result = backend.run(qc_m).result()
counts = result.get_counts()
print("Counts:", counts)
num_qubits = qc.num_qubits
# Generate all possible binary outcomes for num_qubits
all_states = [''.join(state) for state in product('01', repeat=num_qubits)]

# Calculate probabilities, including zero counts
total_shots = sum(counts.values())
probabilities = [counts.get(state, 0) / total_shots for state in all_states]
print(probabilities)

print(qc.depth())
print(qc.count_ops())
results.append({"target": "original", "optimization_level": None, "depth": qc.depth(),
                "gate_count": qc.size(), "count_ops": dict(qc.count_ops()), "fidelity": None})

for optimization_level in [0, 1, 2, 3]:
    qc_t = transpile(qc, basis_gates=['id', 'ry', 'rx', 'rz', 'cx'], optimization_level=optimization_level)
    F = Fidelity(sv.data, Statevector(qc_t).data)
    print(optimization_level, qc_t.depth(), qc_t.count_ops(), F)
    results.append({"target": "basis_gates", "optimization_level": optimization_level, "depth": qc_t.depth(),
                    "gate_count": qc_t.size(), "count_ops": dict(qc_t.count_ops()), "fidelity": F})

backend = FakeGuadalupeV2()
for optimization_level in [0, 1, 2, 3]:
    qc_t = transpile(qc_m, backend=backend, optimization_level=optimization_level)
    counts = backend.run(qc_t).result().get_counts()
    total_shots = sum(counts.values())
    probabilities_t = [counts.get(state, 0) / total_shots for state in all_states]
    F = Fidelity(probabilities, probabilities_t)
    ops = dict(qc_t.count_ops())
    measures = ops.pop("measure", 0)
    barriers = ops.pop("barrier", 0)
    print(optimization_level, qc_t.depth(), ops, "measure:", measures, "barrier:", barriers, F)
    results.append({"target": "FakeGuadalupeV2", "optimization_level": optimization_level, "depth": qc_t.depth(),
                    "gate_count": sum(ops.values()), "count_ops": ops, "measure": measures, "barrier": barriers,
                    "fidelity": F})

df = pd.DataFrame(results)
df.to_csv("es01.csv", index=False)
print(df)
