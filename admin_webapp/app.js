const root = document.getElementById("root");
const yearLabel = document.getElementById("year");

const STORAGE_TOKEN_KEY = "ecostep_admin_token";
const STORAGE_ADMIN_ID_KEY = "ecostep_admin_id";
const API_BASE = `${window.location.origin}/api`;

const state = {
    token: localStorage.getItem(STORAGE_TOKEN_KEY),
    adminId: Number.parseInt(localStorage.getItem(STORAGE_ADMIN_ID_KEY) || "", 10) || null,
    telegramUser: null,
};

const CHALLENGE_TEMPLATES = [
    { id: 1, action: "Пешая прогулка/велопоездка вместо авто (5 км)", points: 10, co2: "1.1 кг CO₂" },
    { id: 2, action: "Использование общественного транспорта вместо такси (10 км)", points: 15, co2: "1.5 - 1.7 кг CO₂" },
    { id: 3, action: "Экономия 1 кВт*ч электроэнергии", points: 5, co2: "0.5 кг CO₂" },
    { id: 4, action: "Сдача 1 кг макулатуры", points: 8, co2: "1.0 - 1.3 кг CO₂" },
    { id: 5, action: "Правильная утилизация 1 кг пластика (ПЭТ)", points: 20, co2: "2.0 кг CO₂" },
    { id: 6, action: "Пользуйся многоразовой бутылкой (отказ от 1 бутылки 0.5л)", points: 3, co2: "0.1 - 0.15 кг CO₂" },
    { id: 7, action: "Экономия 100 литров горячей воды (60°C)", points: 30, co2: "3.0 - 3.5 кг CO₂" },
    { id: 8, action: "Посадка 1 дерева", points: 50, co2: "Поглощает 12-25 кг CO₂/год" },
];

const telegram = window.Telegram?.WebApp;
if (telegram) {
    telegram.ready();
    const user = telegram.initDataUnsafe?.user;
    if (user?.id) {
        state.telegramUser = user;
        state.adminId = user.id;
    }
}

yearLabel.textContent = new Date().getFullYear();

function saveAuth(token, adminId) {
    state.token = token;
    state.adminId = adminId;
    localStorage.setItem(STORAGE_TOKEN_KEY, token);
    localStorage.setItem(STORAGE_ADMIN_ID_KEY, String(adminId));
}

function clearAuth() {
    state.token = null;
    localStorage.removeItem(STORAGE_TOKEN_KEY);
    localStorage.removeItem(STORAGE_ADMIN_ID_KEY);
}

function showMessage(text) {
    if (telegram) {
        telegram.showAlert(text);
    } else {
        alert(text);
    }
}

function initPasswordToggles(container = document) {
    container.querySelectorAll(".password-toggle").forEach((button) => {
        const targetId = button.dataset.target;
        const input = container.querySelector(`#${targetId}`);
        if (!input) {
            return;
        }
        button.addEventListener("click", () => {
            const isHidden = input.type === "password";
            input.type = isHidden ? "text" : "password";
            button.textContent = isHidden ? "Скрыть" : "Показать";
        });
    });
}

function setupChallengeTemplateSelector(form) {
    const templateSelect = form.querySelector("#challenge-template");
    const pointsInput = form.querySelector("#challenge-points");
    const co2Input = form.querySelector("#challenge-co2");

    if (!templateSelect || !pointsInput || !co2Input) return;

    templateSelect.addEventListener("change", () => {
        const templateId = Number(templateSelect.value);
        if (!templateId) {
            pointsInput.value = "";
            co2Input.value = "";
            return;
        }

        const template = CHALLENGE_TEMPLATES.find(t => t.id === templateId);
        if (template) {
            pointsInput.value = template.points;
            co2Input.value = template.co2;
        }
    });
}

async function apiFetch(path, options = {}) {
    const headers = options.headers ? { ...options.headers } : {};
    if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
        headers["Content-Type"] = "application/json";
    }
    if (state.token) {
        headers.Authorization = `Bearer ${state.token}`;
    }

    const response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
    });

    if (response.status === 401) {
        clearAuth();
        throw new Error("Требуется повторный вход в систему.");
    }

    if (!response.ok) {
        let details = "Ошибка запроса.";
        try {
            const data = await response.json();
            details = data.detail || details;
        } catch {
            details = await response.text();
        }
        throw new Error(details);
    }

    if (response.status === 204) {
        return null;
    }
    return response.json();
}

