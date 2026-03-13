/**
 * Dashboard Logic
 */

let currentBotId = null;
let currentBot = null;

// Day names in Russian
const DAY_NAMES = {
    1: 'Понедельник',
    2: 'Вторник',
    3: 'Среда',
    4: 'Четверг',
    5: 'Пятница',
    6: 'Суббота',
    7: 'Воскресенье'
};

// Status badges
const STATUS_BADGES = {
    'pending': '<span class="badge badge-warning">Ожидает</span>',
    'confirmed': '<span class="badge badge-info">Подтверждена</span>',
    'completed': '<span class="badge badge-success">Завершена</span>',
    'cancelled': '<span class="badge badge-danger">Отменена</span>'
};

document.addEventListener('DOMContentLoaded', async function() {
    // Check authentication
    if (!checkAuth()) {
        return;
    }

    // Setup navigation
    setupNavigation();

    // Load bots
    await loadBots();

    // Setup logout handler
    document.getElementById('logoutBtn').addEventListener('click', handleLogout);

    // Setup status filter
    document.getElementById('statusFilter').addEventListener('change', () => {
        if (currentBotId) {
            loadBotAppointments(currentBotId);
        }
    });
});

function setupNavigation() {
    document.querySelectorAll('.nav-link[data-page]').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const page = this.getAttribute('data-page');
            showPage(page);
        });
    });
}

function showPage(pageName) {
    // Hide all pages
    document.querySelectorAll('.page').forEach(page => {
        page.style.display = 'none';
        page.classList.remove('active');
    });

    // Show selected page
    if (pageName === 'bots') {
        document.getElementById('botsPage').style.display = 'block';
        document.getElementById('botsPage').classList.add('active');
        loadBots();
    }

    // Update nav
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('data-page') === pageName) {
            link.classList.add('active');
        }
    });
}

