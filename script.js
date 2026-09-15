const API_URL = window.location.protocol === 'file:' ? 'http://127.0.0.1:5000' : window.location.origin;
let toastTimer;

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.modal').forEach((modal) => {
        modal.addEventListener('click', (event) => {
            if (event.target === modal) fecharModal(modal.id);
        });
    });
    document.querySelectorAll('form').forEach((form) => form.addEventListener('submit', (event) => {
        event.preventDefault();
        const handlers = { formProfessor: cadastrarProfessor, formAluno: cadastrarAluno, formAtividade: cadastrarAtividade, formPresenca: lancarPresenca, formEdicao: salvarEdicao };
        handlers[form.id]?.();
    }));
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') document.querySelectorAll('.modal').forEach((modal) => fecharModal(modal.id));
    });
    carregarTabela();
    carregarCadastros();
    carregarRanking();
});

function abrirModal(idModal) {
    const modal = document.getElementById(idModal);
    if (!modal) return;
    modal.style.display = 'flex';
    modal.querySelector('input, select')?.focus();
}

function fecharModal(idModal) {
    const modal = document.getElementById(idModal);
    if (!modal) return;
    modal.style.display = 'none';
    modal.querySelector('form')?.reset();
    setFormLoading(modal.querySelector('form'), false);
}

function mostrarToast(mensagem, erro = false) {
    const toast = document.getElementById('toast');
    toast.textContent = mensagem;
    toast.classList.toggle('is-error', erro);
    toast.classList.add('is-visible');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('is-visible'), 4200);
}

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#039;', '"': '&quot;' })[char]);
}

function obterDataAtualFormatada() {
    const hoje = new Date();
    return `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, '0')}-${String(hoje.getDate()).padStart(2, '0')}`;
}