function renderLogin() {
    const adminIdLabel = state.telegramUser
        ? `<p>🙋 Привет, ${state.telegramUser.first_name || "админ"}!</p>`
        : `
            <label for="admin-id">ID администратора</label>
            <input type="text" id="admin-id" placeholder="Введите Telegram ID" inputmode="numeric" pattern="\\d*" required>
        `;

    root.innerHTML = `
        <section class="card">
            <h2>Вход в админ-панель</h2>
            <form id="login-form">
                ${adminIdLabel}
                <label for="password">Пароль</label>
                <div class="password-input align-right">
                    <input type="password" id="password" placeholder="Введите пароль" required>
                    <button type="button" class="password-toggle" data-target="password">Показать</button>
                </div>
                <button type="submit">Войти</button>
            </form>
            <p class="hint">
                Эта форма авторизует вас в админ-панели EcoStep. Убедитесь, что вы используете защищённое подключение.
            </p>
        </section>
    `;

    const loginForm = document.getElementById("login-form");
    const passwordInput = document.getElementById("password");
    const adminIdInput = document.getElementById("admin-id");
    initPasswordToggles(loginForm);

    loginForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const password = passwordInput.value.trim();
        const adminId = state.telegramUser
            ? state.telegramUser.id
            : Number.parseInt(adminIdInput.value, 10);

        if (!password) {
            showMessage("Введите пароль администратора.");
            return;
        }
        if (!adminId || Number.isNaN(adminId)) {
            showMessage("Укажите корректный Telegram ID.");
            return;
        }

        try {
            const response = await apiFetch("/auth/login", {
                method: "POST",
                body: JSON.stringify({ password, admin_id: adminId }),
            });
            saveAuth(response.token, response.admin_id);
            showMessage("Успешный вход в админ-панель.");
            renderAdminPanel();
        } catch (error) {
            showMessage(error.message);
        }
    });
}

function renderAdminPanel() {
    root.innerHTML = `
        <section class="card">
            <div class="panel-header">
                <h2>Панель управления</h2>
                <button type="button" id="logout-btn" class="secondary">Выйти</button>
            </div>

            <div class="panel-block">
                <h3>Рассылка</h3>
                <form id="broadcast-form">
                    <label for="broadcast-message">Текст сообщения</label>
                    <textarea id="broadcast-message" rows="4" placeholder="Введите текст для рассылки"></textarea>
                    <button type="submit">Отправить всем пользователям</button>
                </form>
            </div>

            <div class="panel-block">
                <h3>Добавить челлендж</h3>
                <form id="challenge-form">
                    <label for="challenge-template">Выберите действие</label>
                    <select id="challenge-template" required>
                        <option value="">— Выберите из списка —</option>
                        ${CHALLENGE_TEMPLATES.map(t => 
                            `<option value="${t.id}">${t.action}</option>`
                        ).join("")}
                    </select>

                    <label for="challenge-title">Название задания</label>
                    <input id="challenge-title" type="text" placeholder="Например: Прогулка в парке" required>

                    <label for="challenge-description">Описание</label>
                    <textarea id="challenge-description" rows="3" placeholder="Опишите условия выполнения" required></textarea>

                    <label for="challenge-points">Баллы (автоматически)</label>
                    <input id="challenge-points" type="number" min="1" max="500" readonly required>

                    <label for="challenge-co2">Экономия CO₂ (автоматически)</label>
                    <input id="challenge-co2" type="text" readonly required>

                    <button type="submit">Добавить задание</button>
                </form>
            </div>

            <div class="panel-block">
                <div class="panel-header">
                    <h3>Кастомные челленджи</h3>
                    <button type="button" id="refresh-challenges" class="secondary">Обновить</button>
                </div>
                <div id="challenges-list" class="list challenges-list"></div>
            </div>

            <div class="panel-block">
                <div class="panel-header">
                    <h3>Отчёты на проверку</h3>
                    <button type="button" id="refresh-reports" class="secondary">Обновить</button>
                </div>
                <div id="reports-list" class="list"></div>
            </div>

            <div class="panel-block">
                <div class="panel-header">
                    <h3>Лог действий</h3>
                    <button type="button" id="refresh-logs" class="secondary">Обновить</button>
                </div>
                <div class="logs-container">
                    <ul id="logs-list" class="list"></ul>
                </div>
            </div>
        </section>
    `;

    document.getElementById("logout-btn").addEventListener("click", handleLogout);
    document.getElementById("broadcast-form").addEventListener("submit", handleBroadcast);
    document.getElementById("challenge-form").addEventListener("submit", handleAddChallenge);
    document.getElementById("refresh-reports").addEventListener("click", loadPendingReports);
    document.getElementById("refresh-challenges").addEventListener("click", loadChallenges);
    document.getElementById("refresh-logs").addEventListener("click", loadLogs);

    const challengeForm = document.getElementById("challenge-form");
    if (challengeForm) {
        setupChallengeTemplateSelector(challengeForm);
    }

    loadPendingReports();
    loadChallenges();
    loadLogs();
}

