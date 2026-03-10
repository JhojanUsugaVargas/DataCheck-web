let pendingAction = null;

// ── Theme Management ──
function toggleTheme() {
    const isLight = document.body.classList.toggle('light-mode');
    localStorage.setItem('theme', isLight ? 'light' : 'dark');
    document.getElementById('themeToggle').innerText = isLight ? '☀️' : '🌙';
}

function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'light') {
        document.body.classList.add('light-mode');
        document.getElementById('themeToggle').innerText = '☀️';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initTheme();

    // Hide loading overlay
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        setTimeout(() => {
            overlay.classList.add('hidden');
        }, 500);
    }
});

// ── Modal Utility Functions ──
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
        // Animación suave si se desea
        modal.classList.add('fade-in');
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
    }
}

// ── Sidebar Toggle (mobile) ──
function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('active');
}

// Close sidebar when clicking outside on mobile
document.addEventListener('click', (e) => {
    const sidebar = document.getElementById('sidebar');
    if (sidebar.classList.contains('active') &&
        !sidebar.contains(e.target) &&
        !e.target.classList.contains('menu-toggle')) {
        sidebar.classList.remove('active');
    }
});

// ── Logout ──
function confirmLogout() {
    document.getElementById('logoutModal').style.display = 'flex';
}

async function executeLogout() {
    await fetch(window.API_BASE + '/api/logout', { method: 'POST' });
    window.location.href = window.API_BASE + '/login';
}

// ── Send Action (sidebar buttons) ──
function sendAction(action) {
    // Close sidebar on mobile
    document.getElementById('sidebar').classList.remove('active');

    const actionLabels = {
        'status': '📊 Estado SQL Server',
        'bloqueos': '🔒 Bloqueos',
        'cancelar': '❌ Cancelar Consulta',
        'cpu': '⚙️ Monitor de Salud',
        'whoisactive': '👤 Sesiones Activas',
        'discos': '💾 Espacio en Discos',
        'datalog': '🕵️‍♂️ Validar Data y Log',
        'tempdb': '🧹 TempDB',
        'performance': '📈 Verificar Performance',
        'jobs': '📋 Validación de Jobs',
        'alwayson': '🔗 Always On Availability Groups',
        'databases': '🗄️ Bases de Datos',
        'soporte': '🆘 Solicitud de Soporte'
    };

    if (action === 'soporte') {
        openSoporteModal();
        return;
    }

    addMessage('user', actionLabels[action] || action);
    showTyping();
    callAPI(action, '');
}

// ── Send Message (from input) ──
function sendMessage() {
    const input = document.getElementById('chatInput');
    const text = input.value.trim();
    if (!text) return;

    input.value = '';

    addMessage('user', text);
    showTyping();

    if (pendingAction) {
        callAPI(pendingAction, text);
        pendingAction = null;
    } else {
        // Send as AI query
        callAPI(null, text);
    }
}

// ── API Call ──
async function callAPI(action, message) {
    try {
        const body = {};
        if (action) body.action = action;
        if (message) body.message = message;

        const res = await fetch(window.API_BASE + '/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        if (res.status === 401) {
            window.location.href = window.API_BASE + '/login';
            return;
        }

        const data = await res.json();
        removeTyping();
        renderResponse(data);
    } catch (err) {
        removeTyping();
        addBotMessage('❌ Error de conexión con el servidor.', 'error');
    }
}

// ── Render Response ──
function renderResponse(data) {
    switch (data.type) {
        case 'success':
        case 'info':
            addBotMessage(data.message);
            break;

        case 'error':
            addBotMessage(data.message, 'error');
            break;

        case 'table':
            renderTable(data.title, data.data);
            break;

        case 'metrics':
            renderMetrics(data.title, data.data);
            break;

        case 'instance_monitor':
            renderInstanceMonitor(data.title, data.data);
            break;

        case 'disk_monitor':
            renderDiskMonitor(data.title, data.data);
            break;

        case 'datalog_monitor':
            renderDataLogMonitor(data.title, data.data);
            break;

        case 'tempdb_monitor':
            renderTempDBMonitor(data.title, data.data);
            break;

        case 'server_uptime':
            renderServerUptime(data.title, data.data);
            break;

        case 'ai':
            addBotMessage(data.message, null, data.source);
            break;

        case 'prompt':
            addBotMessage(data.message);
            if (data.input_action) {
                pendingAction = data.input_action;
            } else {
                // For soporte, assume the next message is the support text
                pendingAction = 'soporte';
            }
            document.getElementById('chatInput').focus();
            break;

        default:
            addBotMessage(data.message || 'Respuesta recibida.');
    }
}

// ── Add Messages ──
function addMessage(type, text) {
    const container = document.getElementById('chatMessages');
    clearWelcome();

    const msgEl = document.createElement('div');
    msgEl.className = `message ${type}`;

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.textContent = type === 'user' ? '👤' : '🤖';

    const content = document.createElement('div');
    content.className = 'msg-content';
    content.innerHTML = formatText(text);

    msgEl.appendChild(avatar);
    msgEl.appendChild(content);
    container.appendChild(msgEl);
    scrollToBottom();
}

