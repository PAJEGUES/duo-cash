// a galeria de ícones só aparece quando a categoria escolhida é Lazer
const chips = document.querySelectorAll('#categorias .chip');
const galeria = document.getElementById('galeria');

chips.forEach(function (chip) {
  chip.addEventListener('click', function () {
    chips.forEach(function (c) { c.classList.remove('ativo'); });
    chip.classList.add('ativo');
    galeria.style.display = chip.hasAttribute('data-lazer') ? 'block' : 'none';
  });
});

const icones = document.querySelectorAll('.icones button');

icones.forEach(function (botao) {
  botao.addEventListener('click', function () {
    icones.forEach(function (b) { b.classList.remove('ativo'); });
    botao.classList.add('ativo');
  });
});