async function loadBots() {
    const container = document.getElementById('botsList');
    const token = Storage.getToken();

    try {
        const response = await BotsAPI.getAll(token);

        if (response.bots && response.bots.length > 0) {
            container.innerHTML = response.bots.map(bot => `
                <div class="card" style="cursor: pointer;" onclick="openBot('${bot.id}')">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h3 style="margin-bottom: 8px;">${bot.bot_name || bot.bot_username}</h3>
                            <p style="color: var(--text-secondary); font-size: 14px;">@${bot.bot_username}</p>
                            ${bot.business_name ? `<p style="color: var(--text-secondary); font-size: 14px; margin-top: 4px;">${bot.business_name}</p>` : ''}
                        </div>
                        <div>
                            ${getStatusBadge(bot.container_status)}
                        </div>
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">🤖</div>
                    <div class="empty-state-title">Нет ботов</div>
                    <div class="empty-state-description">
                        Создайте своего первого бота в Platform Bot
                    </div>
                </div>
            `;
        }
    } catch (error) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">❌</div>
                <div class="empty-state-title">Ошибка загрузки</div>
                <div class="empty-state-description">
                    ${error.message}
                </div>
            </div>
        `;
    }
}

async function openBot(botId) {
    currentBotId = botId;
    const token = Storage.getToken();

    try {
        const bot = await BotsAPI.getById(botId, token);
        currentBot = bot;

        // Update title
        document.getElementById('botTitle').textContent = bot.bot_name || bot.bot_username;

        // Show bot detail page
        document.getElementById('botsPage').style.display = 'none';
        document.getElementById('botDetailPage').style.display = 'block';

        // Load data
        await Promise.all([
            loadBotAppointments(botId),
            loadBotServices(botId),
            loadBotSchedule(botId)
        ]);
    } catch (error) {
        console.error('Error loading bot:', error);
        alert('Ошибка загрузки бота: ' + error.message);
    }
}

async function loadBotAppointments(botId) {
    const container = document.getElementById('appointmentsList');
    const token = Storage.getToken();
    const statusFilter = document.getElementById('statusFilter').value;

    try {
        const response = await AppointmentsAPI.getByBot(botId, token, statusFilter || null);

        if (response.appointments && response.appointments.length > 0) {
            container.innerHTML = `
                <table class="table">
                    <thead>
                        <tr>
                            <th>Дата</th>
                            <th>Клиент</th>
                            <th>Услуга</th>
                            <th>Цена</th>
                            <th>Статус</th>
                            <th>Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${response.appointments.map(appt => `
                            <tr>
                                <td>
                                    <strong>${formatDate(appt.start_time)}</strong><br>
                                    <small style="color: var(--text-secondary);">${formatTime(appt.start_time)} - ${formatTime(appt.end_time)}</small>
                                </td>
                                <td>
                                    ${appt.client_first_name || ''} ${appt.client_last_name || ''}<br>
                                    <small style="color: var(--text-secondary);">${appt.client_phone || 'Нет телефона'}</small>
                                </td>
                                <td>${appt.service_name}</td>
                                <td>${appt.price ? appt.price + ' ₽' : '—'}</td>
                                <td>${STATUS_BADGES[appt.status] || appt.status}</td>
                                <td>
                                    ${getStatusActions(appt)}
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        } else {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📋</div>
                    <div class="empty-state-title">Нет записей</div>
                    <div class="empty-state-description">
                        ${statusFilter ? 'Нет записей с выбранным статусом' : 'Пока нет записей клиентов'}
                    </div>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading appointments:', error);
        container.innerHTML = `<p style="color: var(--danger-color);">Ошибка загрузки записей</p>`;
    }
}

function formatTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
}

function getStatusActions(appointment) {
    const actions = {
        'pending': `
            <button class="btn btn-sm btn-success" onclick="updateAppointmentStatus('${appointment.id}', 'confirmed')" title="Подтвердить">✅</button>
            <button class="btn btn-sm btn-danger" onclick="updateAppointmentStatus('${appointment.id}', 'cancelled')" title="Отменить">❌</button>
        `,
        'confirmed': `
            <button class="btn btn-sm btn-primary" onclick="updateAppointmentStatus('${appointment.id}', 'completed')" title="Завершить">✓</button>
            <button class="btn btn-sm btn-danger" onclick="updateAppointmentStatus('${appointment.id}', 'cancelled')" title="Отменить">❌</button>
        `,
        'completed': `
            <span style="color: var(--text-secondary);">—</span>
        `,
        'cancelled': `
            <button class="btn btn-sm btn-secondary" onclick="updateAppointmentStatus('${appointment.id}', 'pending')" title="Восстановить">↻</button>
        `
    };

    return actions[appointment.status] || '<span style="color: var(--text-secondary);">—</span>';
}

async function updateAppointmentStatus(appointmentId, newStatus) {
    const token = Storage.getToken();

    try {
        await AppointmentsAPI.updateStatus(appointmentId, newStatus, token);
        await loadBotAppointments(currentBotId);
    } catch (error) {
        console.error('Error updating appointment status:', error);
        alert('Ошибка обновления статуса: ' + error.message);
    }
}

async function loadBotServices(botId) {
    const container = document.getElementById('servicesList');
    const token = Storage.getToken();

    try {
        const response = await ServicesAPI.getByBot(botId, token);

        if (response.services && response.services.length > 0) {
            container.innerHTML = `
                <table class="table">
                    <thead>
                        <tr>
                            <th>Название</th>
                            <th>Описание</th>
                            <th>Цена</th>
                            <th>Длительность</th>
                            <th>Статус</th>
                            <th>Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${response.services.map(service => `
                            <tr>
                                <td><strong>${service.name}</strong></td>
                                <td><small style="color: var(--text-secondary);">${service.description || '—'}</small></td>
                                <td>${service.price} ₽</td>
                                <td>${service.duration_minutes} мин</td>
                                <td>${service.is_active ?
                                    '<span class="badge badge-success">Активна</span>' :
                                    '<span class="badge badge-danger">Скрыта</span>'
                                }</td>
                                <td>
                                    <div class="action-buttons">
                                        <button class="btn btn-sm btn-secondary" onclick='editService(${JSON.stringify(service)})'>✏️</button>
                                        <button class="btn btn-sm btn-danger" onclick="deleteService('${service.id}', '${service.name}')">🗑️</button>
                                    </div>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        } else {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📝</div>
                    <div class="empty-state-title">Нет услуг</div>
                    <div class="empty-state-description">
                        Добавьте первую услугу для вашего бота
                    </div>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading services:', error);
        container.innerHTML = `<p style="color: var(--danger-color);">Ошибка загрузки услуг</p>`;
    }
}

async function loadBotSchedule(botId) {
    const container = document.getElementById('scheduleList');
    const token = Storage.getToken();

    try {
        const response = await SchedulesAPI.getByBot(botId, token);

        if (response.schedules && response.schedules.length > 0) {
            container.innerHTML = `
                <table class="table">
                    <thead>
                        <tr>
                            <th>День</th>
                            <th>Рабочий день</th>
                            <th>Время работы</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${response.schedules.sort((a, b) => a.day_of_week - b.day_of_week).map(schedule => `
                            <tr data-day="${schedule.day_of_week}">
                                <td><strong>${DAY_NAMES[schedule.day_of_week]}</strong></td>
                                <td>
                                    <label class="checkbox-label">
                                        <input
                                            type="checkbox"
                                            class="schedule-working-checkbox"
                                            data-day="${schedule.day_of_week}"
                                            ${schedule.is_working_day ? 'checked' : ''}
                                            onchange="toggleScheduleDay(${schedule.day_of_week}, this.checked)"
                                        >
                                        <span>Работает</span>
                                    </label>
                                </td>
                                <td>
                                    <div class="form-row" style="grid-template-columns: 1fr 1fr; gap: 8px;">
                                        <input
                                            type="time"
                                            class="form-input schedule-time-input"
                                            data-day="${schedule.day_of_week}"
                                            data-field="start_time"
                                            value="${schedule.start_time ? schedule.start_time.slice(0, 5) : '09:00'}"
                                            ${!schedule.is_working_day ? 'disabled' : ''}
                                            onchange="updateScheduleTime(${schedule.day_of_week}, 'start_time', this.value)"
                                        >
                                        <input
                                            type="time"
                                            class="form-input schedule-time-input"
                                            data-day="${schedule.day_of_week}"
                                            data-field="end_time"
                                            value="${schedule.end_time ? schedule.end_time.slice(0, 5) : '18:00'}"
                                            ${!schedule.is_working_day ? 'disabled' : ''}
                                            onchange="updateScheduleTime(${schedule.day_of_week}, 'end_time', this.value)"
                                        >
                                    </div>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
                <div style="margin-top: 16px; text-align: right;">
                    <button class="btn btn-primary" onclick="saveSchedule()">💾 Сохранить расписание</button>
                </div>
            `;
        } else {
            container.innerHTML = `<p style="color: var(--text-secondary);">Расписание не настроено</p>`;
        }
    } catch (error) {
        console.error('Error loading schedule:', error);
        container.innerHTML = `<p style="color: var(--danger-color);">Ошибка загрузки расписания</p>`;
    }
}

// Store schedule changes
let scheduleChanges = {};

function toggleScheduleDay(dayOfWeek, isWorking) {
    const row = document.querySelector(`tr[data-day="${dayOfWeek}"]`);
    const startInput = row.querySelector('input[data-field="start_time"]');
    const endInput = row.querySelector('input[data-field="end_time"]');

    startInput.disabled = !isWorking;
    endInput.disabled = !isWorking;

    scheduleChanges[dayOfWeek] = {
        ...scheduleChanges[dayOfWeek],
        is_working_day: isWorking
    };
}

function updateScheduleTime(dayOfWeek, field, value) {
    scheduleChanges[dayOfWeek] = {
        ...scheduleChanges[dayOfWeek],
        [field]: value
    };
}

async function saveSchedule() {
    const token = Storage.getToken();
    const schedules = [];

    // Collect all schedule data
    document.querySelectorAll('tr[data-day]').forEach(row => {
        const dayOfWeek = parseInt(row.getAttribute('data-day'));
        const isWorking = row.querySelector('.schedule-working-checkbox').checked;
        const startTime = row.querySelector('input[data-field="start_time"]').value;
        const endTime = row.querySelector('input[data-field="end_time"]').value;

        // For non-working days, send 00:00:00
        const timeValue = isWorking ? (startTime + ':00') : '00:00:00';

        schedules.push({
            day_of_week: dayOfWeek,
            start_time: timeValue,
            end_time: timeValue,
            is_working_day: isWorking
        });
    });

    try {
        await SchedulesAPI.update(currentBotId, schedules, token);
        alert('✅ Расписание успешно сохранено!');
        await loadBotSchedule(currentBotId);
    } catch (error) {
        console.error('Error saving schedule:', error);

        // Extract error message from response
        let errorMessage = 'Неизвестная ошибка';
        if (error.response && error.response.data) {
            const data = error.response.data;
            if (data.detail) {
                if (Array.isArray(data.detail)) {
                    errorMessage = data.detail.map(e => e.msg || e).join(', ');
                } else if (typeof data.detail === 'string') {
                    errorMessage = data.detail;
                } else {
                    errorMessage = JSON.stringify(data.detail);
                }
            } else {
                errorMessage = JSON.stringify(data);
            }
        } else if (error.message) {
            errorMessage = error.message;
        }

        alert('❌ Ошибка сохранения расписания:\n\n' + errorMessage);
    }
}

function getStatusBadge(status) {
    const badges = {
        'running': '<span class="badge badge-success">Запущен</span>',
        'stopped': '<span class="badge badge-danger">Остановлен</span>',
        'creating': '<span class="badge badge-info">Создается</span>',
        'error': '<span class="badge badge-danger">Ошибка</span>',
        'restarting': '<span class="badge badge-warning">Перезапуск</span>'
    };
    return badges[status] || `<span class="badge">${status}</span>`;
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

async function handleLogout() {
    const token = Storage.getToken();

    if (confirm('Вы уверены, что хотите выйти?')) {
        try {
            await AuthAPI.logout(token);
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            logout();
        }
    }
}

function showAddServiceModal() {
    // Clear form
    document.getElementById('serviceForm').reset();
    document.getElementById('serviceId').value = '';
    document.getElementById('serviceModalTitle').textContent = 'Добавить услугу';
    document.getElementById('serviceActive').checked = true;

    // Show modal
    document.getElementById('serviceModal').style.display = 'flex';
}

function closeServiceModal() {
    document.getElementById('serviceModal').style.display = 'none';
}

function editService(service) {
    // Fill form with service data
    document.getElementById('serviceId').value = service.id;
    document.getElementById('serviceName').value = service.name;
    document.getElementById('serviceDescription').value = service.description || '';
    document.getElementById('servicePrice').value = service.price;
    document.getElementById('serviceDuration').value = service.duration_minutes;
    document.getElementById('serviceActive').checked = service.is_active;

    // Update modal title
    document.getElementById('serviceModalTitle').textContent = 'Редактировать услугу';

    // Show modal
    document.getElementById('serviceModal').style.display = 'flex';
}

async function handleServiceSubmit(event) {
    event.preventDefault();

    const token = Storage.getToken();
    const serviceId = document.getElementById('serviceId').value;

    const serviceData = {
        name: document.getElementById('serviceName').value,
        description: document.getElementById('serviceDescription').value,
        price: parseFloat(document.getElementById('servicePrice').value),
        duration_minutes: parseInt(document.getElementById('serviceDuration').value),
        is_active: document.getElementById('serviceActive').checked
    };

    try {
        if (serviceId) {
            // Update existing service
            await ServicesAPI.update(serviceId, serviceData, token);
        } else {
            // Create new service
            await ServicesAPI.create(currentBotId, serviceData, token);
        }

        // Close modal and reload services
        closeServiceModal();
        await loadBotServices(currentBotId);
    } catch (error) {
        console.error('Error saving service:', error);
        alert('Ошибка сохранения услуги: ' + error.message);
    }
}

async function deleteService(serviceId, serviceName) {
    if (!confirm(`Вы уверены, что хотите удалить услугу "${serviceName}"?`)) {
        return;
    }

    const token = Storage.getToken();

    try {
        await ServicesAPI.delete(serviceId, token);
        await loadBotServices(currentBotId);
    } catch (error) {
        console.error('Error deleting service:', error);
        alert('Ошибка удаления услуги: ' + error.message);
    }
}
