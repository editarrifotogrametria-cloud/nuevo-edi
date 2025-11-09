const body = document.body;
const toast = document.getElementById('toast');
const views = {
    overview: document.getElementById('overviewView'),
    survey: document.getElementById('surveyView'),
    satellites: document.getElementById('satellitesView'),
    control: document.getElementById('controlView'),
    files: document.getElementById('filesView')
};

const state = {
    mode: 'Rover',
    recording: false,
    sessionStart: Date.now(),
    mapLayer: 'hybrid',
    gnss: {
        latitude: -8.1116,
        longitude: -79.0288,
        altitude: 28.32,
        horizontalAccuracy: 0.014,
        hdop: 0.8,
        satellites: 24,
        fix: 'Float',
        age: 1.8
    },
    imu: {
        tilt: 1.6,
        heading: 81.2,
        pitch: 0.5,
        roll: -0.2,
        calibrated: true,
        drift: 0.03,
        fusion: 'GNSS + IMU'
    },
    services: [
        { name: 'L-Band PPP', status: 'Sincronizando', tone: 'is-warning' },
        { name: 'NTRIP Caster', status: 'Correcciones 1.2s', tone: 'is-active' },
        { name: 'Radio LoRa', status: 'Stand-by', tone: '' },
        { name: 'Ethernet', status: 'Desconectado', tone: 'is-danger' }
    ],
    constellations: [
        { name: 'GPS', count: 12, snr: 41, color: '#5be7a9' },
        { name: 'GLONASS', count: 6, snr: 38, color: '#ffc75f' },
        { name: 'Galileo', count: 5, snr: 44, color: '#32d4ff' },
        { name: 'BeiDou', count: 4, snr: 37, color: '#ff94d5' }
    ],
    satellites: Array.from({ length: 18 }).map((_, i) => ({
        id: `G${(i + 3).toString().padStart(2, '0')}`,
        elevation: Math.round(Math.random() * 70 + 10),
        snr: Math.round(Math.random() * 20 + 35)
    })),
    project: {
        name: 'Catastro La Libertad',
        location: 'Trujillo · Zona 17S',
        owner: 'GNSS.AI Labs',
        accuracy: '2 cm RMS',
        stakeout: {
            target: 'P-023',
            distance: 0.38,
            bearing: 118
        }
    },
    points: [
        {
            name: 'P-021',
            lat: -8.111912,
            lon: -79.028122,
            alt: 32.41,
            accuracy: 0.011,
            date: '2024-02-22 10:14'
        },
        {
            name: 'P-022',
            lat: -8.111742,
            lon: -79.028611,
            alt: 31.96,
            accuracy: 0.009,
            date: '2024-02-22 10:21'
        }
    ],
    events: [
        { title: 'Correcciones RTCM aplicadas', time: 'Hace 45s' },
        { title: 'IMU calibrada correctamente', time: 'Hace 3m' },
        { title: 'Proyecto sincronizado con GNSS Cloud', time: 'Hace 12m' }
    ],
    files: [
        { name: '2024-02-22_trujillo_session.obs', size: '18.2 MB', time: 'Hace 4 min' },
        { name: 'projects_backup.json', size: '256 KB', time: 'Hoy 09:00' }
    ],
    sync: {
        drive: true,
        lastSync: 'Hoy · 09:00',
        pending: 2
    },
    snrHistory: Array.from({ length: 10 }, (_, i) => ({
        label: `-${10 - i}s`,
        gps: 40 + Math.random() * 5,
        glonass: 35 + Math.random() * 5,
        galileo: 38 + Math.random() * 5
    }))
};

let map;
let mapMarker;
let hybridLayer;
let topoLayer;
let snrChart;

function chartAxisColor() {
    return body.classList.contains('light') ? 'rgba(26,34,52,0.55)' : 'rgba(255,255,255,0.6)';
}

