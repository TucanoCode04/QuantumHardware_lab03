// quantum ripple-carry adder from Cuccaro et al, quant-ph/0410184

// Cin = q[0]
// A Input = q[1], q[2], q[3], q[4]
// B Input = q[5], q[6], q[7], q[8]
// Cout = q[9]

OPENQASM 2.0;
include "qelib1.inc";

qreg q[10];

// set input states
x q[1]; // a = 0001
x q[5]; // b = 1111
x q[6];
x q[7];
x q[8];

// add a to b, storing result in b

// majority q[0],q[5],q[1];

cx q[1],q[5];
cx q[1],q[0];
ccx q[0],q[5],q[1];

// majority q[1],q[6],q[2];

cx q[2],q[6];
cx q[2],q[1];
ccx q[1],q[6],q[2];

// majority q[2],q[7],q[3];

cx q[3],q[7];
cx q[3],q[2];
ccx q[2],q[7],q[3];

// majority q[3],q[8],q[4];

cx q[4],q[8];
cx q[4],q[3];
ccx q[3],q[8],q[4];

cx q[4],q[9];

// unmaj q[3],q[8],q[4];

ccx q[3],q[8],q[4];
cx q[4],q[3];
cx q[3],q[8];

// unmaj q[2],q[7],q[3];

ccx q[2],q[7],q[3];
cx q[3],q[2];
cx q[2],q[7];

// unmaj q[1],q[6],q[2];

ccx q[1],q[6],q[2];
cx q[2],q[1];
cx q[1],q[6];

// unmaj q[0],q[5],q[1];

ccx q[0],q[5],q[1];
cx q[1],q[0];
cx q[0],q[5];