function addBotMessage(text, variant, source) {
    const container = document.getElementById('chatMessages');
    clearWelcome();

    const msgEl = document.createElement('div');
    msgEl.className = 'message bot';

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.textContent = '🤖';

    const content = document.createElement('div');
    content.className = 'msg-content';

    if (variant === 'error') {
        content.style.borderColor = 'rgba(239, 68, 68, 0.2)';
        content.style.background = 'rgba(239, 68, 68, 0.06)';
    }

    content.innerHTML = formatText(text);

    if (source) {
        const badge = document.createElement('span');
        badge.className = 'msg-source';
        badge.textContent = `⚡ ${source}`;
        content.appendChild(badge);
    }

    msgEl.appendChild(avatar);
    msgEl.appendChild(content);
    container.appendChild(msgEl);
    scrollToBottom();
}

// ── Render Table ──
function renderTable(title, data) {
    if (!data || data.length === 0) {
        addBotMessage('No se encontraron datos.');
        return;
    }

    const container = document.getElementById('chatMessages');
    clearWelcome();

    const msgEl = document.createElement('div');
    msgEl.className = 'message bot';

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.textContent = '🤖';

    const content = document.createElement('div');
    content.className = 'msg-content';
    content.style.maxWidth = '100%';
    content.style.overflow = 'auto';

    let html = `<strong>${title}</strong>`;

    const keys = Object.keys(data[0]);
    html += '<table class="msg-table"><thead><tr>';
    keys.forEach(k => { html += `<th>${k}</th>`; });
    html += '</tr></thead><tbody>';
    data.forEach(row => {
        html += '<tr>';
        keys.forEach(k => { html += `<td>${row[k] || '-'}</td>`; });
        html += '</tr>';
    });
    html += '</tbody></table>';

    content.innerHTML = html;
    msgEl.appendChild(avatar);
    msgEl.appendChild(content);
    container.appendChild(msgEl);
    scrollToBottom();
}

// ── Render Server Uptime (Premium Cards) ──
function renderServerUptime(title, data) {
    const container = document.getElementById('chatMessages');
    clearWelcome();

    const msgEl = document.createElement('div');
    msgEl.className = 'message bot';

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.textContent = '🤖';

    const content = document.createElement('div');
    content.className = 'msg-content uptime-card';

    const hoursRemaining = data.horas_activo % 24;
    const uptimeLabel = data.dias_activo > 0
        ? `${data.dias_activo} días ${hoursRemaining} hrs`
        : `${data.horas_activo} horas`;

    content.innerHTML = `
        <div class="uptime-header">
            <span class="uptime-status-dot"></span>
            <span class="uptime-online-label">✅ En Línea</span>
        </div>
        <div class="uptime-server-name">
            <span class="uptime-server-icon">🖥️</span>
            <span>${data.servidor}</span>
        </div>
        <div class="uptime-metrics">
            <div class="uptime-metric">
                <div class="uptime-value">${data.dias_activo}</div>
                <div class="uptime-label">Días Activo</div>
            </div>
            <div class="uptime-metric">
                <div class="uptime-value">${hoursRemaining}</div>
                <div class="uptime-label">Horas Restantes</div>
            </div>
            <div class="uptime-metric">
                <div class="uptime-value">${data.horas_activo}</div>
                <div class="uptime-label">Horas Totales</div>
            </div>
        </div>
        <div class="uptime-footer">
            <span class="uptime-footer-label">⏰ Inicio del Servicio</span>
            <span class="uptime-footer-value">${data.fecha_inicio.split('.')[0]}</span>
        </div>
    `;

    msgEl.appendChild(avatar);
    msgEl.appendChild(content);
    container.appendChild(msgEl);
    scrollToBottom();
}

// ── Render Metrics (legacy) ──
function renderMetrics(title, data) {
    const container = document.getElementById('chatMessages');
    clearWelcome();

    const msgEl = document.createElement('div');
    msgEl.className = 'message bot';

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.textContent = '🤖';

    const content = document.createElement('div');
    content.className = 'msg-content';
    content.style.minWidth = '300px';

    const cpuColor = data.cpu_percent > 80 ? '#ef4444' : data.cpu_percent > 50 ? '#f59e0b' : '#10b981';
    const memColor = data.mem_percent > 80 ? '#ef4444' : data.mem_percent > 50 ? '#f59e0b' : '#10b981';

    content.innerHTML = `
        <strong>${title}</strong>
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value" style="color:${cpuColor}">${data.cpu_percent}%</div>
                <div class="metric-label">CPU</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" style="color:${memColor}">${data.mem_percent}%</div>
                <div class="metric-label">Memoria</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">${data.cpu_cores}</div>
                <div class="metric-label">Núcleos</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">${data.cpu_threads}</div>
                <div class="metric-label">Hilos</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">${data.mem_used_gb}</div>
                <div class="metric-label">RAM Usada (GB)</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">${data.mem_total_gb}</div>
                <div class="metric-label">RAM Total (GB)</div>
            </div>
        </div>
    `;

    msgEl.appendChild(avatar);
    msgEl.appendChild(content);
    container.appendChild(msgEl);
    scrollToBottom();
}