function chartGridColor() {
    return body.classList.contains('light') ? 'rgba(26,34,52,0.08)' : 'rgba(255,255,255,0.1)';
}

function formatCoord(value) {
    return `${value.toFixed(7)}°`;
}

function formatMeters(value, decimals = 2) {
    return `${value.toFixed(decimals)} m`;
}

function showToast(message) {
    toast.textContent = message;
    toast.classList.add('is-visible');
    clearTimeout(showToast.timeout);
    showToast.timeout = setTimeout(() => {
        toast.classList.remove('is-visible');
    }, 2500);
}

function updateSessionTimer() {
    const sessionEl = document.querySelector('#sessionInfo .session__value');
    const elapsed = Math.floor((Date.now() - state.sessionStart) / 1000);
    const hours = String(Math.floor(elapsed / 3600)).padStart(2, '0');
    const minutes = String(Math.floor((elapsed % 3600) / 60)).padStart(2, '0');
    const seconds = String(elapsed % 60).padStart(2, '0');
    sessionEl.textContent = `${hours}:${minutes}:${seconds}`;
}

function updateStatusCards() {
    const { gnss } = state;
    document.querySelector('#gnssStatus .status-card__value').textContent = `${gnss.satellites} sats`;
    document.querySelector('#rtkStatus .status-card__value').textContent = gnss.fix;
    document.querySelector('#imuStatus .status-card__value').textContent = state.imu.calibrated ? 'Activo' : 'Calibrando';
    document.querySelector('#networkStatus .status-card__value').textContent = state.services[1].status;

    document.querySelectorAll('.status-card').forEach(card => card.classList.remove('is-active'));
    if (gnss.fix.toLowerCase() === 'rtk fixed') {
        document.getElementById('rtkStatus').classList.add('is-active');
    }
}

function updateSolution() {
    const { gnss } = state;
    document.getElementById('solutionSubtitle').textContent = gnss.fix === 'Sin solución'
        ? 'Esperando posicionamiento RTK'
        : `Precisión ${formatMeters(gnss.horizontalAccuracy * 100)} · Edad ${gnss.age.toFixed(1)}s`;
    document.getElementById('latLon').textContent = `${formatCoord(gnss.latitude)}, ${formatCoord(gnss.longitude)}`;
    document.getElementById('altitude').textContent = `Altitud elipsoidal ${formatMeters(gnss.altitude)}`;
    document.getElementById('hAccuracy').textContent = `${(gnss.horizontalAccuracy * 100).toFixed(1)} cm`;
    document.getElementById('hdop').textContent = gnss.hdop.toFixed(1);
    document.getElementById('satCount').textContent = gnss.satellites;
    document.getElementById('correctionAge').textContent = `${gnss.age.toFixed(1)} s`;
}

function updateConstellations() {
    const list = document.getElementById('constellationsList');
    list.innerHTML = '';
    state.constellations.forEach(constellation => {
        const li = document.createElement('li');
        li.innerHTML = `
            <span>${constellation.name}</span>
            <div class="constellation__metrics">
                <span>${constellation.count} satélites</span>
                <span>${constellation.snr} dBHz</span>
            </div>`;
        li.style.setProperty('--tone', constellation.color);
        list.appendChild(li);
    });
}

function updateServices() {
    const list = document.getElementById('servicesList');
    list.innerHTML = '';
    state.services.forEach(service => {
        const li = document.createElement('li');
        if (service.tone) li.classList.add(service.tone);
        li.innerHTML = `
            <span>${service.name}</span>
            <span>${service.status}</span>`;
        list.appendChild(li);
    });
}