async function requisicao(endpoint, dados) {
    const response = await fetch(`${API_URL}${endpoint}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(dados) });
    const resultado = await response.json().catch(() => ({ erro: 'A API retornou uma resposta inválida.' }));
    if (!response.ok) throw new Error(resultado.erro || 'Não foi possível concluir a operação.');
    return resultado;
}

function setFormLoading(form, loading) {
    if (!form) return;
    const button = form.querySelector('button[type="submit"]');
    if (!button) return;
    if (!button.dataset.label) button.dataset.label = button.textContent;
    button.disabled = loading;
    button.textContent = loading ? 'Salvando...' : button.dataset.label;
}

async function carregarTabela() {
    const tabela = document.getElementById('corpoTabela');
    tabela.innerHTML = '<tr><td class="loading-state" colspan="7">Carregando relatório...</td></tr>';
    try {
        const response = await fetch(`${API_URL}/buscar_presencas`);
        const dados = await response.json();
        if (!response.ok) throw new Error(dados.erro || 'Não foi possível carregar o relatório.');
        atualizarResumo(dados);
        tabela.innerHTML = dados.length ? dados.map((linha) => `<tr><td>${escapeHtml(linha.data)}</td><td><strong>${escapeHtml(linha.atividade)}</strong></td><td><span class="status-badge status-${statusClasse(linha.status)}">${escapeHtml(linha.status)}</span></td><td>${escapeHtml(linha.professor)}</td><td class="present-names">${escapeHtml(linha.presentes_nomes)}</td><td><span class="badge-presente">${Number(linha.presentes) || 0}</span></td><td><span class="badge-ausente">${Number(linha.ausentes) || 0}</span></td></tr>`).join('') : '<tr><td class="empty-state" colspan="7">Nenhuma atividade cadastrada ainda.</td></tr>';
        document.getElementById('ultimaAtualizacao').textContent = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    } catch (error) {
        tabela.innerHTML = '<tr><td class="empty-state" colspan="7">Não foi possível carregar os dados.</td></tr>';
        document.querySelector('.status-dot').style.background = '#d05b4b';
        mostrarToast(error.message, true);
    }
}

function atualizarResumo(dados) {
    document.getElementById('totalAtividades').textContent = dados.length;
    document.getElementById('totalPresentes').textContent = dados.reduce((total, linha) => total + (Number(linha.presentes) || 0), 0);
}

function statusClasse(status) {
    return { 'Agendada': 'scheduled', 'Em andamento': 'running', 'Encerrada': 'closed' }[status] || 'scheduled';
}

async function buscarLista(endpoint) {
    const response = await fetch(`${API_URL}${endpoint}`);
    const dados = await response.json().catch(() => ({ erro: 'Resposta inválida da API.' }));
    if (!response.ok) throw new Error(dados.erro || 'Não foi possível carregar a lista.');
    return dados;
}

async function carregarCadastros() {
    try {
        const [alunos, professores, atividades] = await Promise.all([
            buscarLista('/listar_alunos'),
            buscarLista('/listar_professores'),
            buscarLista('/listar_atividades')
        ]);
        renderizarLista('listaAlunos', alunos, (aluno) => `<tr><td><button class="student-link" type="button" onclick="abrirDetalhesAluno(${aluno.id_pessoa}, ${aluno.id_cadastro})"><strong>${escapeHtml(aluno.nome_pessoa)}</strong><small class="row-subtitle">Ver histórico · ${aluno.id_pessoa}/${aluno.id_cadastro}</small></button></td><td>${aluno.idade ?? '--'} anos</td><td><button class="btn-edit" title="Editar aluno" onclick="abrirEdicao('aluno', ${aluno.id_pessoa}, ${aluno.id_cadastro}, '${escapeHtml(aluno.nome_pessoa)}', '${aluno.data_nascimento || ''}')">✎</button><button class="btn-delete" title="Excluir aluno" onclick="excluirRegistro('aluno', ${aluno.id_pessoa}, ${aluno.id_cadastro})">×</button></td></tr>`);
        renderizarLista('listaProfessores', professores, (professor) => `<tr><td><strong>${escapeHtml(professor.nome_professor)}</strong><small class="row-subtitle">ID ${professor.id_professor}</small></td><td>${professor.idade ?? '--'} anos</td><td><button class="btn-edit" title="Editar professor" onclick="abrirEdicao('professor', ${professor.id_professor}, null, '${escapeHtml(professor.nome_professor)}')">✎</button><button class="btn-delete" title="Excluir professor" onclick="excluirRegistro('professor', ${professor.id_professor})">×</button></td></tr>`);
        renderizarLista('listaAtividades', atividades, (atividade) => `<tr><td><strong>${escapeHtml(atividade.atividade)}</strong><small class="row-subtitle">${escapeHtml(atividade.data)} · ID ${atividade.id_atividade}</small></td><td><span class="status-badge status-${statusClasse(atividade.status)}">${escapeHtml(atividade.status)}</span>${atividade.status === 'Agendada' ? `<button class="btn-action" title="Iniciar atividade" onclick="alterarStatusAtividade('iniciar', ${atividade.id_atividade})">Iniciar</button>` : atividade.status === 'Em andamento' ? `<button class="btn-action btn-action-end" title="Encerrar atividade" onclick="alterarStatusAtividade('encerrar', ${atividade.id_atividade})">Encerrar</button>` : `<small class="row-subtitle">Fim: ${escapeHtml(atividade.data_fim || '--')}</small>`}</td><td><button class="btn-edit" title="Editar atividade" onclick="abrirEdicao('atividade', ${atividade.id_atividade}, null, '${escapeHtml(atividade.atividade)}', '${atividade.data_iso}', ${atividade.id_professor || 'null'}, '${escapeHtml(atividade.status)}')">✎</button><button class="btn-delete" title="Excluir atividade" onclick="excluirRegistro('atividade', ${atividade.id_atividade})">×</button></td></tr>`);
        preencherProfessores(professores);
        preencherCamposPresenca(alunos, atividades);
        document.getElementById('contadorAlunos').textContent = `${alunos.length} registro${alunos.length === 1 ? '' : 's'}`;
        document.getElementById('contadorProfessores').textContent = `${professores.length} registro${professores.length === 1 ? '' : 's'}`;
        document.getElementById('contadorAtividades').textContent = `${atividades.length} registro${atividades.length === 1 ? '' : 's'}`;
    } catch (error) {
        mostrarToast(error.message, true);
    }
}

function renderizarLista(id, dados, template) {
    const lista = document.getElementById(id);
    lista.innerHTML = dados.length ? dados.map(template).join('') : '<tr><td class="empty-state" colspan="3">Nenhum registro.</td></tr>';
}

function preencherProfessores(professores) {
    const select = document.getElementById('professorAtividade');
    if (!select) return;
    select.innerHTML = '<option value="">Sem professor definido</option>' + professores.map((professor) => `<option value="${professor.id_professor}">${escapeHtml(professor.nome_professor)} (#${professor.id_professor})</option>`).join('');
}

async function excluirRegistro(tipo, idPrincipal, idCadastro = null) {
    const nomes = { aluno: 'aluno', professor: 'professor', atividade: 'atividade' };
    if (!window.confirm(`Excluir este ${nomes[tipo]}? Os vínculos relacionados também serão removidos.`)) return;
    const dados = tipo === 'aluno' ? { id_pessoa: idPrincipal, id_cadastro: idCadastro } : tipo === 'professor' ? { id_professor: idPrincipal } : { id_atividade: idPrincipal };
    try {
        const response = await fetch(`${API_URL}/excluir_${tipo}`, { method: 'DELETE', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(dados) });
        const resultado = await response.json();
        if (!response.ok) throw new Error(resultado.erro || 'Não foi possível excluir o registro.');
        mostrarToast(resultado.mensagem);
        carregarCadastros();
        carregarTabela();
    } catch (error) {
        mostrarToast(error.message, true);
    }
}

async function cadastrarProfessor() {
    const form = document.getElementById('formProfessor');
    const dados = { id_professor: Number(document.getElementById('idProfessor').value), nome_professor: document.getElementById('nomeProfessor').value.trim(), data_nascimento: document.getElementById('dataNascimentoProfessor').value || null };
    if (!Number.isInteger(dados.id_professor) || dados.id_professor < 1 || !dados.nome_professor) return mostrarToast('Preencha o ID e o nome do professor.', true);
    await salvarFormulario(form, '/inserir_professor', dados, 'Professor cadastrado com sucesso!', 'modalProfessor');
}

async function cadastrarAluno() {
    const form = document.getElementById('formAluno');
    const dados = { id_pessoa: Number(document.getElementById('idPessoa').value), id_cadastro: Number(document.getElementById('idCadastro').value), nome_pessoa: document.getElementById('nomePessoa').value.trim(), data_nascimento: document.getElementById('dataNascimento').value || null, data_cadastro: obterDataAtualFormatada(), observacao: 'Cadastrado via Dashboard' };
    if (![dados.id_pessoa, dados.id_cadastro].every((id) => Number.isInteger(id) && id > 0) || !dados.nome_pessoa) return mostrarToast('Preencha os IDs e o nome do aluno.', true);
    await salvarFormulario(form, '/inserir_aluno', dados, 'Aluno cadastrado com sucesso!', 'modalAluno');
}

async function cadastrarAtividade() {
    const form = document.getElementById('formAtividade');
    const professorSelecionado = document.getElementById('professorAtividade').value;
    const dados = { id_atividade: Number(document.getElementById('idAtividadeForm').value), data_atividade: document.getElementById('dataAtividade').value, tipo_atividade: document.getElementById('tipoAtividade').value.trim(), id_professor: professorSelecionado ? Number(professorSelecionado) : null };
    if (!Number.isInteger(dados.id_atividade) || dados.id_atividade < 1 || !dados.data_atividade || !dados.tipo_atividade) return mostrarToast('Preencha todos os dados da atividade.', true);
    await salvarFormulario(form, '/inserir_atividade', dados, 'Atividade cadastrada com sucesso!', 'modalAtividade');
}

async function lancarPresenca() {
    const form = document.getElementById('formPresenca');
    const alunoSelecionado = document.getElementById('alunoPresenca').value.split('|');
    const dados = { status_presenca: document.getElementById('statusPresenca').value, fk_pessoa_id_pessoa: Number(alunoSelecionado[0]), fk_pessoa_id_cadastro: Number(alunoSelecionado[1]), fk_atividade_id_atividade: Number(document.getElementById('atividadePresenca').value) };
    if (alunoSelecionado.length !== 2 || ![dados.fk_pessoa_id_pessoa, dados.fk_pessoa_id_cadastro, dados.fk_atividade_id_atividade].every((id) => Number.isInteger(id) && id > 0)) return mostrarToast('Selecione o aluno e a atividade.', true);
    await salvarFormulario(form, '/inserir_presenca', dados, 'Presença registrada com sucesso!', 'modalPresenca', true);
}

async function salvarFormulario(form, endpoint, dados, sucesso, modalId, atualizar = false) {
    setFormLoading(form, true);
    try {
        await requisicao(endpoint, dados);
        mostrarToast(sucesso);
        fecharModal(modalId);
        carregarCadastros();
        carregarRanking();
        if (atualizar || endpoint === '/inserir_atividade') carregarTabela();
    } catch (error) {
        mostrarToast(error.message, true);
        setFormLoading(form, false);
    }
}

async function alterarStatusAtividade(acao, idAtividade) {
    const verbo = acao === 'iniciar' ? 'iniciar' : 'encerrar';
    if (!window.confirm(`Deseja ${verbo} esta atividade agora?`)) return;
    try {
        const response = await fetch(`${API_URL}/${acao}_atividade`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id_atividade: idAtividade }) });
        const resultado = await response.json();
        if (!response.ok) throw new Error(resultado.erro || `Não foi possível ${verbo} a atividade.`);
        mostrarToast(resultado.mensagem);
        carregarCadastros();
        carregarTabela();
    } catch (error) {
        mostrarToast(error.message, true);
    }
}

