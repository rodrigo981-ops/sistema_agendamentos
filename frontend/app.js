const state = {
  apiBaseUrl: localStorage.getItem('agenda_api_base') || 'http://127.0.0.1:5000',
  clientes: [],
  servicos: [],
  administradores: [],
  agendamentos: [],
};

const el = {};

document.addEventListener('DOMContentLoaded', () => {
  bindElements();
  bindEvents();
  initializeUI();
  refreshAll();
});

function bindElements() {
  el.apiBaseUrl = document.getElementById('apiBaseUrl');
  el.apiStatus = document.getElementById('apiStatus');
  el.pageTitle = document.getElementById('pageTitle');
  el.todayLabel = document.getElementById('todayLabel');

  el.totalClientes = document.getElementById('totalClientes');
  el.totalServicos = document.getElementById('totalServicos');
  el.totalServicosAtivos = document.getElementById('totalServicosAtivos');
  el.totalAgendamentos = document.getElementById('totalAgendamentos');
  el.todayAppointments = document.getElementById('todayAppointments');
  el.statusSummary = document.getElementById('statusSummary');
  el.toastContainer = document.getElementById('toastContainer');

  el.clienteForm = document.getElementById('clienteForm');
  el.clienteFormTitle = document.getElementById('clienteFormTitle');
  el.clienteId = document.getElementById('clienteId');
  el.clienteNome = document.getElementById('clienteNome');
  el.clienteTelefone = document.getElementById('clienteTelefone');
  el.clienteObs = document.getElementById('clienteObs');
  el.clienteBusca = document.getElementById('clienteBusca');
  el.clientesTableBody = document.getElementById('clientesTableBody');

  el.servicoForm = document.getElementById('servicoForm');
  el.servicoFormTitle = document.getElementById('servicoFormTitle');
  el.servicoId = document.getElementById('servicoId');
  el.servicoNome = document.getElementById('servicoNome');
  el.servicoDuracao = document.getElementById('servicoDuracao');
  el.servicoPreco = document.getElementById('servicoPreco');
  el.servicoAtivo = document.getElementById('servicoAtivo');
  el.servicoFiltroAtivo = document.getElementById('servicoFiltroAtivo');
  el.servicosTableBody = document.getElementById('servicosTableBody');

  el.agendamentoForm = document.getElementById('agendamentoForm');
  el.agendamentoFormTitle = document.getElementById('agendamentoFormTitle');
  el.agendamentoId = document.getElementById('agendamentoId');
  el.agendamentoCliente = document.getElementById('agendamentoCliente');
  el.agendamentoServico = document.getElementById('agendamentoServico');
  el.agendamentoAdmin = document.getElementById('agendamentoAdmin');
  el.agendamentoStatus = document.getElementById('agendamentoStatus');
  el.agendamentoData = document.getElementById('agendamentoData');
  el.agendamentoHora = document.getElementById('agendamentoHora');
  el.agendamentoObs = document.getElementById('agendamentoObs');
  el.filtroData = document.getElementById('filtroData');
  el.filtroStatus = document.getElementById('filtroStatus');
  el.agendamentosTableBody = document.getElementById('agendamentosTableBody');
}

function bindEvents() {
  document.querySelectorAll('.nav-link').forEach((button) => {
    button.addEventListener('click', () => setActiveSection(button.dataset.section));
  });

  document.querySelectorAll('[data-action="open-section"]').forEach((button) => {
    button.addEventListener('click', () => setActiveSection(button.dataset.target));
  });

  document.getElementById('saveApiBtn').addEventListener('click', saveApiBaseUrl);
  document.getElementById('testApiBtn').addEventListener('click', testApiConnection);
  document.getElementById('refreshAllBtn').addEventListener('click', refreshAll);

  document.getElementById('resetClienteBtn').addEventListener('click', resetClienteForm);
  document.getElementById('resetServicoBtn').addEventListener('click', resetServicoForm);
  document.getElementById('resetAgendamentoBtn').addEventListener('click', resetAgendamentoForm);

  document.getElementById('aplicarFiltrosBtn').addEventListener('click', loadAgendamentos);
  document.getElementById('limparFiltrosBtn').addEventListener('click', () => {
    el.filtroData.value = '';
    el.filtroStatus.value = '';
    loadAgendamentos();
  });

  el.clienteForm.addEventListener('submit', submitClienteForm);
  el.servicoForm.addEventListener('submit', submitServicoForm);
  el.agendamentoForm.addEventListener('submit', submitAgendamentoForm);

  el.clienteBusca.addEventListener('input', renderClientesTable);
  el.servicoFiltroAtivo.addEventListener('change', renderServicosTable);
}