function updateImu() {
    const container = document.getElementById('imuStats');
    container.innerHTML = '';
    const entries = [
        { label: 'Tilt', value: `${state.imu.tilt.toFixed(1)}°` },
        { label: 'Heading', value: `${state.imu.heading.toFixed(1)}°` },
        { label: 'Pitch', value: `${state.imu.pitch.toFixed(1)}°` },
        { label: 'Roll', value: `${state.imu.roll.toFixed(1)}°` },
        { label: 'Drift', value: `${state.imu.drift.toFixed(2)}°/h` },
        { label: 'Fusión', value: state.imu.fusion }
    ];

    entries.forEach(entry => {
        const group = document.createElement('div');
        group.innerHTML = `<dt>${entry.label}</dt><dd>${entry.value}</dd>`;
        container.appendChild(group);
    });
}

function updateTimeline() {
    const list = document.getElementById('timeline');
    list.innerHTML = '';
    state.events.forEach(event => {
        const li = document.createElement('li');
        li.innerHTML = `<strong>${event.title}</strong><time>${event.time}</time>`;
        list.appendChild(li);
    });
}

function updateProject() {
    const summary = document.getElementById('projectSummary');
    summary.innerHTML = `
        <div class="project__header">
            <div>
                <h3>${state.project.name}</h3>
                <p>${state.project.location}</p>
            </div>
            <span class="badge">Precisión ${state.project.accuracy}</span>
        </div>
        <div>
            <p><strong>Responsable:</strong> ${state.project.owner}</p>
            <p><strong>Stakeout:</strong> ${state.project.stakeout.target} · ${state.project.stakeout.distance.toFixed(2)} m · ${state.project.stakeout.bearing}°</p>
        </div>`;
}