// ── Render Instance Monitor (enhanced dashboard) ──
function renderInstanceMonitor(title, data) {
    const container = document.getElementById('chatMessages');
    clearWelcome();

    const msgEl = document.createElement('div');
    msgEl.className = 'message bot';

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.textContent = '🤖';

    const content = document.createElement('div');
    content.className = 'msg-content monitor-dashboard';

    // Color helpers
    const cpuColor = data.sql_cpu_percent > 80 ? '#ef4444' : data.sql_cpu_percent > 50 ? '#f59e0b' : '#10b981';
    const memColor = data.sql_mem_usage_percent > 80 ? '#ef4444' : data.sql_mem_usage_percent > 50 ? '#f59e0b' : '#10b981';
    const cpuOtherColor = '#8b5cf6';
    const cpuIdleColor = 'rgba(99, 102, 241, 0.15)';

    // Donut SVG for CPU
    const sqlAngle = (data.sql_cpu_percent / 100) * 360;
    const otherAngle = (data.cpu_other / 100) * 360;
    const sqlDash = (data.sql_cpu_percent / 100) * 251.2;
    const otherDash = (data.cpu_other / 100) * 251.2;
    const sqlOffset = 0;
    const otherOffset = -sqlDash;

    content.innerHTML = `
        <div class="monitor-header">
            <span class="monitor-title">${title}</span>
            <span class="monitor-timestamp">${data.fecha}</span>
        </div>

        <div class="monitor-grid">
            <!-- CPU Section -->
            <div class="monitor-section cpu-section">
                <div class="section-label">🖥️ CPU</div>
                <div class="cpu-donut-container">
                    <svg class="cpu-donut" viewBox="0 0 100 100">
                        <!-- Background circle -->
                        <circle cx="50" cy="50" r="40" fill="none" stroke="${cpuIdleColor}" stroke-width="8"/>
                        <!-- Other processes -->
                        <circle cx="50" cy="50" r="40" fill="none" stroke="${cpuOtherColor}" stroke-width="8"
                            stroke-dasharray="${otherDash} ${251.2 - otherDash}"
                            stroke-dashoffset="${otherOffset}"
                            transform="rotate(-90 50 50)"
                            class="donut-segment"/>
                        <!-- SQL Server -->
                        <circle cx="50" cy="50" r="40" fill="none" stroke="${cpuColor}" stroke-width="8"
                            stroke-dasharray="${sqlDash} ${251.2 - sqlDash}"
                            stroke-dashoffset="0"
                            transform="rotate(-90 50 50)"
                            class="donut-segment"/>
                        <text x="50" y="46" text-anchor="middle" class="donut-percent" fill="${cpuColor}">${data.sql_cpu_percent}%</text>
                        <text x="50" y="58" text-anchor="middle" class="donut-label" fill="currentColor">SQL</text>
                    </svg>
                </div>
                <div class="cpu-legend">
                    <div class="legend-item">
                        <span class="legend-dot" style="background:${cpuColor}"></span>
                        <span class="legend-text">SQL Server: ${data.sql_cpu_percent}%</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-dot" style="background:${cpuOtherColor}"></span>
                        <span class="legend-text">Otros: ${data.cpu_other}%</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-dot" style="background:rgba(99,102,241,0.3)"></span>
                        <span class="legend-text">Libre: ${data.cpu_idle}%</span>
                    </div>
                </div>
            </div>

            <!-- Memory Section -->
            <div class="monitor-section mem-section">
                <div class="section-label">🧠 Memoria del Servidor</div>
                <div class="mem-bar-container">
                    <div class="mem-bar-bg">
                        <div class="mem-bar-fill" style="width:${data.sql_mem_usage_percent}%; background:${memColor}"></div>
                    </div>
                    <div class="mem-bar-label">
                        <span style="color:${memColor}; font-weight:700; font-size:20px;">${data.sql_mem_usage_percent}%</span>
                    </div>
                </div>
                <div class="mem-details">
                    <div class="mem-detail-item">
                        <span class="mem-detail-value">${data.sql_mem_used_mb.toLocaleString()}</span>
                        <span class="mem-detail-label">En uso (SQL)</span>
                    </div>
                    <div class="mem-detail-item">
                        <span class="mem-detail-value">${data.sql_max_mem_mb.toLocaleString()}</span>
                        <span class="mem-detail-label">Total Servidor</span>
                    </div>
                    <div class="mem-detail-item">
                        <span class="mem-detail-value">${data.sql_mem_free_mb.toLocaleString()}</span>
                        <span class="mem-detail-label">Libre Servidor</span>
                    </div>
                </div>
            </div>

            <!-- Activity Section -->
            <div class="monitor-section activity-section">
                <div class="section-label">📊 Actividad</div>
                <div class="activity-cards">
                    <div class="activity-card">
                        <div class="activity-icon" style="background:rgba(16,185,129,0.12); color:#10b981">▶</div>
                        <div class="activity-info">
                            <div class="activity-value">${data.sessions_running}</div>
                            <div class="activity-label">Ejecutando</div>
                        </div>
                    </div>
                    <div class="activity-card">
                        <div class="activity-icon" style="background:rgba(99,102,241,0.12); color:#818cf8">👤</div>
                        <div class="activity-info">
                            <div class="activity-value">${data.sessions_user}</div>
                            <div class="activity-label">Sesiones Usuario</div>
                        </div>
                    </div>
                    <div class="activity-card">
                        <div class="activity-icon" style="background:rgba(245,158,11,0.12); color:#f59e0b">⚡</div>
                        <div class="activity-info">
                            <div class="activity-value">${data.requests_active}</div>
                            <div class="activity-label">Requests Activas</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    msgEl.appendChild(avatar);
    msgEl.appendChild(content);
    container.appendChild(msgEl);
    scrollToBottom();
}

// ── Helpers ──
function formatText(text) {
    // Bold **text**
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Newlines
    text = text.replace(/\n/g, '<br>');
    return text;
}

function showTyping() {
    const container = document.getElementById('chatMessages');
    const typing = document.createElement('div');
    typing.className = 'message bot';
    typing.id = 'typingIndicator';

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.textContent = '🤖';

    const content = document.createElement('div');
    content.className = 'msg-content';
    content.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';

    typing.appendChild(avatar);
    typing.appendChild(content);
    container.appendChild(typing);
    scrollToBottom();
}

function removeTyping() {
    const typing = document.getElementById('typingIndicator');
    if (typing) typing.remove();
}

function clearWelcome() {
    const welcome = document.querySelector('.welcome-card');
    if (welcome) welcome.remove();
}

function scrollToBottom() {
    const container = document.getElementById('chatMessages');
    setTimeout(() => {
        container.scrollTop = container.scrollHeight;
    }, 50);
}

// ── Profile Modal Logic ──
function openProfileModal() {
    document.getElementById('profileModal').style.display = 'flex';
}

function closeModal(id) {
    document.getElementById(id).style.display = 'none';
}

function previewPhoto(event) {
    const reader = new FileReader();
    reader.onload = function () {
        const preview = document.getElementById('modalAvatarPreview');
        preview.src = reader.result;
        preview.style.display = 'block';
    }
    reader.readAsDataURL(event.target.files[0]);
}

async function updateProfile(e) {
    e.preventDefault();
    const btn = document.getElementById('profileSaveBtn');
    const fullName = document.getElementById('profileFullName').value;
    const password = document.getElementById('profilePassword').value;
    const photoFile = document.getElementById('profilePhoto').files[0];

    btn.disabled = true;
    btn.textContent = 'Guardando...';

    try {
        // 1. Update basic info
        const res = await fetch(window.API_BASE + '/api/profile/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ full_name: fullName, password: password })
        });
        const data = await res.json();

        if (!data.success) {
            alert('Error al actualizar perfil: ' + data.error);
            return;
        }

        // 2. Update photo if selected
        if (photoFile) {
            const formData = new FormData();
            formData.append('photo', photoFile);

            const photoRes = await fetch(window.API_BASE + '/api/profile/photo', {
                method: 'POST',
                body: formData
            });
            const photoData = await photoRes.json();
            if (!photoData.success) {
                alert('Error al subir foto: ' + photoData.error);
            }
        }

        alert('Perfil actualizado correctamente.');
        location.reload();
    } catch (err) {
        alert('Error de conexión');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Guardar Cambios';
    }
}

// ── Admin Modal Logic ──
async function openAdminModal() {
    document.getElementById('adminModal').style.display = 'flex';
    loadUsers();
}

async function loadUsers() {
    try {
        const res = await fetch(window.API_BASE + '/api/admin/users');
        const users = await res.json();
        const tbody = document.getElementById('usersTableBody');
        tbody.innerHTML = '';

        users.forEach(u => {
            const tr = document.createElement('tr');

            const mfaStatus = u.mfa_enabled ? '✅' : '❌';
            const isActive = u.is_active !== undefined ? u.is_active : true;
            const statusClass = isActive ? '' : 'style="opacity: 0.5; background: rgba(239, 68, 68, 0.1);"';
            const toggleIcon = isActive ? '🚫' : '✅';
            const toggleTitle = isActive ? 'Inactivar' : 'Activar';

            tr.innerHTML = `
                <td ${statusClass}>${u.username}</td>
                <td ${statusClass}>${u.full_name}</td>
                <td ${statusClass}><span class="role-badge role-${u.role.toLowerCase()}">${u.role}</span></td>
                <td ${statusClass} style="text-align: center;">${mfaStatus}</td>
                <td>
                    <div style="display: flex; gap: 5px; justify-content: flex-start;">
                        <button class="quick-btn" title="Renombrar" style="padding: 4px; border: none; background: transparent; font-size: 14px;" onclick="renameUser('${u.username}', '${u.full_name}')">✏️</button>
                        <button class="quick-btn" title="Resetear Password" style="padding: 4px; border: none; background: transparent; font-size: 14px;" onclick="resetPassword('${u.username}')">🔑</button>
                        <button class="quick-btn" title="${toggleTitle}" style="padding: 4px; border: none; background: transparent; font-size: 14px;" onclick="toggleUserStatus('${u.username}', ${!isActive})">${toggleIcon}</button>
                        <button class="quick-btn" title="Eliminar" style="padding: 4px; border: none; background: transparent; font-size: 14px;" onclick="deleteUser('${u.username}')">🗑️</button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error('Error cargando usuarios:', err);
    }
}