function initializeUI() {
  el.apiBaseUrl.value = state.apiBaseUrl;
  const hoje = new Date();
  el.todayLabel.textContent = hoje.toLocaleDateString('pt-BR');
  el.agendamentoData.value = hoje.toISOString().split('T')[0];
}

function saveApiBaseUrl() {
  state.apiBaseUrl = normalizeBaseUrl(el.apiBaseUrl.value);
  localStorage.setItem('agenda_api_base', state.apiBaseUrl);
  el.apiBaseUrl.value = state.apiBaseUrl;
  showToast('URL da API salva com sucesso.', 'success');
}

function normalizeBaseUrl(value) {
  return (value || 'http://127.0.0.1:5000').trim().replace(/\/$/, '');
}

async function testApiConnection() {
  try {
    saveApiBaseUrl();
    const data = await apiRequest('/health');
    if (data.ok) {
      el.apiStatus.textContent = 'Conexão OK com a API.';
      showToast('API conectada com sucesso.', 'success');
    }
  } catch (error) {
    el.apiStatus.textContent = 'Falha ao conectar com a API.';
    showToast(error.message, 'error');
  }
}

async function refreshAll() {
  try {
    saveApiBaseUrl();
    await Promise.all([
      loadClientes(false),
      loadServicos(false),
      loadAdministradores(false),
      loadAgendamentos(false),
    ]);
    renderDashboard();
    renderClientesTable();
    renderServicosTable();
    renderAgendamentosTable();
    populateSelects();
    el.apiStatus.textContent = 'Dados carregados com sucesso.';
  } catch (error) {
    el.apiStatus.textContent = 'Erro ao carregar dados.';
    showToast(error.message, 'error');
  }
}