function updatePoints() {
    const tbody = document.querySelector('#pointsTable tbody');
    tbody.innerHTML = '';
    state.points.forEach(point => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${point.name}</td>
            <td>${point.lat.toFixed(6)}</td>
            <td>${point.lon.toFixed(6)}</td>
            <td>${point.alt.toFixed(2)}</td>
            <td>${(point.accuracy * 100).toFixed(1)} cm</td>
            <td>${point.date}</td>`;
        tbody.appendChild(row);
    });
}

function updateSatellites() {
    const panel = document.getElementById('satellitesPanel');
    panel.innerHTML = '';
    state.satellites.forEach(sat => {
        const container = document.createElement('div');
        container.className = 'satellite';
        container.innerHTML = `
            <span class="satellite__id">${sat.id}</span>
            <div class="satellite__bar"><span style="width: ${Math.min(sat.snr, 60)}%"></span></div>
            <span>${sat.snr} dBHz</span>`;
        panel.appendChild(container);
    });

    document.getElementById('polarChart').textContent = 'Visualización polar disponible en la versión móvil.';
}

function updateCommands() {
    const commands = {
        IMU: [
            { title: 'TILT ON', cmd: 'TILTCOMPENSATION ENABLE', desc: 'Activa compensación de inclinación' },
            { title: 'IMU 100Hz', cmd: 'IMURATE 100', desc: 'Frecuencia máxima de fusión' },
            { title: 'Calibrar IMU', cmd: 'IMUCALIBRATE', desc: 'Mantén quieto el receptor 30s' }
        ],
        Posicionamiento: [
            { title: 'Modo Rover', cmd: 'MODE ROVER', desc: 'Móvil con correcciones RTK' },
            { title: 'Modo Base', cmd: 'MODE BASE', desc: 'Genera correcciones RTCM' },
            { title: 'Reset RTK', cmd: 'RTKRESET', desc: 'Limpia solución y reinicia filtros' }
        ],
        GNSS: [
            { title: 'GPS + Galileo', cmd: 'LOG SATVIS', desc: 'Ver constelaciones habilitadas' },
            { title: 'PPP ON', cmd: 'PPP ENABLE', desc: 'Requiere conexión satelital L-Band' }
        ]
    };

    const container = document.getElementById('commandList');
    container.innerHTML = '';

    Object.entries(commands).forEach(([group, items]) => {
        const heading = document.createElement('h3');
        heading.textContent = group;
        container.appendChild(heading);

        items.forEach(item => {
            const block = document.createElement('div');
            block.className = 'command';
            block.innerHTML = `
                <div class="command__title">${item.title}</div>
                <div class="command__desc">${item.desc}</div>
                <code>${item.cmd}</code>
                <div class="command__actions">
                    <button class="ghost-btn" data-command="${item.cmd}">Enviar</button>
                    <button class="icon-btn" aria-label="Copiar comando" data-copy="${item.cmd}"><i data-lucide="copy"></i></button>
                </div>`;
            container.appendChild(block);
        });
    });
}

function updateProfiles() {
    const profiles = document.getElementById('profiles');
    profiles.innerHTML = '';
    const data = [
        { name: 'Topografía RTK', desc: 'RTK fijo + Tilt', accuracy: '2 cm' },
        { name: 'PPP L-Band', desc: 'PPP + IMU', accuracy: '5 cm' },
        { name: 'Base fija', desc: 'RTCM 3.x @ 1Hz', accuracy: 'Controlada' }
    ];

    data.forEach(profile => {
        const li = document.createElement('li');
        li.innerHTML = `
            <span>
                <strong>${profile.name}</strong>
                <small>${profile.desc}</small>
            </span>
            <span>${profile.accuracy}</span>`;
        profiles.appendChild(li);
    });
}

function updateFiles() {
    const list = document.getElementById('fileList');
    list.innerHTML = '';
    state.files.forEach(file => {
        const li = document.createElement('li');
        li.innerHTML = `
            <span>
                <strong>${file.name}</strong>
                <small>${file.time}</small>
            </span>
            <span>${file.size}</span>`;
        list.appendChild(li);
    });

    const sync = document.getElementById('syncPanel');
    sync.innerHTML = `
        <div><strong>Google Drive</strong><p>${state.sync.drive ? 'Vinculado' : 'Sin conexión'}</p></div>
        <div><strong>Última sincronización</strong><p>${state.sync.lastSync}</p></div>
        <div><strong>Pendientes</strong><p>${state.sync.pending}</p></div>
        <button class="primary-btn" id="syncBtn"><i data-lucide="refresh-cw"></i> Sincronizar ahora</button>`;
}

function setupMap() {
    map = L.map('map', { zoomControl: false, attributionControl: false }).setView([state.gnss.latitude, state.gnss.longitude], 17);

    hybridLayer = L.tileLayer('https://{s}.tile.jawg.io/jawg-sunny/{z}/{x}/{y}{r}.png?access-token=KPsw7SfjD8VR6pXqJx3NQ0dJrLrE2J28vKb5d9uKZ6SUIZIb2ypz6rZh0GJn4Ojd', {
        maxZoom: 20
    }).addTo(map);

    topoLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19
    });

    mapMarker = L.circleMarker([state.gnss.latitude, state.gnss.longitude], {
        radius: 8,
        color: '#32d4ff',
        fillColor: '#0ff0b3',
        fillOpacity: 0.9,
        weight: 3
    }).addTo(map);
}

function updateMap() {
    mapMarker.setLatLng([state.gnss.latitude, state.gnss.longitude]);
    if (!map.getBounds().contains(mapMarker.getLatLng())) {
        map.panTo(mapMarker.getLatLng());
    }
}

function setupSnrChart() {
    const ctx = document.getElementById('snrChart');
    snrChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: state.snrHistory.map(item => item.label),
            datasets: [
                {
                    label: 'GPS',
                    data: state.snrHistory.map(item => item.gps),
                    borderColor: '#5be7a9',
                    tension: 0.35,
                    fill: false
                },
                {
                    label: 'GLONASS',
                    data: state.snrHistory.map(item => item.glonass),
                    borderColor: '#ffc75f',
                    tension: 0.35,
                    fill: false
                },
                {
                    label: 'Galileo',
                    data: state.snrHistory.map(item => item.galileo),
                    borderColor: '#32d4ff',
                    tension: 0.35,
                    fill: false
                }
            ]
        },
        options: {
            plugins: { legend: { display: false } },
            scales: {
                x: { ticks: { color: chartAxisColor() }, grid: { color: chartGridColor() } },
                y: { ticks: { color: chartAxisColor() }, grid: { color: chartGridColor() }, suggestedMin: 20, suggestedMax: 55 }
            }
        }
    });
    updateChartTheme();
}

function updateSnrChart() {
    state.snrHistory.shift();
    state.snrHistory.push({
        label: 'Ahora',
        gps: 38 + Math.random() * 8,
        glonass: 34 + Math.random() * 8,
        galileo: 36 + Math.random() * 8
    });

    snrChart.data.labels = state.snrHistory.map(item => item.label);
    snrChart.data.datasets[0].data = state.snrHistory.map(item => item.gps);
    snrChart.data.datasets[1].data = state.snrHistory.map(item => item.glonass);
    snrChart.data.datasets[2].data = state.snrHistory.map(item => item.galileo);
    snrChart.update();
}

function updateChartTheme() {
    if (!snrChart) return;
    const axis = chartAxisColor();
    const grid = chartGridColor();
    snrChart.options.scales.x.ticks.color = axis;
    snrChart.options.scales.y.ticks.color = axis;
    snrChart.options.scales.x.grid.color = grid;
    snrChart.options.scales.y.grid.color = grid;
    snrChart.update('none');
}

function bindMenu() {
    document.querySelectorAll('.menu__item').forEach(button => {
        button.addEventListener('click', () => {
            document.querySelectorAll('.menu__item').forEach(item => item.classList.remove('is-active'));
            button.classList.add('is-active');

            Object.values(views).forEach(view => view.classList.remove('is-active'));
            views[button.dataset.view].classList.add('is-active');
            Object.entries(views).forEach(([key, view]) => {
                view.setAttribute('aria-hidden', key === button.dataset.view ? 'false' : 'true');
            });
        });
    });
}

function bindActions() {
    document.getElementById('themeToggle').addEventListener('click', () => {
        body.classList.toggle('light');
        showToast(body.classList.contains('light') ? 'Modo claro activado' : 'Modo nocturno activado');
        updateChartTheme();
    });

    document.getElementById('modeToggle').addEventListener('click', () => {
        state.mode = state.mode === 'Rover' ? 'Base' : 'Rover';
        document.querySelector('.mode-toggle__value').textContent = state.mode;
        showToast(`Modo ${state.mode}`);
    });

    document.getElementById('recordBtn').addEventListener('click', () => {
        state.recording = !state.recording;
        document.getElementById('recordBtn').innerHTML = state.recording
            ? '<i data-lucide="pause"></i><span>Detener registro</span>'
            : '<i data-lucide="radio"></i><span>Iniciar registro</span>';
        showToast(state.recording ? 'Grabando puntos GNSS' : 'Registro detenido');
        lucide.createIcons();
    });

    document.getElementById('copyCoords').addEventListener('click', () => {
        navigator.clipboard.writeText(`${state.gnss.latitude.toFixed(7)}, ${state.gnss.longitude.toFixed(7)}, ${state.gnss.altitude.toFixed(2)}`);
        showToast('Coordenadas copiadas');
    });

    document.getElementById('refreshBtn').addEventListener('click', () => {
        simulateUpdate();
        showToast('Datos actualizados');
    });

    document.getElementById('mapReset').addEventListener('click', () => {
        map.flyTo([state.gnss.latitude, state.gnss.longitude], 17, { duration: 0.6 });
    });

    document.getElementById('mapLayer').addEventListener('click', () => {
        if (state.mapLayer === 'hybrid') {
            map.removeLayer(hybridLayer);
            topoLayer.addTo(map);
            state.mapLayer = 'topo';
            showToast('Capa Topográfica activada');
        } else {
            map.removeLayer(topoLayer);
            hybridLayer.addTo(map);
            state.mapLayer = 'hybrid';
            showToast('Capa Satelital activada');
        }
    });

    document.getElementById('newPointBtn').addEventListener('click', () => {
        const id = `P-${(state.points.length + 21).toString().padStart(3, '0')}`;
        const now = new Date();
        const entry = {
            name: id,
            lat: state.gnss.latitude + (Math.random() - 0.5) * 0.0001,
            lon: state.gnss.longitude + (Math.random() - 0.5) * 0.0001,
            alt: state.gnss.altitude + (Math.random() - 0.5) * 0.5,
            accuracy: Math.max(0.008, state.gnss.horizontalAccuracy + Math.random() * 0.004),
            date: `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
        };
        state.points.unshift(entry);
        updatePoints();
        showToast(`Punto ${entry.name} almacenado`);
    });

    document.getElementById('filesView').addEventListener('click', event => {
        if (event.target.closest('#syncBtn')) {
            state.sync.lastSync = 'Hace instantes';
            state.sync.pending = 0;
            updateFiles();
            lucide.createIcons();
            showToast('Sincronización completada');
        }
    });

    document.getElementById('controlView').addEventListener('click', event => {
        const copy = event.target.closest('[data-copy]');
        if (copy) {
            navigator.clipboard.writeText(copy.dataset.copy);
            showToast('Comando copiado');
        }
        const send = event.target.closest('[data-command]');
        if (send) {
            showToast(`Enviado: ${send.dataset.command}`);
        }
    });
}