async function carregarRanking() {
    const tabela = document.getElementById('rankingAlunos');
    if (!tabela) return;
    try {
        const ranking = await buscarLista('/ranking_alunos');
        tabela.innerHTML = ranking.length ? ranking.map((aluno, indice) => `<tr><td><span class="rank-number">${indice + 1}</span></td><td><button class="student-link" type="button" onclick="abrirDetalhesAluno(${aluno.id_pessoa}, ${aluno.id_cadastro})"><strong>${escapeHtml(aluno.nome_pessoa)}</strong></button></td><td>${aluno.participacoes}</td><td>${aluno.atividades_encerradas}</td><td><span class="progress-value">${aluno.percentual ?? 0}%</span></td></tr>`).join('') : '<tr><td class="empty-state" colspan="5">Ainda não há atividades encerradas.</td></tr>';
    } catch (error) {
        tabela.innerHTML = '<tr><td class="empty-state" colspan="5">Não foi possível carregar o ranking.</td></tr>';
    }
}

async function abrirDetalhesAluno(idPessoa, idCadastro) {
    try {
        const aluno = await buscarLista(`/detalhes_aluno?id_pessoa=${idPessoa}&id_cadastro=${idCadastro}`);
        const historico = aluno.historico.length ? aluno.historico.map((item) => `<tr><td>${escapeHtml(item.data)}</td><td><strong>${escapeHtml(item.atividade)}</strong></td><td><span class="status-badge status-${item.presenca === 'Presente' ? 'running' : 'closed'}">${escapeHtml(item.presenca)}</span></td><td>${escapeHtml(item.status)}</td></tr>`).join('') : '<tr><td class="empty-state" colspan="4">Nenhuma participação registrada.</td></tr>';
        document.getElementById('detalhesAluno').innerHTML = `<p class="eyebrow">Perfil do aluno</p><h2>${escapeHtml(aluno.nome_pessoa)}</h2><div class="detail-facts"><div><span>ID pessoa</span><strong>${aluno.id_pessoa}</strong></div><div><span>RGM</span><strong>${aluno.id_cadastro}</strong></div><div><span>Idade</span><strong>${aluno.idade ?? '--'} anos</strong></div><div><span>Nascimento</span><strong>${escapeHtml(aluno.data_nascimento || 'Não informado')}</strong></div></div><h3 class="history-title">Histórico de atividades</h3><div class="table-responsive"><table><thead><tr><th>Data</th><th>Atividade</th><th>Presença</th><th>Status</th></tr></thead><tbody>${historico}</tbody></table></div>`;
        abrirModal('modalAlunoDetalhes');
    } catch (error) {
        mostrarToast(error.message, true);
    }
}

