// Script para generar edificios
//Eder Jezrael Cantero Moreno

const args = process.argv.slice(2);

// Valores por defecto
const sides = args[0] !== undefined ? Number(args[0]) : 8;
const height = args[1] !== undefined ? Number(args[1]) : 6.0;
const baseRadius = args[2] !== undefined ? Number(args[2]) : 1.0;
const topRadius = args[3] !== undefined ? Number(args[3]) : 0.8;

if (sides < 3 || sides > 36) {
    console.error("El número de lados debe ser entre 3 y 36.");
    process.exit(1);
}

let vertices = [];
let normals = [];
let faces = [];

// Anillos de base y cima
for (let i = 0; i < sides; i++) {
    const angle = (2 * Math.PI * i) / sides;

    const bx = baseRadius * Math.cos(angle);
    const bz = baseRadius * Math.sin(angle);

    const tx = topRadius * Math.cos(angle);
    const tz = topRadius * Math.sin(angle);

    vertices.push([bx, 0, bz]);
    vertices.push([tx, height, tz]);

    const nx = Math.cos(angle);
    const nz = Math.sin(angle);
    normals.push([nx, 0, nz]);
    normals.push([nx, 0, nz]);
}

// Centros
const baseCenterIndex = vertices.length;
vertices.push([0, 0, 0]);
normals.push([0, -1, 0]);

const topCenterIndex = vertices.length;
vertices.push([0, height, 0]);
normals.push([0, 1, 0]);

function addFace(a, b, c) {
    faces.push(`f ${a+1}//${a+1} ${b+1}//${b+1} ${c+1}//${c+1}`);
}

// Caras laterales
for (let i = 0; i < sides; i++) {
    const next = (i + 1) % sides;

    const b0 = i * 2;
    const t0 = i * 2 + 1;
    const b1 = next * 2;
    const t1 = next * 2 + 1;

    addFace(b0, t0, b1);
    addFace(b1, t0, t1);
}

// Base
for (let i = 0; i < sides; i++) {
    const next = (i + 1) % sides;
    addFace(baseCenterIndex, i * 2, next * 2);
}

// Cima
for (let i = 0; i < sides; i++) {
    const next = (i + 1) % sides;
    addFace(topCenterIndex, next * 2 + 1, i * 2 + 1);
}

// Salida OBJ
let output = "";

for (let v of vertices) {
    output += `v ${v[0]} ${v[1]} ${v[2]}\n`;
}

for (let n of normals) {
    output += `vn ${n[0]} ${n[1]} ${n[2]}\n`;
}

for (let f of faces) {
    output += f + "\n";
}

console.log(output);