async function resetPassword(username) {
    const newPassword = prompt(`Ingresa la nueva contraseña para ${username}:`);
    if (!newPassword) return;

    try {
        const res = await fetch(window.API_BASE + '/api/admin/users/reset_password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: username, password: newPassword })
        });
        const data = await res.json();
        if (data.success) {
            alert(data.message);
        } else {
            alert('Error: ' + data.error);
        }
    } catch (err) {
        alert('Error de conexión');
    }
}

async function addUser(e) {
    e.preventDefault();
    const btn = document.getElementById('addUserBtn');
    const data = {
        username: document.getElementById('newUsername').value,
        full_name: document.getElementById('newFullName').value,
        password: document.getElementById('newPassword').value,
        role: document.getElementById('newRole').value
    };

    btn.disabled = true;
    try {
        const res = await fetch(window.API_BASE + '/api/admin/users/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await res.json();
        if (result.success) {
            alert('Usuario creado correctamente');
            document.getElementById('addUserForm').reset();
            loadUsers();
        } else {
            alert('Error: ' + result.error);
        }
    } catch (err) {
        alert('Error de conexión');
    } finally {
        btn.disabled = false;
    }
}

// ── MFA Setup Logic ──
async function setupMFA() {
    try {
        const res = await fetch(window.API_BASE + '/api/mfa/setup');
        const data = await res.json();

        if (data.success) {
            document.getElementById('mfaSetupContainer').style.display = 'none';
            document.getElementById('mfaQRContainer').style.display = 'block';
            document.getElementById('mfaQRCode').src = data.qr_code;
        } else {
            alert('Error al iniciar configuración de MFA');
        }
    } catch (err) {
        alert('Error de conexión');
    }
}

function validateMFAInput() {
    const token = document.getElementById('mfaConfirmToken').value.trim();
    const btn = document.getElementById('mfaActivateBtn');
    if (token.length === 6 && /^\d+$/.test(token)) {
        btn.disabled = false;
        btn.style.opacity = '1';
    } else {
        btn.disabled = true;
        btn.style.opacity = '0.5';
    }
}

function cancelMFASetup() {
    document.getElementById('mfaQRContainer').style.display = 'none';
    const setupContainer = document.getElementById('mfaSetupContainer');
    const enabledContainer = document.getElementById('mfaEnabledContainer');
    if (setupContainer) setupContainer.style.display = 'block';
    else if (enabledContainer) enabledContainer.style.display = 'block';
}

async function activateMFA() {
    const token = document.getElementById('mfaConfirmToken').value.trim();
    const btn = document.getElementById('mfaActivateBtn');

    if (!token || token.length !== 6) {
        alert('Por favor ingresa un código válido de 6 dígitos');
        return;
    }

    btn.disabled = true;
    btn.textContent = 'Verificando...';

    try {
        const res = await fetch(window.API_BASE + '/api/mfa/activate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: token })
        });
        const data = await res.json();

        if (data.success) {
            alert('¡MFA activado correctamente!');
            location.reload();
        } else {
            alert('Error de validación: ' + (data.error || 'El código ingresado es incorrecto o ha expirado.'));
            btn.disabled = false;
            btn.textContent = 'Verificar y Activar';
        }
    } catch (err) {
        alert('Error de conexión con el servidor móvil.');
        btn.disabled = false;
        btn.textContent = 'Verificar y Activar';
    }
}

