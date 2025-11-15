'use strict';

import * as twgl from 'twgl-base.js';
import GUI from 'lil-gui';


const vsGLSL = `#version 300 es
in vec2 a_position;
in vec4 a_color;

uniform vec2 u_resolution;
uniform mat3 u_matrix;

out vec4 v_color;

void main() {
    vec3 worldPosition = u_matrix * vec3(a_position, 1.0);
    vec2 zeroToOne = worldPosition.xy / u_resolution;
    vec2 clipSpace = zeroToOne * 2.0 - 1.0;
    gl_Position = vec4(clipSpace * vec2(1.0, -1.0), 0.0, 1.0);
    v_color = a_color;
}
`;

const fsGLSL = `#version 300 es
precision highp float;

in vec4 v_color;

out vec4 outColor;

void main() {
    outColor = v_color;
}
`;

function main() {
  const canvas = document.querySelector('#canvas');
  const gl = canvas.getContext('webgl2');

  if (!gl) {
    throw new Error('WebGL2 no está disponible en este navegador.');
  }

  const programInfo = twgl.createProgramInfo(gl, [vsGLSL, fsGLSL]);

  const faceGeometry = createFaceGeometry();
  const pivotGeometry = createPivotGeometry();

  const faceBufferInfo = twgl.createBufferInfoFromArrays(gl, faceGeometry);
  const pivotBufferInfo = twgl.createBufferInfoFromArrays(gl, pivotGeometry);

  const faceVao = twgl.createVAOFromBufferInfo(gl, programInfo, faceBufferInfo);
  const pivotVao = twgl.createVAOFromBufferInfo(gl, programInfo, pivotBufferInfo);

  const state = {
    pivot: { x: 220, y: 260 },
    face: {
      tx: 420,
      ty: 260,
      rotation: 0,
      scaleX: 1,
      scaleY: 1,
    },
  };

  const render = () => drawScene(gl, programInfo, {
    face: { vao: faceVao, bufferInfo: faceBufferInfo },
    pivot: { vao: pivotVao, bufferInfo: pivotBufferInfo },
  }, state);

  setupGui(state, render);
  render();
}

function drawScene(gl, programInfo, objects, state) {
  twgl.resizeCanvasToDisplaySize(gl.canvas);
  gl.viewport(0, 0, gl.canvas.width, gl.canvas.height);
  gl.clearColor(1, 1, 1, 1);
  gl.clear(gl.COLOR_BUFFER_BIT);

  const commonUniforms = {
    u_resolution: [gl.canvas.width, gl.canvas.height],
  };

  gl.useProgram(programInfo.program);

  // Draw pivot marker
  gl.bindVertexArray(objects.pivot.vao);
  twgl.setUniforms(programInfo, {
    ...commonUniforms,
    u_matrix: translation(state.pivot.x, state.pivot.y),
  });
  twgl.drawBufferInfo(gl, objects.pivot.bufferInfo);

  // Draw face using pivot-aware rotation
  const rotationMatrix = rotationAround(
    degToRad(state.face.rotation),
    state.pivot.x,
    state.pivot.y,
  );

  const faceMatrix = multiplyAll([
    rotationMatrix,
    translation(state.face.tx, state.face.ty),
    scaling(state.face.scaleX, state.face.scaleY),
  ]);

  gl.bindVertexArray(objects.face.vao);
  twgl.setUniforms(programInfo, {
    ...commonUniforms,
    u_matrix: faceMatrix,
  });
  twgl.drawBufferInfo(gl, objects.face.bufferInfo);
}

function setupGui(state, onChange) {
  const gui = new GUI();

  const pivotFolder = gui.addFolder('Pivote');
  pivotFolder.add(state.pivot, 'x', 0, 960, 1).name('Posición X').onChange(onChange);
  pivotFolder.add(state.pivot, 'y', 0, 540, 1).name('Posición Y').onChange(onChange);
  pivotFolder.open();

  const faceFolder = gui.addFolder('Cara');
  faceFolder.add(state.face, 'tx', 0, 960, 1).name('Traslación X').onChange(onChange);
  faceFolder.add(state.face, 'ty', 0, 540, 1).name('Traslación Y').onChange(onChange);
  faceFolder.add(state.face, 'scaleX', 0.2, 3, 0.01).name('Escala X').onChange(onChange);
  faceFolder.add(state.face, 'scaleY', 0.2, 3, 0.01).name('Escala Y').onChange(onChange);
  faceFolder.add(state.face, 'rotation', -180, 180, 1).name('Rotación').onChange(onChange);
  faceFolder.open();

  return gui;
}