function simulateUpdate() {
    const jitter = () => (Math.random() - 0.5) * 0.00005;
    state.gnss.latitude += jitter();
    state.gnss.longitude += jitter();
    state.gnss.altitude += (Math.random() - 0.5) * 0.05;
    state.gnss.horizontalAccuracy = Math.max(0.009, state.gnss.horizontalAccuracy + (Math.random() - 0.5) * 0.002);
    state.gnss.hdop = Math.max(0.6, state.gnss.hdop + (Math.random() - 0.5) * 0.1);
    state.gnss.satellites = Math.max(16, Math.min(32, state.gnss.satellites + Math.round((Math.random() - 0.5) * 2)));
    state.gnss.age = Math.max(0.6, state.gnss.age + (Math.random() - 0.5) * 0.4);

    if (state.gnss.horizontalAccuracy < 0.012) {
        state.gnss.fix = 'RTK Fixed';
    } else if (state.gnss.horizontalAccuracy < 0.02) {
        state.gnss.fix = 'RTK Float';
    } else {
        state.gnss.fix = 'Float';
    }

    state.imu.heading = (state.imu.heading + (Math.random() - 0.5) * 1.5 + 360) % 360;
    state.imu.pitch += (Math.random() - 0.5) * 0.3;
    state.imu.roll += (Math.random() - 0.5) * 0.3;

    state.services[1].status = `Correcciones ${state.gnss.age.toFixed(1)}s`;

    state.satellites.forEach(sat => {
        sat.snr = Math.max(20, Math.min(55, sat.snr + (Math.random() - 0.5) * 2));
    });

    state.events.unshift({ title: 'Estado actualizado', time: 'Ahora mismo' });
    state.events = state.events.slice(0, 5);

    updateStatusCards();
    updateSolution();
    updateConstellations();
    updateServices();
    updateImu();
    updateTimeline();
    updateSatellites();
    updateSnrChart();
    updateMap();
    lucide.createIcons();
}

function init() {
    lucide.createIcons();
    bindMenu();
    bindActions();
    setupMap();
    setupSnrChart();
    updateStatusCards();
    updateSolution();
    updateConstellations();
    updateServices();
    updateImu();
    updateTimeline();
    updateProject();
    updatePoints();
    updateSatellites();
    updateCommands();
    updateProfiles();
    updateFiles();
    updateSessionTimer();

    setInterval(updateSessionTimer, 1000);
    setInterval(simulateUpdate, 5000);
}

document.addEventListener('DOMContentLoaded', init);