// ── Render Disk Monitor ──
function renderDiskMonitor(title, data) {
    if (!data || data.length === 0) {
        addBotMessage('No se encontraron datos de discos.');
        return;
    }

    const container = document.getElementById('chatMessages');
    clearWelcome();

    const msgEl = document.createElement('div');
    msgEl.className = 'message bot';

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.textContent = '🤖';

    const content = document.createElement('div');
    content.className = 'msg-content monitor-dashboard';

    let disksHtml = `<div class="monitor-header"><span class="monitor-title">${title}</span></div>`;
    disksHtml += `<div style="padding: 15px; display: grid; gap: 12px;">`;

    data.forEach(d => {
        const freePct = parseFloat(d.FreePct);
        const totalGB = parseFloat(d.TotalGB);
        const usedGB = parseFloat(d.UsedGB);
        const freeGB = parseFloat(d.FreeGB);
        const usedPct = 100 - freePct;

        // Color based on free space
        const barColor = freePct < 10 ? '#ef4444' : freePct < 20 ? '#f59e0b' : '#10b981';

        disksHtml += `
            <div class="monitor-section" style="padding: 12px; border-radius: 10px; background: rgba(255,255,255,0.03); border: 1px solid var(--border-subtle);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-weight: 700; color: var(--text-primary); font-size: 15px;">Unidad ${d.Drive}</span>
                    <span style="font-size: 12px; color: ${barColor}; font-weight: 600;">${freePct}% Libre</span>
                </div>
                
                <div class="mem-bar-container" style="height: 10px; margin-bottom: 12px;">
                    <div class="mem-bar-bg" style="height: 10px; border-radius: 5px;">
                        <div class="mem-bar-fill" style="width: ${usedPct}%; background: ${barColor}; height: 10px; border-radius: 5px;"></div>
                    </div>
                </div>

                <div class="mem-details" style="grid-template-columns: 1fr 1fr 1fr; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 8px;">
                    <div class="mem-detail-item">
                        <span class="mem-detail-value" style="font-size: 14px;">${totalGB}</span>
                        <span class="mem-detail-label">Total (GB)</span>
                    </div>
                    <div class="mem-detail-item">
                        <span class="mem-detail-value" style="font-size: 14px;">${usedGB}</span>
                        <span class="mem-detail-label">Usado (GB)</span>
                    </div>
                    <div class="mem-detail-item">
                        <span class="mem-detail-value" style="font-size: 14px; color: ${barColor}">${freeGB}</span>
                        <span class="mem-detail-label">Libre (GB)</span>
                    </div>
                </div>
            </div>
        `;
    });

    disksHtml += `</div>`;

    content.innerHTML = disksHtml;
    msgEl.appendChild(avatar);
    msgEl.appendChild(content);
    container.appendChild(msgEl);
    scrollToBottom();
}

