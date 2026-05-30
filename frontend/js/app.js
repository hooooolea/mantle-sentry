/* MantleSentry — Dashboard logic */

const MAX_FEED_ITEMS = 100;
let txCount = 0;
let isPaused = false;
let prevWhales = {};

function amountClass(usd) {
    if (usd >= 10000) return 'amt-high';
    if (usd >= 100) return 'amt-mid';
    return 'amt-low';
}

function miniSparkline() {
    const w = 50, h = 16;
    const pts = [0.3, 0.5, 0.4, 0.7, 0.6, 0.9, 1.0].map((v, i) =>
        `${i * 8},${h - v * (h - 2)}`).join(' ');
    return `<svg width="${w}" height="${h}" class="opacity-60">
        <polyline points="${pts}" fill="none" stroke="#6366f1" stroke-width="1.5"/>
    </svg>`;
}

// --- Feed item ---
function txItemHTML(tx, isNew) {
    const time = tx.timestamp ? new Date(tx.timestamp * 1000).toLocaleTimeString() : new Date().toLocaleTimeString();
    const hash = (tx.tx_hash || '').slice(0, 10);
    const from = (tx.from || tx.from_address || '').slice(0, 8);
    const to = (tx.to || tx.to_address || '').slice(0, 8);
    const value = tx.value || tx.value_native || 0;
    const valueUsd = tx.value_usd || (value * 0.85);
    const token = tx.token || 'MNT';
    const txType = tx.type || tx.tx_type || '';
    const protocol = tx.protocol && tx.protocol !== 'unknown' ? ` · ${tx.protocol}` : '';
    const whaleClass = tx.is_whale ? 'row-item-highlight' : '';
    const newClass = isNew ? 'animate-highlight' : '';
    const ai = tx.ai_analysis ? `
        <div class="mt-2 ml-24 mr-8">
            <div class="text-xs text-blue-600/80 border border-blue-200 rounded-lg px-3 py-2 bg-blue-50/50">
                <span class="font-medium text-blue-600">AI:</span> ${tx.ai_analysis}
            </div>
        </div>` : '';

    return `
        <div class="row-item ${whaleClass} ${newClass}" onclick="window.open('https://mantlescan.xyz/tx/${tx.tx_hash}','_blank')">
            <div class="grid grid-cols-12 gap-3 items-center">
                <div class="col-span-2">
                    <span class="font-mono-data text-xs text-gray-400" title="${tx.tx_hash}">${hash}...</span>
                </div>
                <div class="col-span-4">
                    <span class="text-xs text-gray-600 truncate block">${from} <span class="text-gray-400">→</span> ${to}<span class="text-gray-400 ml-1">${protocol}</span></span>
                </div>
                <div class="col-span-2 text-right">
                    <div class="font-mono-data text-sm ${amountClass(valueUsd)}">${value.toFixed(2)} ${token}</div>
                    <div class="text-xs text-gray-400 font-mono-data">$${valueUsd.toLocaleString(undefined, {maximumFractionDigits: 0})}</div>
                </div>
                <div class="col-span-2">
                    <span class="badge">${txType}</span>
                </div>
                <div class="col-span-2 text-right">
                    <span class="text-xs text-gray-400 tabular-nums">${time}</span>
                </div>
            </div>
            ${ai}
        </div>
    `;
}

// --- Alert item ---
function alertItemHTML(a) {
    const sevClass = `severity-${a.severity || 'low'}`;
    const time = a.created_at ? new Date(a.created_at).toLocaleTimeString() : '';
    const sevBadge = `badge-severity-${a.severity || 'low'}`;
    const icons = { high: '🔴', medium: '🟡', low: '⚪' };
    const icon = icons[a.severity] || '⚪';
    const addrLink = a.address
        ? `<a href="/address/${a.address}" class="text-blue-600 hover:underline font-mono-data text-xs">${a.address.slice(0, 12)}...</a>`
        : '';

    return `
        <div class="row-item border-l-2 ${sevClass}" onclick="${a.address ? `window.location.href='/address/${a.address}'` : ''}">
            <div class="flex items-start gap-3">
                <span class="mt-0.5 shrink-0">${icon}</span>
                <div class="flex-1 min-w-0">
                    <div class="text-sm font-medium text-gray-800 truncate">${a.description || a.alert_type}</div>
                    <div class="flex items-center gap-2 mt-1">
                        ${addrLink}
                        <span class="badge ${sevBadge}">${a.severity}</span>
                    </div>
                </div>
                <span class="text-xs text-gray-400 shrink-0 tabular-nums">${time}</span>
            </div>
        </div>
    `;
}