function preencherCamposPresenca(alunos, atividades) {
    const alunoSelect = document.getElementById('alunoPresenca');
    const atividadeSelect = document.getElementById('atividadePresenca');
    if (alunoSelect) {
        alunoSelect.innerHTML = '<option value="">Selecione o aluno</option>' + alunos.map((aluno) => `<option value="${aluno.id_pessoa}|${aluno.id_cadastro}">${escapeHtml(aluno.nome_pessoa)} · RGM ${aluno.id_cadastro}</option>`).join('');
    }
    if (atividadeSelect) {
        atividadeSelect.innerHTML = '<option value="">Selecione a atividade</option>' + atividades.filter((atividade) => atividade.status !== 'Encerrada').map((atividade) => `<option value="${atividade.id_atividade}">${escapeHtml(atividade.atividade)} · ${escapeHtml(atividade.data)}</option>`).join('');
    }
}

function abrirEdicao(tipo, idPrincipal, idCadastro, nome, dataExtra = '', idProfessor = null, status = 'Agendada') {
    const titulos = { aluno: 'Editar aluno', professor: 'Editar professor', atividade: 'Editar atividade' };
    document.getElementById('edicaoTipo').value = tipo;
    document.getElementById('edicaoIdPrincipal').value = idPrincipal;
    document.getElementById('edicaoIdCadastro').value = idCadastro || '';
    document.getElementById('nomeEdicao').value = nome;
    document.getElementById('tituloEdicao').textContent = titulos[tipo];
    document.getElementById('campoNascimentoEdicao').style.display = tipo === 'aluno' ? 'block' : 'none';
    document.getElementById('campoDataAtividadeEdicao').style.display = tipo === 'atividade' ? 'block' : 'none';
    document.getElementById('campoProfessorEdicao').style.display = tipo === 'atividade' ? 'block' : 'none';
    document.getElementById('dataNascimentoEdicao').value = tipo === 'aluno' ? dataExtra : '';
    document.getElementById('dataAtividadeEdicao').value = tipo === 'atividade' ? dataExtra : '';
    document.getElementById('professorEdicao').innerHTML = document.getElementById('professorAtividade').innerHTML;
    document.getElementById('professorEdicao').value = idProfessor || '';
    document.getElementById('statusEdicao').value = status;
    document.getElementById('campoStatusEdicao').style.display = tipo === 'atividade' ? 'block' : 'none';
    abrirModal('modalEdicao');
}

