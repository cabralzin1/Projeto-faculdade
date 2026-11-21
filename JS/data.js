// Camada de dados do painel.
// Sprint 2: substitui o JSON estatico por fetch() contra a API REST (FastAPI),
// que apura tudo a partir do banco dimensional (Dados/campanha.db).
//
// A interface publica (Dados.*) e mantida sincrona para nao reescrever a camada
// de apresentacao (site.js): os dados sao carregados uma vez em init() e a lista
// corrente (BASE) pode ser recalculada no banco via filtrarPorBanco().

const API_BASE =
  location.protocol === 'file:' ? 'http://127.0.0.1:8000/api' : 'api';

let CARGA = null;
let BASE = null; // lista corrente de candidatos (pode vir filtrada pelo banco)
let CARGO = '1'; // CD_CARGO corrente
let CARGOS = null; // cache da lista de cargos

async function httpJson(path) {
  const resp = await fetch(`${API_BASE}${path}`);
  if (!resp.ok) {
    throw new Error(`Falha ao consultar ${path}: HTTP ${resp.status}`);
  }
  return resp.json();
}

const Dados = {
  // Carrega a carga completa do cargo (resumo + candidatos + serie + origens + partidos).
  async init(cargo) {
    if (cargo) CARGO = String(cargo);
    const qs = CARGO ? `?cargo=${encodeURIComponent(CARGO)}` : '';
    CARGA = await httpJson('/carga' + qs);
    BASE = CARGA.candidatos;
    return Dados;
  },

  obterCarga() {
    return CARGA;
  },

  obterCargo() {
    return CARGO;
  },

  // Lista corrente (respeita filtros de periodo/categoria aplicados no banco).
  listarCandidatos() {
    return (BASE || (CARGA && CARGA.candidatos) || []).slice();
  },

  // Recalcula a lista de candidatos no banco aplicando periodo e categoria.
  async filtrarPorBanco({ data_ini, data_fim, categoria } = {}) {
    const params = new URLSearchParams();
    params.set('cargo', CARGO);
    if (data_ini) params.set('data_ini', data_ini);
    if (data_fim) params.set('data_fim', data_fim);
    if (categoria) params.set('categoria', categoria);
    const data = await httpJson(`/candidatos?${params.toString()}`);
    BASE = data.candidatos;
    return data; // { filtros, resumo, candidatos }
  },

  obterCandidato(sq) {
    return (CARGA.candidatos || []).find((c) => c.sq_candidato === sq) || null;
  },

  // Detalhe completo (com origens) — carregado sob demanda.
  async detalheCandidato(sq) {
    return httpJson(`/candidatos/${encodeURIComponent(sq)}`);
  },

  // Lista de cargos disponiveis (cache).
  async listarCargos() {
    if (!CARGOS) {
      const data = await httpJson('/cargos');
      CARGOS = data.cargos;
    }
    return CARGOS;
  },

  // Custos por partido. Sem cargo = soma todos os cargos.
  async partidos(cargo) {
    const qs = cargo ? `?cargo=${encodeURIComponent(cargo)}` : '';
    return httpJson('/partidos' + qs);
  },

  listarPartidos() {
    const vistos = new Map();
    CARGA.candidatos.forEach((c) => {
      if (!vistos.has(c.sg_partido)) {
        vistos.set(c.sg_partido, c.nm_partido);
      }
    });
    return Array.from(vistos, ([sigla, nome]) => ({ sigla, nome })).sort((a, b) =>
      a.sigla.localeCompare(b.sigla, 'pt-BR')
    );
  },

  listarTiposPrestacao() {
    const tipos = new Set();
    CARGA.candidatos.forEach((c) => {
      c.prestacoes.forEach((p) => tipos.add(p.tipo));
    });
    return Array.from(tipos).sort((a, b) => a.localeCompare(b, 'pt-BR'));
  },

  listarOrigens() {
    return (CARGA.origens_gerais || []).map((o) => o.origem);
  },

  // Alias claro para o filtro de categoria do painel.
  listarCategorias() {
    return Dados.listarOrigens();
  },
};