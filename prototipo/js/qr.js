// Desenha um QR Code "de mentira" só para o protótipo.
// No app de verdade o QR é gerado a partir do link do convite.
const N = 25;
const celulas = [];

// gerador pseudoaleatório com semente fixa, para o desenho ser sempre o mesmo
let semente = 2026;
function sorteio() {
  semente = (semente * 9301 + 49297) % 233280;
  return semente / 233280;
}

function noCanto(l, c) {
  return (l < 8 && c < 8) || (l < 8 && c >= N - 8) || (l >= N - 8 && c < 8);
}

for (let l = 0; l < N; l++) {
  for (let c = 0; c < N; c++) {
    if (!noCanto(l, c) && sorteio() > 0.52) {
      celulas.push('<rect x="' + c + '" y="' + l + '" width="1" height="1"/>');
    }
  }
}

// os três quadrados dos cantos
function marcador(x, y) {
  return '<rect x="' + x + '" y="' + y + '" width="7" height="7"/>' +
    '<rect x="' + (x + 1) + '" y="' + (y + 1) + '" width="5" height="5" fill="#fff"/>' +
    '<rect x="' + (x + 2) + '" y="' + (y + 2) + '" width="3" height="3"/>';
}

document.getElementById('qr').innerHTML =
  '<svg viewBox="0 0 ' + N + ' ' + N + '" fill="#23212b" shape-rendering="crispEdges">' +
  celulas.join('') + marcador(0, 0) + marcador(N - 7, 0) + marcador(0, N - 7) +
  '</svg>';