// ── Render DataLog Monitor ──
function renderDataLogMonitor(title, data) {
    if (!data || data.length === 0) {
        addBotMessage('No se encontraron datos de archivos.');
        return;
    }

    const container = document.getElementById('chatMessages');
    clearWelcome();

    const msgEl = document.createElement('div');
    msgEl.className = 'message bot';

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.textContent = '🤖';

    const content = document.createElement('div');
    content.className = 'msg-content monitor-dashboard';

    let html = `<div class="monitor-header"><span class="monitor-title">${title}</span></div>`;
    html += `<div style="padding: 15px; display: grid; gap: 15px;">`;

    // Group by Database
    const grouped = {};
    data.forEach(d => {
        if (!grouped[d.DatabaseName]) grouped[d.DatabaseName] = [];
        grouped[d.DatabaseName].push(d);
    });

    Object.keys(grouped).forEach(dbName => {
        const files = grouped[dbName];
        html += `
            <div class="monitor-section" style="padding: 12px; border-radius: 12px; background: rgba(255,255,255,0.03); border: 1px solid var(--border-subtle);">
                <div style="font-weight: 700; color: var(--accent-light); font-size: 15px; margin-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 5px;">
                    🗄️ ${dbName}
                </div>
                <div style="display: grid; gap: 10px;">
        `;

        files.forEach(f => {
            const isLog = f.FileType === 'LOG';
            const icon = isLog ? '📝' : '📊';
            const color = isLog ? '#f59e0b' : '#3b82f6';

            html += `
                <div style="font-size: 13px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                        <span style="color: var(--text-primary); font-family: var(--font-mono);">${icon} ${f.FileType}</span>
                        <span style="font-weight: 600; color: ${color};">${f.SizeMB} MB</span>
                    </div>
                    <div style="padding: 6px 10px; background: rgba(0,0,0,0.2); border-radius: 6px; font-family: var(--font-mono); font-size: 11px; color: var(--text-secondary); word-break: break-all; border: 1px solid rgba(255,255,255,0.03);">
                        ${f.PhysicalPath}
                    </div>
                </div>
            `;
        });

        html += `</div></div>`;
    });

    html += `</div>`;

    content.innerHTML = html;
    msgEl.appendChild(avatar);
    msgEl.appendChild(content);
    container.appendChild(msgEl);
    scrollToBottom();
}

// ── Render TempDB Monitor ──
function renderTempDBMonitor(title, data) {
    if (!data) {
        addBotMessage('No se encontraron datos de TempDB.');
        return;
    }

    const container = document.getElementById('chatMessages');
    clearWelcome();

    const msgEl = document.createElement('div');
    msgEl.className = 'message bot';

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.textContent = '🤖';

    const content = document.createElement('div');
    content.className = 'msg-content monitor-dashboard';

    let html = `<div class="monitor-header"><span class="monitor-title">${title}</span></div>`;
    html += `<div style="padding: 15px; display: grid; gap: 20px;">`;

    // 1. Files Section
    html += `
        <div class="monitor-section">
            <div style="font-weight: 700; color: var(--accent-light); font-size: 14px; margin-bottom: 10px; display: flex; align-items: center; gap: 8px;">
                📁 Archivos Físicos
            </div>
            <div style="display: grid; gap: 8px;">
    `;
    data.files.forEach(f => {
        html += `
            <div style="padding: 10px; background: rgba(255,255,255,0.03); border: 1px solid var(--border-subtle); border-radius: 8px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="font-weight: 600; font-size: 13px;">${f.name}</span>
                    <span style="color: var(--cyan); font-weight: 700; font-size: 13px;">${f.size} MB</span>
                </div>
                <div style="font-size: 10px; color: var(--text-muted); font-family: var(--font-mono); word-break: break-all;">${f.path}</div>
            </div>
        `;
    });
    html += `</div></div>`;

    // 2. Sessions Section
    html += `
        <div class="monitor-section">
            <div style="font-weight: 700; color: var(--accent-light); font-size: 14px; margin-bottom: 10px; display: flex; align-items: center; gap: 8px;">
                👤 Uso por Sesiones Activas
            </div>
    `;

    if (data.active_sessions.length === 0) {
        html += `<div style="font-size: 12px; color: var(--text-muted); text-align: center; padding: 10px;">No hay sesiones de usuario usando TempDB actualmente.</div>`;
    } else {
        html += `<div style="display: grid; gap: 10px;">`;
        data.active_sessions.forEach(s => {
            html += `
                <div style="padding: 10px; background: rgba(99, 102, 241, 0.05); border: 1px solid rgba(99, 102, 241, 0.2); border-radius: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="font-weight: 700; color: var(--text-primary);">SID: ${s.sid} (${s.login})</span>
                        <span style="background: var(--accent); color: white; padding: 2px 8px; border-radius: 4px; font-size: 10px;">${s.status}</span>
                    </div>
                    <div style="display: flex; gap: 15px; margin-bottom: 8px; font-size: 12px;">
                        <span>📦 User: <strong style="color: var(--cyan);">${s.user_mb} MB</strong></span>
                        <span>⚙️ Internal: <strong style="color: var(--yellow);">${s.internal_mb} MB</strong></span>
                    </div>
                    <div style="padding: 8px; background: rgba(0,0,0,0.3); border-radius: 6px; font-family: var(--font-mono); font-size: 11px; color: var(--text-secondary); max-height: 60px; overflow-y: auto; border: 1px solid rgba(255,255,255,0.05);">
                        ${s.query}
                    </div>
                </div>
            `;
        });
        html += `</div>`;
    }
    html += `</div>`;

    html += `</div>`;

    content.innerHTML = html;
    msgEl.appendChild(avatar);
    msgEl.appendChild(content);
    container.appendChild(msgEl);
    scrollToBottom();
}

