/**
 * Analytics API Client
 */

const AnalyticsAPI = {
    async getMasterOverview(token) {
        return apiRequest(`/analytics/masters/overview?token=${token}`);
    },

    async getBotOverview(botId, token, days = 30) {
        return apiRequest(`/analytics/bots/${botId}/overview?token=${token}&days=${days}`);
    },

    async getBotRevenue(botId, token, days = 30) {
        return apiRequest(`/analytics/bots/${botId}/revenue?token=${token}&days=${days}`);
    },

    async getBotAppointments(botId, token, days = 30) {
        return apiRequest(`/analytics/bots/${botId}/appointments?token=${token}&days=${days}`);
    }
};

/**
 * Render charts using simple SVG
 */
function renderRevenueChart(containerId, data) {
    const container = document.getElementById(containerId);
    if (!container || !data || data.length === 0) return;

    const width = container.offsetWidth || 600;
    const height = 300;
    const padding = 40;

    const maxRevenue = Math.max(...data.map(d => d.revenue)) || 1;
    const barWidth = (width - padding * 2) / data.length - 10;

    let svg = `<svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`;

    // Draw axes
    svg += `<line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" stroke="#e2e8f0" stroke-width="1"/>`;
    svg += `<line x1="${padding}" y1="${padding}" x2="${padding}" y2="${height - padding}" stroke="#e2e8f0" stroke-width="1"/>`;

    // Draw bars
    data.forEach((d, i) => {
        const barHeight = (d.revenue / maxRevenue) * (height - padding * 2);
        const x = padding + i * (barWidth + 10);
        const y = height - padding - barHeight;

        const dateLabel = new Date(d.date).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });

        svg += `
            <rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" fill="#4F46E5" rx="4"/>
            <text x="${x + barWidth / 2}" y="${height - padding + 20}" text-anchor="middle" font-size="10" fill="#64748b">${dateLabel}</text>
            ${d.revenue > 0 ? `<text x="${x + barWidth / 2}" y="${y - 5}" text-anchor="middle" font-size="10" fill="#4F46E5">${Math.round(d.revenue)}₽</text>` : ''}
        `;
    });

    svg += '</svg>';
    container.innerHTML = svg;
}

/**
 * Update analytics page
 */
async function loadAnalyticsPage() {
    const token = Storage.getToken();
    if (!token) {
        window.location.href = '/';
        return;
    }

    try {
        // Load master overview
        const masterOverview = await AnalyticsAPI.getMasterOverview(token);
        renderMasterOverview(masterOverview);

        // Load first bot's analytics if available
        const bots = await BotsAPI.getAll(token);
        if (bots && bots.length > 0) {
            const firstBot = bots[0];
            await loadBotAnalytics(firstBot.id, token);
            populateBotSelector(bots, firstBot.id);
        } else {
            document.getElementById('botAnalyticsSection').style.display = 'none';
            document.getElementById('noBotsMessage').style.display = 'block';
        }

    } catch (error) {
        console.error('Error loading analytics:', error);
        showNotification('Ошибка загрузки аналитики', 'error');
    }
}

/**
 * Render master overview
 */
function renderMasterOverview(data) {
    document.getElementById('totalBots').textContent = data.total_bots;
    document.getElementById('activeBots').textContent = data.active_bots;
    document.getElementById('totalAppointments').textContent = data.total_appointments;
    document.getElementById('totalRevenue').textContent = formatCurrency(data.total_revenue);
    document.getElementById('uniqueClients').textContent = data.unique_clients;
}

/**
 * Load bot-specific analytics
 */
async function loadBotAnalytics(botId, token) {
    try {
        // Load overview
        const overview = await AnalyticsAPI.getBotOverview(botId, token);
        renderBotOverview(overview);

        // Load revenue
        const revenue = await AnalyticsAPI.getBotRevenue(botId, token);
        renderRevenueChart('revenueChart', revenue.daily_data);

        // Load appointments stats
        const appointments = await AnalyticsAPI.getBotAppointments(botId, token);
        renderAppointmentsStats(appointments);

    } catch (error) {
        console.error('Error loading bot analytics:', error);
    }
}

/**
 * Render bot overview
 */
function renderBotOverview(data) {
    document.getElementById('botName').textContent = data.bot_name;
    document.getElementById('botTotalAppointments').textContent = data.total_appointments;
    document.getElementById('botCompletedAppointments').textContent = data.completed_appointments;
    document.getElementById('botCancelledAppointments').textContent = data.cancelled_appointments;
    document.getElementById('botTotalRevenue').textContent = formatCurrency(data.total_revenue);
    document.getElementById('botUniqueClients').textContent = data.unique_clients;
    document.getElementById('botActiveServices').textContent = data.active_services;
}

/**
 * Render appointments statistics
 */
function renderAppointmentsStats(data) {
    document.getElementById('pendingAppointments').textContent = data.pending;
    document.getElementById('confirmedAppointments').textContent = data.confirmed;
    document.getElementById('completedAppointments').textContent = data.completed;
    document.getElementById('cancelledAppointments').textContent = data.cancelled;
    document.getElementById('conversionRate').textContent = data.conversion_rate + '%';
}

/**
 * Populate bot selector dropdown
 */
function populateBotSelector(bots, selectedId) {
    const select = document.getElementById('botSelector');
    select.innerHTML = bots.map(bot =>
        `<option value="${bot.id}" ${bot.id === selectedId ? 'selected' : ''}>${bot.bot_name || bot.bot_username}</option>`
    ).join('');

    select.onchange = async (e) => {
        const token = Storage.getToken();
        await loadBotAnalytics(e.target.value, token);
    };
}

/**
 * Format currency
 */
function formatCurrency(value) {
    return new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: 'RUB',
        minimumFractionDigits: 0
    }).format(value);
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 3000);
}

/**
 * Period change handler
 */
function changePeriod(days) {
    const token = Storage.getToken();
    const botId = document.getElementById('botSelector').value;

    AnalyticsAPI.getBotRevenue(botId, token, days).then(data => {
        renderRevenueChart('revenueChart', data.daily_data);
    });

    AnalyticsAPI.getBotOverview(botId, token, days).then(data => {
        renderBotOverview(data);
    });
}

// Export functions for HTML
window.loadAnalyticsPage = loadAnalyticsPage;
window.changePeriod = changePeriod;