async function apiRequest(path, options = {}) {
  const response = await fetch(`${state.apiBaseUrl}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  });

  let payload = null;
  try {
    payload = await response.json();
  } catch (_) {
    payload = null;
  }

  if (!response.ok) {
    const message = payload?.erro || payload?.mensagem || 'Erro inesperado na API.';
    const detalhes = payload?.detalhes ? ` Detalhes: ${JSON.stringify(payload.detalhes)}` : '';
    throw new Error(`${message}${detalhes}`);
  }

  return payload;
}

async function loadClientes(render = true) {
  state.clientes = await apiRequest('/clientes');
  if (render) {
    renderClientesTable();
    populateSelects();
    renderDashboard();
  }
}

async function loadServicos(render = true) {
  state.servicos = await apiRequest('/servicos');
  if (render) {
    renderServicosTable();
    populateSelects();
    renderDashboard();
  }
}

async function loadAdministradores(render = true) {
  state.administradores = await apiRequest('/administradores');
  if (render) {
    populateSelects();
  }
}

async function loadAgendamentos(render = true) {
  const params = new URLSearchParams();
  if (el.filtroData?.value) params.append('data', el.filtroData.value);
  if (el.filtroStatus?.value) params.append('status', el.filtroStatus.value);
  const query = params.toString() ? `?${params.toString()}` : '';
  state.agendamentos = await apiRequest(`/agendamentos${query}`);
  if (render) {
    renderAgendamentosTable();
    renderDashboard();
  }
}

function renderDashboard() {
  el.totalClientes.textContent = state.clientes.length;
  el.totalServicos.textContent = state.servicos.length;
  el.totalServicosAtivos.textContent = state.servicos.filter((item) => Number(item.ativo) === 1).length;
  el.totalAgendamentos.textContent = state.agendamentos.length;

  const hoje = new Date().toISOString().split('T')[0];
  const hojeAgendamentos = state.agendamentos
    .filter((item) => item.data_atendimento === hoje)
    .sort((a, b) => a.horario_atendimento.localeCompare(b.horario_atendimento));

  if (!hojeAgendamentos.length) {
    el.todayAppointments.innerHTML = '<div class="empty-state-inline">Nenhum agendamento para hoje.</div>';
  } else {
    el.todayAppointments.innerHTML = hojeAgendamentos
      .map((item) => `
        <div class="list-item">
          <div>
            <strong>${escapeHtml(item.horario_atendimento)} · ${escapeHtml(item.cliente_nome)}</strong>
            <p>${escapeHtml(item.servico_nome)} · ${escapeHtml(item.administrador_nome || 'Administrador')}</p>
          </div>
          <span class="badge ${item.status.toLowerCase()}">${escapeHtml(item.status)}</span>
        </div>
      `)
      .join('');
  }

  const counts = {
    AGENDADO: 0,
    CONCLUIDO: 0,
    CANCELADO: 0,
  };
  state.agendamentos.forEach((item) => {
    counts[item.status] = (counts[item.status] || 0) + 1;
  });
  el.statusSummary.innerHTML = Object.entries(counts)
    .map(([status, total]) => `
      <div class="status-card">
        <div>
          <span class="badge ${status.toLowerCase()}">${status}</span>
        </div>
        <strong>${total}</strong>
      </div>
    `)
    .join('');
}

function renderClientesTable() {
  const term = (el.clienteBusca.value || '').trim().toLowerCase();
  const items = state.clientes.filter((cliente) => {
    const base = `${cliente.nome} ${cliente.telefone} ${cliente.observacoes || ''}`.toLowerCase();
    return base.includes(term);
  });

  el.clientesTableBody.innerHTML = items.length
    ? items.map((cliente) => `
        <tr>
          <td>${escapeHtml(cliente.nome)}</td>
          <td>${escapeHtml(cliente.telefone)}</td>
          <td>${escapeHtml(cliente.observacoes || '-')}</td>
          <td>
            <div class="table-actions">
              <button class="btn btn-secondary btn-sm" onclick="editCliente(${cliente.id})">Editar</button>
              <button class="btn btn-danger btn-sm" onclick="deleteCliente(${cliente.id})">Excluir</button>
            </div>
          </td>
        </tr>
      `).join('')
    : '<tr><td colspan="4" class="muted">Nenhum cliente encontrado.</td></tr>';
}

function renderServicosTable() {
  const filtro = el.servicoFiltroAtivo.value;
  const items = state.servicos.filter((servico) => {
    if (filtro === 'todos') return true;
    return String(servico.ativo) === filtro;
  });

  el.servicosTableBody.innerHTML = items.length
    ? items.map((servico) => `
        <tr>
          <td>${escapeHtml(servico.nome)}</td>
          <td>${servico.duracao_minutos} min</td>
          <td>${formatMoney(servico.preco)}</td>
          <td><span class="badge ${Number(servico.ativo) === 1 ? 'ativo' : 'inativo'}">${Number(servico.ativo) === 1 ? 'Ativo' : 'Inativo'}</span></td>
          <td>
            <div class="table-actions">
              <button class="btn btn-secondary btn-sm" onclick="editServico(${servico.id})">Editar</button>
              <button class="btn btn-warning btn-sm" onclick="toggleServicoAtivo(${servico.id}, ${Number(servico.ativo) === 1 ? 0 : 1})">${Number(servico.ativo) === 1 ? 'Inativar' : 'Ativar'}</button>
              <button class="btn btn-danger btn-sm" onclick="deleteServico(${servico.id})">Excluir</button>
            </div>
          </td>
        </tr>
      `).join('')
    : '<tr><td colspan="5" class="muted">Nenhum serviço encontrado.</td></tr>';
}

function renderAgendamentosTable() {
  const items = [...state.agendamentos].sort((a, b) => {
    const dataA = `${a.data_atendimento} ${a.horario_atendimento}`;
    const dataB = `${b.data_atendimento} ${b.horario_atendimento}`;
    return dataA.localeCompare(dataB);
  });

  el.agendamentosTableBody.innerHTML = items.length
    ? items.map((agendamento) => `
        <tr>
          <td>${formatDate(agendamento.data_atendimento)}</td>
          <td>${escapeHtml(agendamento.horario_atendimento)}</td>
          <td>${escapeHtml(agendamento.cliente_nome)}</td>
          <td>${escapeHtml(agendamento.servico_nome)}</td>
          <td><span class="badge ${agendamento.status.toLowerCase()}">${escapeHtml(agendamento.status)}</span></td>
          <td>${escapeHtml(agendamento.administrador_nome || '-')}</td>
          <td>
            <div class="table-actions">
              <button class="btn btn-secondary btn-sm" onclick="editAgendamento(${agendamento.id})">Editar</button>
              <button class="btn btn-success btn-sm" onclick="changeAgendamentoStatus(${agendamento.id}, 'CONCLUIDO')">Concluir</button>
              <button class="btn btn-warning btn-sm" onclick="changeAgendamentoStatus(${agendamento.id}, 'CANCELADO')">Cancelar</button>
              <button class="btn btn-danger btn-sm" onclick="deleteAgendamento(${agendamento.id})">Excluir</button>
            </div>
          </td>
        </tr>
      `).join('')
    : '<tr><td colspan="7" class="muted">Nenhum agendamento encontrado.</td></tr>';
}

function populateSelects() {
  fillSelect(el.agendamentoCliente, state.clientes, 'Selecione um cliente', (item) => ({ value: item.id, label: item.nome }));
  fillSelect(
    el.agendamentoServico,
    state.servicos.filter((item) => Number(item.ativo) === 1 || String(el.agendamentoId.value || '').trim()),
    'Selecione um serviço',
    (item) => ({ value: item.id, label: `${item.nome} (${item.duracao_minutos} min)` })
  );
  fillSelect(el.agendamentoAdmin, state.administradores, 'Selecione um administrador', (item) => ({ value: item.id, label: item.nome }));
}

function fillSelect(select, items, placeholder, mapFn) {
  const currentValue = select.value;
  const options = [`<option value="">${placeholder}</option>`]
    .concat(items.map((item) => {
      const mapped = mapFn(item);
      return `<option value="${mapped.value}">${escapeHtml(mapped.label)}</option>`;
    }))
    .join('');
  select.innerHTML = options;
  if (items.some((item) => String(mapFn(item).value) === String(currentValue))) {
    select.value = currentValue;
  }
}

async function submitClienteForm(event) {
  event.preventDefault();
  const id = el.clienteId.value;
  const payload = {
    nome: el.clienteNome.value.trim(),
    telefone: el.clienteTelefone.value.trim(),
    observacoes: el.clienteObs.value.trim() || null,
  };

  try {
    if (id) {
      await apiRequest(`/clientes/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
      showToast('Cliente atualizado com sucesso.', 'success');
    } else {
      await apiRequest('/clientes', { method: 'POST', body: JSON.stringify(payload) });
      showToast('Cliente criado com sucesso.', 'success');
    }
    resetClienteForm();
    await loadClientes();
    await loadAgendamentos();
  } catch (error) {
    showToast(error.message, 'error');
  }
}

