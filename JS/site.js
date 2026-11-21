(function () {
  'use strict';

  const moeda = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
  const inteiro = new Intl.NumberFormat('pt-BR');
  const PALETA = [
    '#2563eb',
    '#f59e0b',
    '#10b981',
    '#8b5cf6',
    '#06b6d4',
    '#ec4899',
    '#84cc16',
    '#f97316',
    '#6366f1',
    '#14b8a6',
    '#a855f7',
    '#eab308',
  ];

  const INICIO_EVOLUCAO = '2026-08-06';
  const FIM_EVOLUCAO = '2026-12-31';

  const NOME_POPULAR = {
    '280002551544': 'Flávio Bolsonaro',
    '280002551932': 'Ronaldo Caiado',
    '280002542548': 'Lula',
    '280002539826': 'Romeu Zema',
    '280002540694': 'Renan Santos',
    '280002548139': 'Wilson Grassi',
    '280002541457': 'Hertz Dias',
    '280002551547': 'Augusto Cury',
    '280002551975': 'Edmilson Costa',
    '280002552487': 'Rui Costa Pimenta',
    '280002552484': 'Clariana Barão',
    '280002538811': 'Samara',
  };

  const el = (id) => document.getElementById(id);
  const graficos = {};

  const estado = {
    view: 'visao',
    cargo: '1',
    busca: '',
    ordem: 'valor_desc',
    partido: '',
    prestacao: '',
    categoria: '',
    dataIni: '',
    dataFim: '',
    tipoGrafico: 'horizontalBar',
    escala: 'dia',
    aberto: null,
    compararA: '',
    compararB: '',
    origensCache: {},
  };

  function rotuloLancamentos(n) {
    return n === 1 ? '1 lançamento' : `${inteiro.format(n)} lançamentos`;
  }

  function dataBR(iso) {
    if (!iso) return '—';
    if (iso.includes('/')) return iso;
    const [ano, mes, dia] = iso.split('-');
    return `${dia}/${mes}/${ano}`;
  }

  function eixoReais(valor) {
    if (Math.abs(valor) >= 1e6) {
      return (valor / 1e6).toFixed(1).replace('.', ',') + ' mi';
    }
    if (Math.abs(valor) >= 1e3) {
      return (valor / 1e3).toFixed(0) + ' mil';
    }
    return String(valor);
  }

  function candidatoTemPrestacao(candidato, tipo) {
    if (!tipo) return true;
    return candidato.prestacoes.some((p) => p.tipo === tipo);
  }

  function filtrar() {
    const termo = estado.busca.trim().toLowerCase();
    return Dados.listarCandidatos()
      .filter((c) => {
        if (estado.partido && c.sg_partido !== estado.partido) return false;
        if (!candidatoTemPrestacao(c, estado.prestacao)) return false;
        if (!termo) return true;
        const alvo = `${nomePopular(c)} ${c.nm_candidato} ${c.nr_candidato} ${c.sg_partido} ${c.nm_partido}`.toLowerCase();
        return alvo.includes(termo);
      })
      .sort((a, b) => {
        const porNome = a.nm_candidato.localeCompare(b.nm_candidato, 'pt-BR');
        switch (estado.ordem) {
          case 'valor_asc':
            return a.total - b.total || porNome;
          case 'nome':
            return porNome;
          case 'lancamentos':
            return b.lancamentos - a.lancamentos || b.total - a.total || porNome;
          default:
            return b.total - a.total || porNome;
        }
      });
  }

  function nomePopular(c) {
    return NOME_POPULAR[c.sq_candidato] || c.nm_candidato;
  }

  function rotuloCandidato(c) {
    return nomePopular(c);
  }

  function origensDoRecorte(lista) {
    const mapa = new Map();
    lista.forEach((c) => {
      c.origens.forEach((o) => {
        if (!o.origem || o.origem === '#NULO') return;
        const atual = mapa.get(o.origem) || { origem: o.origem, total: 0, lancamentos: 0 };
        atual.total += o.total;
        atual.lancamentos += o.lancamentos;
        mapa.set(o.origem, atual);
      });
    });
    return Array.from(mapa.values()).sort((a, b) => b.total - a.total);
  }

  function partidosDoRecorte(lista) {
    const mapa = new Map();
    lista.forEach((c) => {
      const atual = mapa.get(c.sg_partido) || { sigla: c.sg_partido, total: 0 };
      atual.total += c.total;
      mapa.set(c.sg_partido, atual);
    });
    return Array.from(mapa.values()).sort((a, b) => b.total - a.total);
  }

  function corPartido(indice) {
    if (indice < PALETA.length) return PALETA[indice];
    const hue = Math.round((indice * 360) / (PALETA.length + 7)) % 360;
    return `hsl(${hue}, 62%, 52%)`;
  }

  function atualizarEvolucao(lista) {
    const grafico = graficos.mes;
    const partidosVisiveis = new Set(lista.map((c) => c.sg_partido));

    const serie = (Dados.obterCarga().serie_diaria || []).filter(
      (d) => d.data >= INICIO_EVOLUCAO && d.data <= FIM_EVOLUCAO
    );

    const porDia = new Map();
    serie.forEach((dia) => {
      porDia.set(dia.data, new Map(Object.entries(dia.por_partido || {})));
    });

    const totais = new Map();
    serie.forEach((dia) => {
      porDia.get(dia.data).forEach((valor, partido) => {
        totais.set(partido, (totais.get(partido) || 0) + valor);
      });
    });

    // remove dias iniciais/finais sem valor (evita barras vazias e outliers 2025/2027+).
    let primeiro = 0;
    while (primeiro < serie.length) {
      const mapa = porDia.get(serie[primeiro].data);
      const soma = Array.from(mapa.values()).reduce((a, b) => a + b, 0);
      if (soma > 0) break;
      primeiro += 1;
    }
    let ultimo = serie.length - 1;
    while (ultimo >= primeiro) {
      const mapa = porDia.get(serie[ultimo].data);
      const soma = Array.from(mapa.values()).reduce((a, b) => a + b, 0);
      if (soma > 0) break;
      ultimo -= 1;
    }
    const recorte = ultimo >= primeiro ? serie.slice(primeiro, ultimo + 1) : [];

    let buckets;
    if (estado.escala === 'semana') {
      buckets = [];
      for (let i = 0; i < recorte.length; i += 7) {
        const fim = recorte[Math.min(i + 6, recorte.length - 1)];
        buckets.push({
          rotulo: `${dataBR(recorte[i].data).slice(0, 5)}–${dataBR(fim.data).slice(0, 5)}`,
          dias: recorte.slice(i, i + 7).map((d) => d.data),
        });
      }
    } else {
      buckets = recorte.map((d) => ({ rotulo: dataBR(d.data).slice(0, 5), dias: [d.data] }));
    }

    const partidos = Array.from(totais, ([partido, total]) => ({ partido, total }))
      .filter((p) => p.total > 0 && partidosVisiveis.has(p.partido))
      .sort((a, b) => b.total - a.total);

    grafico.data.labels = buckets.map((b) => b.rotulo);
    grafico.data.datasets = partidos.map((p, i) => ({
      label: p.partido,
      data: buckets.map((b) => {
        let soma = 0;
        b.dias.forEach((data) => {
          soma += porDia.get(data).get(p.partido) || 0;
        });
        return Math.round(soma * 100) / 100;
      }),
      backgroundColor: corPartido(i),
      borderRadius: 3,
      maxBarThickness: estado.escala === 'semana' ? 46 : 12,
    }));

    grafico.options.scales.x.ticks.maxTicksLimit = estado.escala === 'semana' ? 15 : 10;
    grafico.options.scales.x.ticks.font = { size: 9 };
    grafico.options.scales.x.ticks.maxRotation = 0;
    grafico.options.scales.x.ticks.autoSkip = true;
    grafico.update();
  }

  function padraoGrafico() {
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => moeda.format(ctx.parsed.y ?? ctx.parsed),
          },
        },
      },
    };
  }

  function criarGraficos() {
    graficos.mes = new Chart(el('graficoMes'), {
      type: 'bar',
      data: { labels: [], datasets: [] },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'nearest', intersect: true },
        plugins: {
          legend: {
            position: 'bottom',
            labels: { boxWidth: 8, boxHeight: 8, font: { size: 8 }, padding: 4 },
          },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.dataset.label}: ${moeda.format(ctx.parsed.y)}`,
              footer: (items) => {
                if (!items.length) return '';
                const chart = items[0].chart;
                const indice = items[0].dataIndex;
                let soma = 0;
                chart.data.datasets.forEach((ds) => {
                  const valor = Number(ds.data[indice]);
                  if (valor) soma += valor;
                });
                return `Total: ${moeda.format(soma)}`;
              },
            },
          },
        },
        scales: {
          x: {
            stacked: true,
            grid: { display: false },
            ticks: { maxRotation: 0, autoSkip: true },
          },
          y: {
            stacked: true,
            beginAtZero: true,
            ticks: { callback: eixoReais },
            grid: { color: '#e5edf7' },
          },
        },
      },
    });

    graficos.origens = new Chart(el('graficoOrigens'), {
      type: 'doughnut',
      data: { labels: [], datasets: [{ data: [], backgroundColor: PALETA, borderColor: '#fff', borderWidth: 2 }] },
      options: {
        ...padraoGrafico(),
        plugins: {
          legend: { position: 'right', labels: { boxWidth: 10, font: { size: 10 } } },
          tooltip: {
            callbacks: { label: (ctx) => `${ctx.label}: ${moeda.format(ctx.parsed)}` },
          },
        },
      },
    });

    graficos.partidos = new Chart(el('graficoPartidos'), {
      type: 'bar',
      data: { labels: [], datasets: [{ data: [], backgroundColor: PALETA, borderRadius: 6 }] },
      options: {
        ...padraoGrafico(),
        scales: {
          y: { ticks: { callback: eixoReais }, grid: { color: '#e5edf7' } },
          x: { grid: { display: false } },
        },
      },
    });
  }

  function aplicarTipoCandidatos() {
    const canvas = el('graficoCandidatos');
    const lista = filtrar()
      .filter((c) => c.total > 0)
      .sort((a, b) => b.total - a.total)
      .slice(0, 8);
    const labels = lista.map(rotuloCandidato);
    const valores = lista.map((c) => c.total);
    const tipo = estado.tipoGrafico;
    const horizontal = tipo === 'horizontalBar';
    const doughnut = tipo === 'doughnut';

    if (graficos.candidatos) {
      graficos.candidatos.destroy();
    }

    graficos.candidatos = new Chart(canvas, {
      type: doughnut ? 'doughnut' : 'bar',
      data: {
        labels,
        datasets: [
          {
            data: valores,
            backgroundColor: PALETA,
            borderColor: doughnut ? '#fff' : undefined,
            borderWidth: doughnut ? 2 : 0,
            borderRadius: doughnut ? 0 : 6,
          },
        ],
      },
      options: doughnut
        ? {
            ...padraoGrafico(),
            plugins: {
              legend: { position: 'right', labels: { boxWidth: 10, font: { size: 10 } } },
              tooltip: {
                callbacks: { label: (ctx) => `${ctx.label}: ${moeda.format(ctx.parsed)}` },
              },
            },
          }
        : {
            ...padraoGrafico(),
            indexAxis: horizontal ? 'y' : 'x',
            scales: {
              x: {
                ticks: horizontal ? { callback: eixoReais } : { maxRotation: 50, font: { size: 10 } },
                grid: { display: horizontal, color: '#e5edf7' },
              },
              y: {
                ticks: horizontal ? { font: { size: 10 } } : { callback: eixoReais },
                grid: { display: !horizontal, color: '#e5edf7' },
              },
            },
            plugins: {
              legend: { display: false },
              tooltip: {
                callbacks: {
                  label: (ctx) => moeda.format(horizontal ? ctx.parsed.x : ctx.parsed.y),
                },
              },
            },
          },
    });
  }

  function atualizarGraficos() {
    const lista = filtrar();
    const total = lista.reduce((s, c) => s + c.total, 0);
    el('resumoTotal').textContent = moeda.format(total);
    el('resumoCandidatos').textContent = inteiro.format(lista.length);
    el('resumoLancamentos').textContent = inteiro.format(lista.reduce((s, c) => s + c.lancamentos, 0));

    aplicarTipoCandidatos();
    atualizarEvolucao(lista);

    let origens = origensDoRecorte(lista).slice(0, 6);
    if (!origens.length) {
      // Cargos grandes: origens por candidato não vieram no payload; usa o agregado do cargo.
      origens = (Dados.obterCarga().origens_gerais || []).slice(0, 6);
    }
    graficos.origens.data.labels = origens.map((o) =>
      o.origem.length > 28 ? o.origem.slice(0, 26) + '…' : o.origem
    );
    graficos.origens.data.datasets[0].data = origens.map((o) => o.total);

    const partidos = partidosDoRecorte(lista);
    graficos.partidos.data.labels = partidos.map((p) => p.sigla);
    graficos.partidos.data.datasets[0].data = partidos.map((p) => p.total);

    graficos.origens.update();
    graficos.partidos.update();
  }

  async function desenharPartidos() {
    const data = await Dados.partidos();
    const itens = data.partidos;
    const total = data.total;

    if (graficos.partidosGeral) graficos.partidosGeral.destroy();
    graficos.partidosGeral = new Chart(el('graficoPartidosGeral'), {
      type: 'bar',
      data: {
        labels: itens.map((p) => p.sigla),
        datasets: [
          {
            data: itens.map((p) => p.total),
            backgroundColor: PALETA,
            borderRadius: 6,
            maxBarThickness: 22,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        scales: {
          x: { ticks: { callback: eixoReais }, grid: { color: '#e5edf7' } },
          y: { grid: { display: false } },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => `${itens[ctx.dataIndex].sigla}: ${moeda.format(ctx.parsed.x)}`,
            },
          },
        },
      },
    });

    el('tabelaPartidos').innerHTML =
      `<table class="tabela-itens"><thead><tr><th>Partido</th><th class="numero">Lançamentos</th><th class="numero">Total</th><th class="numero">% do total</th></tr></thead><tbody>` +
      itens
        .map((p) => {
          const pct = total ? ((p.total / total) * 100).toFixed(1).replace('.', ',') : '0,0';
          return `<tr><td><b>${p.sigla}</b></td><td class="numero">${inteiro.format(p.lancamentos)}</td><td class="numero">${moeda.format(p.total)}</td><td class="numero">${pct}%</td></tr>`;
        })
        .join('') +
      `</tbody></table>`;
  }

  function desenharResumoFixo() {
    const carga = Dados.obterCarga();
    const cargoNome = (carga.candidatos[0] && carga.candidatos[0].ds_cargo) || 'Cargo';
    el('resumoGeracao').textContent = carga.dt_geracao_tse || '—';
    el('periodoDespesas').textContent =
      `${dataBR(carga.periodo_despesas.inicio)} a ${dataBR(carga.periodo_despesas.fim)}`;
    el('menuCargo').textContent = cargoNome;
    document.title = `Financiamento de Campanha — ${cargoNome} 2026`;
    desenharAvisos();
  }

  function desenharAvisos() {
    const caixa = el('avisos');
    if (!caixa) return;
    const avisos = (Dados.obterCarga().avisos_desatualizados) || [];
    caixa.innerHTML = avisos
      .map(
        (a) =>
          `<p class="aviso" role="note"><strong>Dado desatualizado.</strong> ${a.texto}</p>`
      )
      .join('');
  }

  async function popularCargos() {
    const select = el('filtroCargo');
    const cargos = await Dados.listarCargos();
    select.innerHTML = '';
    cargos.forEach((c) => {
      const opcao = document.createElement('option');
      opcao.value = c.cd_cargo;
      opcao.textContent = c.nome;
      select.appendChild(opcao);
    });
    select.value = estado.cargo;
  }

  function popularFiltros() {
    Dados.listarPartidos().forEach((p) => {
      const opcao = document.createElement('option');
      opcao.value = p.sigla;
      opcao.textContent = p.sigla;
      el('filtroPartido').appendChild(opcao);
    });
    Dados.listarTiposPrestacao().forEach((tipo) => {
      const opcao = document.createElement('option');
      opcao.value = tipo;
      opcao.textContent = tipo;
      el('filtroPrestacao').appendChild(opcao);
    });
    Dados.listarCategorias().forEach((cat) => {
      const opcao = document.createElement('option');
      opcao.value = cat;
      opcao.textContent = cat;
      el('filtroCategoria').appendChild(opcao);
    });
  }

  async function aplicarFiltrosBanco() {
    await Dados.filtrarPorBanco({
      data_ini: estado.dataIni,
      data_fim: estado.dataFim,
      categoria: estado.categoria,
    });
    atualizarGraficos();
    desenharLista();
  }

  function popularComparar() {
    [el('compararA'), el('compararB')].forEach((select) => {
      const atual = select.value;
      select.innerHTML = '<option value="">Selecione</option>';
      Dados.listarCandidatos()
        .slice()
        .sort((a, b) => b.total - a.total)
        .slice(0, 200)
        .forEach((c) => {
          const opcao = document.createElement('option');
          opcao.value = c.sq_candidato;
          opcao.textContent = `${nomePopular(c)} (${c.sg_partido})`;
          select.appendChild(opcao);
        });
      select.value = atual;
    });
  }

  function mostrarView(nome) {
    estado.view = nome;
    document.querySelectorAll('.view').forEach((secao) => {
      secao.hidden = secao.id !== `view-${nome}`;
    });
    document.querySelectorAll('.menu__item').forEach((botao) => {
      botao.classList.toggle('menu__item--ativo', botao.dataset.view === nome);
    });
    if (nome === 'visao') atualizarGraficos();
    if (nome === 'partidos') desenharPartidos();
  }

  function limparErrosComparacao() {
    ['erroComparar', 'erroCompararA', 'erroCompararB'].forEach((id) => {
      const no = el(id);
      no.hidden = true;
      no.textContent = '';
    });
    el('compararA').closest('.campo').classList.remove('campo--invalido');
    el('compararB').closest('.campo').classList.remove('campo--invalido');
  }

  function mostrarErro(idCampo, idErro, mensagem) {
    const erro = el(idErro);
    erro.hidden = false;
    erro.textContent = mensagem;
    if (idCampo) el(idCampo).closest('.campo').classList.add('campo--invalido');
  }

  function validarComparacao() {
    limparErrosComparacao();
    let ok = true;
    if (!estado.compararA) {
      mostrarErro('compararA', 'erroCompararA', 'Selecione o primeiro candidato.');
      ok = false;
    }
    if (!estado.compararB) {
      mostrarErro('compararB', 'erroCompararB', 'Selecione o segundo candidato.');
      ok = false;
    }
    if (estado.compararA && estado.compararB && estado.compararA === estado.compararB) {
      mostrarErro(null, 'erroComparar', 'Escolha dois candidatos diferentes.');
      ok = false;
    }
    return ok;
  }

  function origensAlinhadas(a, b) {
    const nomes = new Set([...a.origens.map((o) => o.origem), ...b.origens.map((o) => o.origem)]);
    const mapaA = Object.fromEntries(a.origens.map((o) => [o.origem, o.total]));
    const mapaB = Object.fromEntries(b.origens.map((o) => [o.origem, o.total]));
    return Array.from(nomes)
      .map((origem) => ({ origem, a: mapaA[origem] || 0, b: mapaB[origem] || 0 }))
      .sort((x, y) => y.a + y.b - (x.a + x.b));
  }

  async function desenharComparacao() {
    const caixa = el('resultadoComparacao');
    if (!validarComparacao()) {
      caixa.hidden = true;
      caixa.innerHTML = '';
      return;
    }
    const [a, b] = await Promise.all([
      Dados.detalheCandidato(estado.compararA),
      Dados.detalheCandidato(estado.compararB),
    ]);
    const origens = origensAlinhadas(a, b).filter((o) => o.origem !== '#NULO').slice(0, 8);
    const linhas = origens
      .map(
        (o) => `<tr><td>${o.origem}</td><td class="numero">${moeda.format(o.a)}</td><td class="numero">${moeda.format(o.b)}</td></tr>`
      )
      .join('');
    const desatualizados = [a, b].filter((c) => c && c.desatualizado);
    const avisoDesatualizado = desatualizados.length
      ? `<p class="comparacao__aviso"><strong>Atenção:</strong> ${desatualizados
          .map((c) => nomePopular(c))
          .join(' e ')} ${desatualizados.length > 1 ? 'têm' : 'tem'} valores <b>desatualizados</b> (carga parcial de 12/09/2026 — não constam na fonte de 21/11/2026).</p>`
      : '';
    caixa.innerHTML = `
      <div class="comparacao__pares">
        <article>
          <h3>${nomePopular(a)}${a.desatualizado ? '<span class="selo-desatualizado">Desatualizado</span>' : ''}</h3>
          <p>${a.sg_partido} · nº ${a.nr_candidato}</p>
          <p class="comparacao__valor">${moeda.format(a.total)}</p>
        </article>
        <article>
          <h3>${nomePopular(b)}${b.desatualizado ? '<span class="selo-desatualizado">Desatualizado</span>' : ''}</h3>
          <p>${b.sg_partido} · nº ${b.nr_candidato}</p>
          <p class="comparacao__valor">${moeda.format(b.total)}</p>
        </article>
      </div>
      ${avisoDesatualizado}
      <table class="tabela-itens">
        <thead><tr><th>Origem</th><th class="numero">A</th><th class="numero">B</th></tr></thead>
        <tbody>${linhas}</tbody>
      </table>`;
    caixa.hidden = false;
  }

  function desenharLista() {
    const lista = filtrar();
    const container = el('listaCandidatos');
    const max = Math.max(0, ...lista.map((c) => c.total));
    const limite = 100;
    const mostrados = lista.slice(0, limite);
    container.innerHTML = '';
    el('contagemLista').textContent =
      (lista.length === 1
        ? '1 candidato neste recorte'
        : `${inteiro.format(lista.length)} candidatos neste recorte`) +
      (lista.length > limite ? ` · mostrando os ${limite} maiores` : '');

    if (!lista.length) {
      container.innerHTML = '<p class="lista__vazia">Nenhum candidato neste filtro.</p>';
      return;
    }

    mostrados.forEach((c) => {
      const artigo = document.createElement('article');
      artigo.className = c.desatualizado ? 'candidato candidato--desatualizado' : 'candidato';
      const pct = max > 0 ? (c.total / max) * 100 : 0;
      const tipo = c.prestacoes.map((p) => p.tipo).join(', ') || '—';
      artigo.innerHTML = `
        <div class="candidato__topo">
          <div>
            <p class="candidato__nome">${nomePopular(c)}${c.desatualizado ? '<span class="selo-desatualizado">Desatualizado</span>' : ''}</p>
            <p class="candidato__meta">nº ${c.nr_candidato} · ${c.sg_partido} · ${tipo}</p>
          </div>
          <div>
            <p class="candidato__valor">${moeda.format(c.total)}</p>
            <p class="candidato__meta">${rotuloLancamentos(c.lancamentos)}</p>
          </div>
        </div>
        <div class="barra" aria-hidden="true"><span style="width:${pct}%"></span></div>
        ${c.desatualizado ? '<p class="candidato__aviso">Valor da carga parcial de 12/09/2026 — desatualizado, não consta na fonte de 21/11/2026.</p>' : ''}`;
      const botao = document.createElement('button');
      botao.type = 'button';
      botao.className = 'expandir';
      botao.textContent = estado.aberto === c.sq_candidato ? 'Ocultar origens' : 'Ver origens';
      botao.addEventListener('click', async () => {
        const sq = c.sq_candidato;
        if (estado.aberto === sq) {
          estado.aberto = null;
          desenharLista();
          return;
        }
        estado.aberto = sq;
        desenharLista();
        if (!estado.origensCache[sq]) {
          try {
            const detalhe = await Dados.detalheCandidato(sq);
            estado.origensCache[sq] = detalhe.origens || [];
          } catch (e) {
            estado.origensCache[sq] = [];
          }
          if (estado.aberto === sq) desenharLista();
        }
      });
      artigo.querySelector('.candidato__topo').appendChild(botao);

      if (estado.aberto === c.sq_candidato) {
        const origens = (estado.origensCache[c.sq_candidato] || []).filter(
          (o) => o.origem !== '#NULO' || o.total > 0
        );
        const detalhe = document.createElement('div');
        detalhe.innerHTML = `<table class="tabela-itens"><thead><tr><th>Origem</th><th class="numero">Lanç.</th><th class="numero">Valor</th></tr></thead><tbody>${origens
          .map(
            (o) =>
              `<tr><td>${o.origem === '#NULO' ? 'Não informado' : o.origem}</td><td class="numero">${inteiro.format(o.lancamentos)}</td><td class="numero">${moeda.format(o.total)}</td></tr>`
          )
          .join('')}</tbody></table>`;
        artigo.appendChild(detalhe);
      }
      container.appendChild(artigo);
    });
  }

  function ligarEventos() {
    el('filtroCargo').addEventListener('change', (e) => {
      const url = new URL(location.href);
      url.searchParams.set('cargo', e.target.value);
      location.href = url.toString();
    });
    document.querySelectorAll('.menu__item').forEach((botao) => {
      botao.addEventListener('click', () => mostrarView(botao.dataset.view));
    });
    el('filtroPartido').addEventListener('change', (e) => {
      estado.partido = e.target.value;
      atualizarGraficos();
      desenharLista();
    });
    el('filtroPrestacao').addEventListener('change', (e) => {
      estado.prestacao = e.target.value;
      atualizarGraficos();
      desenharLista();
    });
    el('filtroCategoria').addEventListener('change', async (e) => {
      estado.categoria = e.target.value;
      await aplicarFiltrosBanco();
    });
    el('filtroDataIni').addEventListener('change', async (e) => {
      estado.dataIni = e.target.value;
      await aplicarFiltrosBanco();
    });
    el('filtroDataFim').addEventListener('change', async (e) => {
      estado.dataFim = e.target.value;
      await aplicarFiltrosBanco();
    });
    el('tipoGrafico').addEventListener('change', (e) => {
      estado.tipoGrafico = e.target.value;
      aplicarTipoCandidatos();
    });
    el('escalaEvolucao').addEventListener('change', (e) => {
      estado.escala = e.target.value;
      atualizarEvolucao(filtrar());
    });
    el('busca').addEventListener('input', (e) => {
      estado.busca = e.target.value;
      desenharLista();
    });
    el('ordenacao').addEventListener('change', (e) => {
      estado.ordem = e.target.value;
      desenharLista();
    });
    el('compararA').addEventListener('change', (e) => {
      estado.compararA = e.target.value;
    });
    el('compararB').addEventListener('change', (e) => {
      estado.compararB = e.target.value;
    });
    el('botaoComparar').addEventListener('click', desenharComparacao);
    el('limparComparacao').addEventListener('click', () => {
      estado.compararA = '';
      estado.compararB = '';
      el('compararA').value = '';
      el('compararB').value = '';
      limparErrosComparacao();
      el('resultadoComparacao').hidden = true;
      el('resultadoComparacao').innerHTML = '';
    });
  }

  async function iniciar() {
    const params = new URLSearchParams(location.search);
    estado.cargo = params.get('cargo') || '1';
    await Dados.init(estado.cargo);
    const periodo = Dados.obterCarga().periodo_despesas;
    ['filtroDataIni', 'filtroDataFim'].forEach((id) => {
      el(id).min = periodo.inicio;
      el(id).max = periodo.fim;
    });
    desenharResumoFixo();
    await popularCargos();
    popularFiltros();
    popularComparar();
    criarGraficos();
    ligarEventos();
    atualizarGraficos();
    desenharLista();
  }

  iniciar();
})();