function createFaceGeometry() {
  const arrays = {
    a_position: { numComponents: 2, data: [] },
    a_color: { numComponents: 4, data: [] },
  };

  const faceColor = [1, 0.92, 0.23, 1];
  const segments = 24;
  const radius = 110;
  for (let i = 0; i < segments; i++) {
    const angle1 = (i / segments) * Math.PI * 2;
    const angle2 = ((i + 1) / segments) * Math.PI * 2;
    appendTriangle(arrays,
      [0, 0],
      [Math.cos(angle1) * radius, Math.sin(angle1) * radius],
      [Math.cos(angle2) * radius, Math.sin(angle2) * radius],
      faceColor,
    );
  }

  const eyebrowColor = [0.1, 0.1, 0.1, 1];
  appendTriangle(arrays, [-50, -80], [-80, -60], [-20, -60], eyebrowColor);
  appendTriangle(arrays, [50, -80], [80, -60], [20, -60], eyebrowColor);

  const eyeColor = [0.1, 0.1, 0.1, 1];
  appendTriangle(arrays, [-30, 10], [-65, -40], [-25, -40], eyeColor);
  appendTriangle(arrays, [30, 10], [65, -40], [25, -40], eyeColor);

  const mouthColor = [0.05, 0.05, 0.05, 1];
  appendTriangle(arrays, [70, 25], [-70, 25], [40, 60], mouthColor);
  appendTriangle(arrays, [-70, 25], [-40, 60], [40, 60], mouthColor);

  return arrays;
}

function createPivotGeometry() {
  const arrays = {
    a_position: { numComponents: 2, data: [] },
    a_color: { numComponents: 4, data: [] },
  };

  const pivotColor = [0.55, 0.55, 0.58, 1];
  appendTriangle(arrays, [0, -20], [20, 0], [0, 20], pivotColor);
  appendTriangle(arrays, [0, -20], [-20, 0], [0, 20], pivotColor);

  return arrays;
}

function appendTriangle(arrays, p0, p1, p2, color) {
  [
    ...p0,
    ...p1,
    ...p2,
  ].forEach((value) => arrays.a_position.data.push(value));

  for (let i = 0; i < 3; i++) {
    color.forEach((c) => arrays.a_color.data.push(c));
  }
}

function degToRad(deg) {
  return deg * Math.PI / 180;
}

'use strict';

/**
 * Basic 3x3 matrix helpers for 2D affine transformations.
 * Matrices are stored column-major to match WebGL expectations.
 */

export function identity() {
  return new Float32Array([
    1, 0, 0,
    0, 1, 0,
    0, 0, 1,
  ]);
}

export function translation(tx = 0, ty = 0) {
  return new Float32Array([
    1, 0, 0,
    0, 1, 0,
    tx, ty, 1,
  ]);
}

export function rotation(rad = 0) {
  const c = Math.cos(rad);
  const s = Math.sin(rad);
  return new Float32Array([
    c, s, 0,
    -s, c, 0,
    0, 0, 1,
  ]);
}

export function scaling(sx = 1, sy = 1) {
  return new Float32Array([
    sx, 0, 0,
    0, sy, 0,
    0, 0, 1,
  ]);
}

export function multiply(a, b) {
  const dst = new Float32Array(9);
  for (let col = 0; col < 3; col++) {
    for (let row = 0; row < 3; row++) {
      let sum = 0;
      for (let i = 0; i < 3; i++) {
        sum += a[row + i * 3] * b[i + col * 3];
      }
      dst[row + col * 3] = sum;
    }
  }
  return dst;
}

export function multiplyAll(matrices) {
  if (!matrices.length) {
    return identity();
  }
  return matrices.reduce((acc, mat) => multiply(acc, mat));
}

export function rotationAround(rad, px, py) {
  const translateToPivot = translation(px, py);
  const translateBack = translation(-px, -py);
  return multiplyAll([translateToPivot, rotation(rad), translateBack]);
}

main();
