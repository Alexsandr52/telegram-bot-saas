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
                            <th>Статус</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${response.appointments.map(appt => `
                            <tr>
                                <td>${formatDate(appt.start_time)}</td>
                                <td>
                                    ${appt.client_first_name || ''} ${appt.client_last_name || ''}<br>
                                    <small style="color: var(--text-secondary);">${appt.client_phone || ''}</small>
                                </td>
                                <td>${appt.service_name}</td>
                                <td>${STATUS_BADGES[appt.status] || appt.status}</td>
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
                        Пока нет записей клиентов
                    </div>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading appointments:', error);
        container.innerHTML = `<p style="color: var(--danger-color);">Ошибка загрузки записей</p>`;
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
                            <th>Цена</th>
                            <th>Длительность</th>
                            <th>Статус</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${response.services.map(service => `
                            <tr>
                                <td>${service.name}</td>
                                <td>${service.price} ₽</td>
                                <td>${service.duration_minutes} мин</td>
                                <td>${service.is_active ?
                                    '<span class="badge badge-success">Активна</span>' :
                                    '<span class="badge badge-danger">Скрыта</span>'
                                }</td>
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
                            <th>Время работы</th>
                            <th>Статус</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${response.schedules.sort((a, b) => a.day_of_week - b.day_of_week).map(schedule => `
                            <tr>
                                <td>${DAY_NAMES[schedule.day_of_week] || schedule.day_of_week}</td>
                                <td>
                                    ${schedule.is_working_day ?
                                        `${schedule.start_time.slice(0, 5)} - ${schedule.end_time.slice(0, 5)}` :
                                        '—'
                                    }
                                </td>
                                <td>
                                    ${schedule.is_working_day ?
                                        '<span class="badge badge-success">Работает</span>' :
                                        '<span class="badge badge-danger">Выходной</span>'
                                    }
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        } else {
            container.innerHTML = `<p style="color: var(--text-secondary);">Расписание не настроено</p>`;
        }
    } catch (error) {
        console.error('Error loading schedule:', error);
        container.innerHTML = `<p style="color: var(--danger-color);">Ошибка загрузки расписания</p>`;
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
    alert('Функция добавления услуг будет реализована в следующей версии');
}