// ── Inactivity Timeout Logic ──
// Configurable: 15 minutes = 15 * 60 * 1000 ms
const INACTIVITY_TIMEOUT = 15 * 60 * 1000;
let inactivityTimer;

function resetInactivityTimer() {
    clearTimeout(inactivityTimer);
    inactivityTimer = setTimeout(async () => {
        // Perform silent logout
        await fetch(window.API_BASE + '/api/logout', { method: 'POST' });
        // Show timeout modal
        document.getElementById('timeoutModal').style.display = 'flex';
    }, INACTIVITY_TIMEOUT);
}

// Events to track activity
const activityEvents = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart'];
activityEvents.forEach(event => {
    document.addEventListener(event, resetInactivityTimer, true);
});

// Initial start
resetInactivityTimer();

// ── Multi-Contract Hierarchy Logic ──
async function loadInstances() {
    const contractId = document.getElementById('contractSelector').value;
    const instanceSelector = document.getElementById('instanceSelector');

    // Clear current instances
    instanceSelector.innerHTML = '<option value="">Cargando...</option>';

    try {
        const res = await fetch(window.API_BASE + `/api/instances?contract_id=${contractId}`);
        const instances = await res.json();

        instanceSelector.innerHTML = '';
        if (instances.length === 0) {
            instanceSelector.innerHTML = '<option value="">Sin instancias</option>';
        } else {
            instances.forEach(inst => {
                const opt = document.createElement('option');
                opt.value = inst.id;
                opt.textContent = inst.name;
                instanceSelector.appendChild(opt);
            });
            // Pre-seleccionar si corresponde
            if (window.currentInstanceId) {
                instanceSelector.value = window.currentInstanceId;
                window.currentInstanceId = null;
            }
            // No forzar changeInstance() automáticamente en carga inicial
            // Solo cambiar si el usuario interactúa (via onchange en el select)
        }
    } catch (err) {
        console.error('Error loading instances:', err);
        instanceSelector.innerHTML = '<option value="">Error al cargar</option>';
    }
}

async function changeInstance() {
    const instanceId = document.getElementById('instanceSelector').value;
    if (!instanceId) return;

    try {
        const res = await fetch(window.API_BASE + '/api/instances/select', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ instance_id: parseInt(instanceId) })
        });
        const data = await res.json();

        if (data.success) {
            // Recargar la página para reflejar la nueva instancia
            location.reload();
        } else {
            addBotMessage(`⚠️ ${data.message || 'Error al cambiar instancia'}`, 'error');
        }
    } catch (err) {
        console.error('Error changing instance:', err);
        addBotMessage('❌ Error de conexión al cambiar instancia.', 'error');
    }
}

// ── Admin: Contract & Instance Management ──
function openAddContractModal() {
    console.log("Opening Add Contract Modal");
    openModal('addContractModal');
}

function openAddInstanceModal() {
    console.log("Opening Add Instance Modal");
    const currentContractId = document.getElementById('contractSelector').value;
    const parentSelect = document.getElementById('instanceParentContract');
    if (parentSelect && currentContractId) {
        parentSelect.value = currentContractId;
    }
    openModal('addInstanceModal');
}

async function addContract(e) {
    e.preventDefault();
    const name = document.getElementById('newContractName').value;

    try {
        const res = await fetch(window.API_BASE + '/api/contracts/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        const data = await res.json();
        if (data.success) {
            alert('Contrato creado exitosamente');
            location.reload();
        } else {
            alert('Error: ' + data.message);
        }
    } catch (err) {
        console.error(err);
    }
}

async function addInstance(e) {
    e.preventDefault();
    const contract_id = parseInt(document.getElementById('instanceParentContract').value);
    const name = document.getElementById('newInstanceName').value;
    const conn_str = document.getElementById('newInstanceConn').value;

    try {
        const res = await fetch(window.API_BASE + '/api/instances/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ contract_id, name, conn_str })
        });
        const data = await res.json();
        if (data.success) {
            alert('Instancia creada exitosamente');
            location.reload();
        } else {
            alert('Error: ' + data.message);
        }
    } catch (err) {
        console.error(err);
    }
}