async function salvarEdicao() {
    const form = document.getElementById('formEdicao');
    const tipo = document.getElementById('edicaoTipo').value;
    const nome = document.getElementById('nomeEdicao').value.trim();
    const dados = tipo === 'aluno'
        ? { id_pessoa: Number(document.getElementById('edicaoIdPrincipal').value), id_cadastro: Number(document.getElementById('edicaoIdCadastro').value), nome, data_nascimento: document.getElementById('dataNascimentoEdicao').value || null }
        : tipo === 'professor'
            ? { id_professor: Number(document.getElementById('edicaoIdPrincipal').value), nome }
            : { id_atividade: Number(document.getElementById('edicaoIdPrincipal').value), nome, data_atividade: document.getElementById('dataAtividadeEdicao').value, id_professor: document.getElementById('professorEdicao').value ? Number(document.getElementById('professorEdicao').value) : null, status: document.getElementById('statusEdicao').value };
    if (!nome) return mostrarToast('Digite um nome válido.', true);
    setFormLoading(form, true);
    try {
        const response = await fetch(`${API_URL}/editar_${tipo}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(dados) });
        const resultado = await response.json();
        if (!response.ok) throw new Error(resultado.erro || 'Não foi possível salvar a alteração.');
        mostrarToast(resultado.mensagem);
        fecharModal('modalEdicao');
        carregarCadastros();
        carregarTabela();
    } catch (error) {
        mostrarToast(error.message, true);
        setFormLoading(form, false);
    }
}