async function submitServicoForm(event) {
  event.preventDefault();
  const id = el.servicoId.value;
  const payload = {
    nome: el.servicoNome.value.trim(),
    duracao_minutos: Number(el.servicoDuracao.value),
    preco: el.servicoPreco.value ? Number(el.servicoPreco.value) : null,
    ativo: el.servicoAtivo.checked ? 1 : 0,
  };

  try {
    if (id) {
      await apiRequest(`/servicos/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
      showToast('Serviço atualizado com sucesso.', 'success');
    } else {
      await apiRequest('/servicos', { method: 'POST', body: JSON.stringify(payload) });
      showToast('Serviço criado com sucesso.', 'success');
    }
    resetServicoForm();
    await loadServicos();
    await loadAgendamentos();
  } catch (error) {
    showToast(error.message, 'error');
  }
}

async function submitAgendamentoForm(event) {
  event.preventDefault();
  const id = el.agendamentoId.value;
  const payload = {
    cliente_id: Number(el.agendamentoCliente.value),
    servico_id: Number(el.agendamentoServico.value),
    administrador_id: Number(el.agendamentoAdmin.value),
    data_atendimento: el.agendamentoData.value,
    horario_atendimento: el.agendamentoHora.value,
    observacoes: el.agendamentoObs.value.trim() || null,
  };

  if (id) {
    payload.status = el.agendamentoStatus.value;
  }

  try {
    if (id) {
      await apiRequest(`/agendamentos/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
      showToast('Agendamento atualizado com sucesso.', 'success');
    } else {
      await apiRequest('/agendamentos', { method: 'POST', body: JSON.stringify(payload) });
      showToast('Agendamento criado com sucesso.', 'success');
    }
    resetAgendamentoForm();
    await loadAgendamentos();
  } catch (error) {
    showToast(error.message, 'error');
  }
}

window.editCliente = function editCliente(id) {
  const cliente = state.clientes.find((item) => item.id === id);
  if (!cliente) return;
  setActiveSection('clientes');
  el.clienteFormTitle.textContent = `Editar cliente #${cliente.id}`;
  el.clienteId.value = cliente.id;
  el.clienteNome.value = cliente.nome || '';
  el.clienteTelefone.value = cliente.telefone || '';
  el.clienteObs.value = cliente.observacoes || '';
};

window.editServico = function editServico(id) {
  const servico = state.servicos.find((item) => item.id === id);
  if (!servico) return;
  setActiveSection('servicos');
  el.servicoFormTitle.textContent = `Editar serviço #${servico.id}`;
  el.servicoId.value = servico.id;
  el.servicoNome.value = servico.nome || '';
  el.servicoDuracao.value = servico.duracao_minutos || '';
  el.servicoPreco.value = servico.preco ?? '';
  el.servicoAtivo.checked = Number(servico.ativo) === 1;
};

window.editAgendamento = async function editAgendamento(id) {
  const agendamento = state.agendamentos.find((item) => item.id === id);
  if (!agendamento) return;
  setActiveSection('agendamentos');
  populateSelects();
  el.agendamentoFormTitle.textContent = `Editar agendamento #${agendamento.id}`;
  el.agendamentoId.value = agendamento.id;
  el.agendamentoCliente.value = String(agendamento.cliente_id);
  el.agendamentoServico.value = String(agendamento.servico_id);
  el.agendamentoAdmin.value = String(agendamento.administrador_id);
  el.agendamentoStatus.value = agendamento.status;
  el.agendamentoData.value = agendamento.data_atendimento;
  el.agendamentoHora.value = agendamento.horario_atendimento;
  el.agendamentoObs.value = agendamento.observacoes || '';
};

window.deleteCliente = async function deleteCliente(id) {
  if (!confirm('Deseja realmente excluir este cliente?')) return;
  try {
    await apiRequest(`/clientes/${id}`, { method: 'DELETE' });
    showToast('Cliente removido com sucesso.', 'success');
    await loadClientes();
    await loadAgendamentos();
  } catch (error) {
    showToast(error.message, 'error');
  }
};

window.deleteServico = async function deleteServico(id) {
  if (!confirm('Deseja realmente excluir este serviço?')) return;
  try {
    await apiRequest(`/servicos/${id}`, { method: 'DELETE' });
    showToast('Serviço removido com sucesso.', 'success');
    await loadServicos();
    await loadAgendamentos();
  } catch (error) {
    showToast(error.message, 'error');
  }
};

window.deleteAgendamento = async function deleteAgendamento(id) {
  if (!confirm('Deseja realmente excluir este agendamento?')) return;
  try {
    await apiRequest(`/agendamentos/${id}`, { method: 'DELETE' });
    showToast('Agendamento removido com sucesso.', 'success');
    await loadAgendamentos();
  } catch (error) {
    showToast(error.message, 'error');
  }
};

window.toggleServicoAtivo = async function toggleServicoAtivo(id, ativo) {
  try {
    await apiRequest(`/servicos/${id}/ativo`, {
      method: 'PATCH',
      body: JSON.stringify({ ativo }),
    });
    showToast('Status do serviço atualizado.', 'success');
    await loadServicos();
  } catch (error) {
    showToast(error.message, 'error');
  }
};

window.changeAgendamentoStatus = async function changeAgendamentoStatus(id, status) {
  try {
    await apiRequest(`/agendamentos/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
    showToast(`Status alterado para ${status}.`, 'success');
    await loadAgendamentos();
  } catch (error) {
    showToast(error.message, 'error');
  }
};

function resetClienteForm() {
  el.clienteForm.reset();
  el.clienteId.value = '';
  el.clienteFormTitle.textContent = 'Novo cliente';
}

function resetServicoForm() {
  el.servicoForm.reset();
  el.servicoId.value = '';
  el.servicoAtivo.checked = true;
  el.servicoFormTitle.textContent = 'Novo serviço';
}

function resetAgendamentoForm() {
  el.agendamentoForm.reset();
  el.agendamentoId.value = '';
  el.agendamentoStatus.value = 'AGENDADO';
  el.agendamentoFormTitle.textContent = 'Novo agendamento';
  el.agendamentoData.value = new Date().toISOString().split('T')[0];
  populateSelects();
}

function setActiveSection(sectionId) {
  document.querySelectorAll('.content-section').forEach((section) => section.classList.toggle('active', section.id === sectionId));
  document.querySelectorAll('.nav-link').forEach((link) => link.classList.toggle('active', link.dataset.section === sectionId));
  const title = sectionId.charAt(0).toUpperCase() + sectionId.slice(1);
  el.pageTitle.textContent = title;
}

function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  el.toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 3500);
}

function formatMoney(value) {
  if (value === null || value === undefined || value === '') return '—';
  return Number(value).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function formatDate(dateStr) {
  if (!dateStr) return '—';
  const [y, m, d] = dateStr.split('-');
  return `${d}/${m}/${y}`;
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}