async function handleLogout() {
    try {
        await apiFetch("/auth/logout", { method: "POST" });
    } catch {
        // игнорируем ошибки выхода
    } finally {
        clearAuth();
        showMessage("Вы вышли из админ-панели.");
        renderLogin();
    }
}

async function handleBroadcast(event) {
    event.preventDefault();
    const textarea = document.getElementById("broadcast-message");
    const message = textarea.value.trim();
    if (!message) {
        showMessage("Введите текст рассылки.");
        return;
    }
    try {
        const result = await apiFetch("/broadcast", {
            method: "POST",
            body: JSON.stringify({ message }),
        });
        showMessage(`Рассылка завершена. Отправлено: ${result.sent}, ошибки: ${result.failed}.`);
        textarea.value = "";
    } catch (error) {
        showMessage(error.message);
    }
}

async function handleAddChallenge(event) {
    event.preventDefault();
    const title = document.getElementById("challenge-title").value.trim();
    const description = document.getElementById("challenge-description").value.trim();
    const points = Number.parseInt(document.getElementById("challenge-points").value, 10);
    const co2 = document.getElementById("challenge-co2").value.trim();

    if (!title || !description || !co2 || Number.isNaN(points) || points <= 0) {
        showMessage("Проверьте корректность полей задания.");
        return;
    }

    try {
        await apiFetch("/challenges", {
            method: "POST",
            body: JSON.stringify({ title, description, points, co2 }),
        });
        showMessage("Задание добавлено и доступно пользователям.");
        document.getElementById("challenge-form").reset();
        document.getElementById("challenge-points").value = "5";
        await loadChallenges();
    } catch (error) {
        showMessage(error.message);
    }
}

async function loadChallenges() {
    const container = document.getElementById("challenges-list");
    if (!container) {
        return;
    }
    container.textContent = "Загрузка...";
    try {
        const challenges = await apiFetch("/challenges");
        const custom = challenges.filter((challenge) => challenge.source === "custom");
        if (!custom.length) {
            container.innerHTML = "<p class=\"placeholder\">Нет созданных кастомных челленджей.</p>";
            return;
        }
        container.innerHTML = custom
            .map((challenge) => {
                const statusLabel = challenge.active ? "Активно" : "Отключено";
                const actionLabel = challenge.active ? "Убрать" : "Вернуть";
                const actionType = challenge.active ? "deactivate" : "activate";
                return `
                    <article class="challenge-card ${challenge.active ? "" : "inactive"}" data-id="${challenge.challenge_id}">
                        <header>
                            <strong>${challenge.title}</strong>
                            <span>${statusLabel}</span>
                        </header>
                        <p>${challenge.description}</p>
                        <p class="meta">Баллы: ${challenge.points} • CO₂: ${challenge.co2}</p>
                        <div class="actions">
                            <button type="button" data-action="${actionType}">${actionLabel}</button>
                            <button type="button" data-action="delete" class="danger">Удалить</button>
                        </div>
                    </article>
                `;
            })
            .join("");
        container.querySelectorAll("button[data-action]").forEach((button) => {
            button.addEventListener("click", async (event) => {
                const card = event.target.closest(".challenge-card");
                const challengeId = card.dataset.id;
                const action = event.target.dataset.action;
                if (action === "delete") {
                    const confirmedDelete = confirm("Удалить задание без возможности восстановления?");
                    if (!confirmedDelete) {
                        return;
                    }
                    try {
                        await apiFetch(`/challenges/${encodeURIComponent(challengeId)}`, {
                            method: "DELETE",
                        });
                        showMessage("Задание удалено.");
                        await loadChallenges();
                    } catch (error) {
                        showMessage(error.message);
                    }
                    return;
                }

                const isDeactivate = action === "deactivate";
                if (isDeactivate) {
                    const confirmed = confirm("Убрать задание из списка доступных?");
                    if (!confirmed) {
                        return;
                    }
                }
                try {
                    await apiFetch(`/challenges/${encodeURIComponent(challengeId)}`, {
                        method: "PATCH",
                        body: JSON.stringify({ active: !isDeactivate }),
                    });
                    showMessage(isDeactivate ? "Задание скрыто." : "Задание снова доступно.");
                    await loadChallenges();
                } catch (error) {
                    showMessage(error.message);
                }
            });
        });
    } catch (error) {
        container.textContent = error.message;
    }
}