// --- Whale item ---
function whaleItemHTML(w, rank) {
    const addr = w.address.slice(0, 10);
    const prevRank = prevWhales[w.address];
    let rankChange = '';
    if (prevRank !== undefined) {
        if (prevRank > rank) rankChange = `<span class="rank-up">↑${prevRank - rank}</span>`;
        else if (prevRank < rank) rankChange = `<span class="rank-down">↓${rank - prevRank}</span>`;
        else rankChange = `<span class="rank-same">-</span>`;
    }
    const vol = w.total_volume_usd || 0;

    return `
        <a href="/address/${w.address}" class="row-item grid grid-cols-12 gap-2 items-center group">
            <div class="col-span-1 flex items-center gap-1">
                <span class="text-xs text-gray-400 font-mono-data">${rank}</span>
                ${rankChange}
            </div>
            <div class="col-span-4">
                <span class="font-mono-data text-xs text-gray-600 group-hover:text-blue-600 transition-colors truncate">${addr}...</span>
            </div>
            <div class="col-span-2">
                <span class="badge-gradient">${w.category || '-'}</span>
            </div>
            <div class="col-span-5 flex items-center justify-end gap-2">
                ${miniSparkline()}
                <span class="text-sm font-semibold text-gray-900 font-mono-data w-24 text-right tabular-nums">$${vol.toLocaleString(undefined, {maximumFractionDigits: 0})}</span>
            </div>
        </a>
    `;
}

// --- Pause ---
function togglePause() {
    isPaused = !isPaused;
    document.getElementById('pauseBtn').textContent = isPaused ? '继续' : '暂停';
}
document.getElementById('txFeed')?.addEventListener('mouseenter', () => {
    if (!isPaused) document.getElementById('txFeed').dataset.hoverPaused = 'true';
});
document.getElementById('txFeed')?.addEventListener('mouseleave', () => {
    document.getElementById('txFeed').dataset.hoverPaused = 'false';
});

// --- / key ---
document.addEventListener('keydown', e => {
    if (e.key === '/' && document.activeElement.tagName !== 'INPUT') {
        e.preventDefault();
        document.getElementById('searchBox')?.focus();
    }
});

// --- API fetch ---
async function loadInitialData() {
    try {
        const resp = await fetch('/api/whales?limit=10');
        const data = await resp.json();
        const el = document.getElementById('whaleList');
        if (data.whales?.length) {
            data.whales.forEach((w, i) => { prevWhales[w.address] = i + 1; });
            el.innerHTML = data.whales.map((w, i) => whaleItemHTML(w, i + 1)).join('');
        }
    } catch (e) {}

    try {
        const resp = await fetch('/api/alerts?limit=10');
        const data = await resp.json();
        const el = document.getElementById('alertList');
        if (data.alerts?.length) {
            el.innerHTML = data.alerts.map(alertItemHTML).join('');
            document.getElementById('alertBadge').textContent = data.alerts.length;
            document.getElementById('alertBadge').classList.remove('hidden');
            document.getElementById('alertBannerCount').textContent = data.alerts.length;
            document.getElementById('alertBanner').classList.remove('hidden');
        }
    } catch (e) {}

    try {
        const resp = await fetch('/api/transactions/whale?limit=20');
        const data = await resp.json();
        const el = document.getElementById('txFeed');
        if (data.transactions?.length) {
            el.innerHTML = data.transactions.map(tx => txItemHTML(tx)).join('');
            txCount = data.transactions.length;
            document.getElementById('txCount').textContent = txCount + ' 笔';
        }
    } catch (e) {}

    try {
        const [txResp, whaleResp, alertResp] = await Promise.all([
            fetch('/api/transactions?limit=200'),
            fetch('/api/whales?limit=50'),
            fetch('/api/alerts?limit=50'),
        ]);
        const txData = await txResp.json();
        const whaleData = await whaleResp.json();
        const alertData = await alertResp.json();
        const txs = txData.transactions || [];
        const totalVolume = txs.reduce((sum, t) => sum + (t.value_usd || 0), 0);
        document.getElementById('statTxCount').textContent = txs.length.toLocaleString();
        document.getElementById('statVolume').textContent = '$' + totalVolume.toLocaleString(undefined, {maximumFractionDigits: 0});
        document.getElementById('statAddresses').textContent = (whaleData.whales || []).length;
        document.getElementById('statAlerts').textContent = (alertData.alerts || []).length;
    } catch (e) {}
}

// --- WebSocket ---
const liveSocket = new LiveSocket((msg) => {
    if (msg.type === 'new_transaction') {
        if (isPaused) return;
        const feed = document.getElementById('txFeed');
        if (feed.dataset.hoverPaused === 'true') return;
        const placeholder = feed.querySelector('.text-center');
        if (placeholder) placeholder.remove();
        feed.insertAdjacentHTML('afterbegin', txItemHTML(msg.data, true));
        txCount++;
        document.getElementById('txCount').textContent = txCount + ' 笔';
        while (feed.children.length > MAX_FEED_ITEMS) feed.lastElementChild.remove();
    }
    if (msg.type === 'alert') {
        const el = document.getElementById('alertList');
        const placeholder = el.querySelector('.text-center');
        if (placeholder) placeholder.remove();
        el.insertAdjacentHTML('afterbegin', alertItemHTML(msg.data));
        const badge = document.getElementById('alertBadge');
        badge.textContent = parseInt(badge.textContent || '0') + 1;
        badge.classList.remove('hidden');
        document.getElementById('alertBannerCount').textContent = badge.textContent;
        document.getElementById('alertBanner').classList.remove('hidden');
    }
});

// --- Search ---
document.getElementById('searchBox')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        const q = e.target.value.trim();
        if (q.startsWith('0x') && q.length === 42) window.location.href = `/address/${q}`;
        else if (q.length === 66) window.open(`https://mantlescan.xyz/tx/${q}`, '_blank');
    }
});

loadInitialData();