// ── Focus input on load ──
document.getElementById('chatInput').focus();

async function renameUser(username, currentName) {
    const newName = prompt(`Escribe el nuevo nombre para el usuario ${username}:`, currentName);
    if (!newName || newName === currentName) return;

    try {
        const res = await fetch(window.API_BASE + '/api/admin/users/rename', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ old_username: username, new_username: newName })
        });
        const data = await res.json();
        if (data.success) {
            alert(data.message);
            loadUsers();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (err) {
        alert('Error de conexión');
    }
}

async function toggleUserStatus(username, targetStatus) {
    if (!confirm(`¿Seguro que deseas cambiar el estado del usuario ${username}?`)) return;

    try {
        const res = await fetch(window.API_BASE + '/api/admin/users/toggle_status', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: username, is_active: targetStatus })
        });
        const data = await res.json();
        if (data.success) {
            loadUsers();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (err) {
        alert('Error de conexión');
    }
}

async function deleteUser(username) {
    if (!confirm(`⚠️ ATENCIÓN: ¿Estás ABSOLUTAMENTE SEGURO de eliminar al usuario ${username}? Esta acción no se puede deshacer.`)) return;

    try {
        const res = await fetch(window.API_BASE + `/api/admin/users/delete?username=${username}`, {
            method: 'DELETE'
        });
        const data = await res.json();
        if (data.success) {
            alert(data.message);
            loadUsers();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (err) {
        alert('Error de conexión');
    }
}

// ── Feedback Logic ──
function openFeedbackModal() {
    openModal('feedbackModal');
    resetFeedback();
}

function resetFeedback() {
    document.getElementById('feedbackSuggestion').value = '';
    const stars = document.querySelectorAll('.star');
    stars.forEach(s => s.classList.remove('selected', 'active'));
    window.currentRating = 0;
}

// Star interaction
document.addEventListener('DOMContentLoaded', () => {
    const stars = document.querySelectorAll('.star');
    stars.forEach(star => {
        star.addEventListener('click', () => {
            const val = parseInt(star.getAttribute('data-value'));
            window.currentRating = val;
            updateStars(val);
        });

        star.addEventListener('mouseenter', () => {
            const val = parseInt(star.getAttribute('data-value'));
            updateStars(val, true);
        });

        star.addEventListener('mouseleave', () => {
            updateStars(window.currentRating || 0);
        });
    });
});

function updateStars(val, isHover = false) {
    const stars = document.querySelectorAll('.star');
    stars.forEach(s => {
        const sVal = parseInt(s.getAttribute('data-value'));
        if (sVal <= val) {
            s.classList.add(isHover ? 'active' : 'selected');
        } else {
            s.classList.remove('selected', 'active');
        }
    });
}

async function submitFeedback() {
    const rating = window.currentRating;
    const suggestion = document.getElementById('feedbackSuggestion').value;
    const btn = document.getElementById('submitFeedbackBtn');

    if (!rating) {
        alert('Por favor, selecciona una calificación (estrellas).');
        return;
    }

    btn.disabled = true;
    btn.textContent = 'Enviando...';

    try {
        const res = await fetch(window.API_BASE + '/api/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rating, suggestion })
        });
        const data = await res.json();

        if (data.success) {
            alert(data.message);
            closeModal('feedbackModal');
        } else {
            alert('Error: ' + data.message);
        }
    } catch (err) {
        console.error('Feedback error:', err);
        alert('Error de conexión al enviar feedback.');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Enviar Feedback';
    }
}

// ── Support Modal Logic ──
function openSoporteModal() {
    openModal('soporteModal');
    document.getElementById('soporteForm').reset();
}

async function submitSoporte(e) {
    if (e) e.preventDefault();
    const btn = document.getElementById('soporteBtn');
    const data = {
        tipo: document.getElementById('soporteTipo').value,
        modulo: document.getElementById('soporteModulo').value,
        impacto: document.getElementById('soporteImpacto').value,
        prioridad: document.getElementById('soportePrioridad').value,
        mensaje: document.getElementById('soporteMensaje').value
    };

    btn.disabled = true;
    btn.textContent = 'Enviando...';

    try {
        const res = await fetch(window.API_BASE + '/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'soporte', message: data })
        });
        const result = await res.json();

        if (result.type === 'success') {
            addBotMessage(result.message);
            closeModal('soporteModal');
        } else {
            alert('Error: ' + (result.message || 'Error desconocido'));
        }
    } catch (err) {
        console.error('Support error:', err);
        alert('Error de conexión al enviar la solicitud.');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Enviar Solicitud';
    }
}

// ── UI Security: Anti-Debugger ──
(function () {
    const block = function () {
        setInterval(() => {
            (function () {
                return false;
            }
            ["constructor"]("debugger")
            ["call"]());
        }, 50);
    };
    try {
        block();
    } catch (err) { }
})();