async function loadPendingReports() {
    const container = document.getElementById("reports-list");
    container.textContent = "Загрузка...";
    try {
        const reports = await apiFetch("/reports/pending");
        if (!reports.length) {
            container.textContent = "Нет отчётов, ожидающих проверки.";
            return;
        }
        container.innerHTML = reports
            .map((report) => {
                let attachmentBlock = "<p>Файл: —</p>";
                if (report.file_url && report.attachment_type === "photo") {
                    attachmentBlock = `
                        <figure class="report-media">
                            <img src="${report.file_url}" alt="Фото отчёта" class="report-preview" loading="lazy" />
                            <figcaption>${report.attachment_name || "Фото"}</figcaption>
                        </figure>
                    `;
                } else if (report.file_url) {
                    const fileLabel = report.attachment_name || "Скачать файл";
                    attachmentBlock = `
                        <p class="report-download">
                            <a href="${report.file_url}" target="_blank" rel="noopener" class="download-link">${fileLabel}</a>
                        </p>
                    `;
                }
                const commentText = report.caption || "—";
                const usernameText = report.username ? `@${report.username}` : "—";
                return `
                    <article class="report-card" data-user="${report.user_id}" data-challenge="${report.challenge_id}">
                        <header>
                            <strong>${report.challenge_title}</strong>
                            <span>${report.submitted_at}</span>
                        </header>
                        <p>Пользователь: ${report.first_name || "Без имени"} (${usernameText})</p>
                        <p>Комментарий: ${commentText}</p>
                        ${attachmentBlock}
                        <div class="actions">
                            <button type="button" data-action="approve">Одобрить</button>
                            <button type="button" data-action="reject" class="danger">Отклонить</button>
                        </div>
                    </article>
                `;
            })
            .join("");

        container.querySelectorAll("button[data-action]").forEach((button) => {
            button.addEventListener("click", async (event) => {
                const card = event.target.closest(".report-card");
                const userId = Number(card.dataset.user);
                const challengeId = card.dataset.challenge;
                const decision = event.target.dataset.action === "approve" ? "approved" : "rejected";
                let comment = null;
                if (decision === "rejected") {
                    const input = prompt("Укажите причину отклонения (необязательно):", "");
                    if (input === null) {
                        return;
                    }
                    comment = input.trim();
                }
                try {
                    await apiFetch("/reports/resolve", {
                        method: "POST",
                        body: JSON.stringify({
                            user_id: userId,
                            challenge_id: challengeId,
                            decision,
                            comment: comment && comment.length ? comment : null,
                        }),
                    });
                    showMessage("Отчёт обработан.");
                    await loadPendingReports();
                    await loadLogs();
                } catch (error) {
                    showMessage(error.message);
                }
            });
        });
    } catch (error) {
        container.textContent = error.message;
    }
}

async function loadLogs() {
    const container = document.getElementById("logs-list");
    container.textContent = "";
    try {
        const logs = await apiFetch("/logs");
        if (!logs.length) {
            container.innerHTML = "<li>Лог пуст.</li>";
            return;
        }
        container.innerHTML = logs
            .map((log) => {
                const created = new Date(log.created_at).toLocaleString();
                return `<li><strong>${created}</strong> — [${log.admin_id ?? "?"}] ${log.action}${log.details ? ` (${log.details})` : ""}</li>`;
            })
            .join("");
    } catch (error) {
        container.innerHTML = `<li>${error.message}</li>`;
    }
}

if (state.token) {
    renderAdminPanel();
} else {
    renderLogin();
}
