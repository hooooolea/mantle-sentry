/* MantleSentry — Dashboard logic */

const MAX_FEED_ITEMS = 100;
let txCount = 0;
let isPaused = false;
let prevWhales = {};

// --- Amount color tier ---
function amountClass(usd) {
    if (usd >= 10000) return 'amt-high';
    if (usd >= 100) return 'amt-mid';
    return 'amt-low';
}

// --- Mini sparkline SVG ---
function miniSparkline() {
    const w = 60, h = 20;
    const pts = [0.3, 0.5, 0.4, 0.7, 0.6, 0.9, 1.0].map((v, i) =>
        `${i * 10},${h - v * (h - 2)}`).join(' ');
    return `<svg width="${w}" height="${h}" class="opacity-70">
        <polyline points="${pts}" fill="none" stroke="#3b82f6" stroke-width="1.5"/>
    </svg>`;
}

// --- Render helpers ---

function txItemHTML(tx) {
    const whaleClass = tx.is_whale ? 'tx-whale' : '';
    const time = tx.timestamp ? new Date(tx.timestamp * 1000).toLocaleTimeString() : new Date().toLocaleTimeString();
    const hash = (tx.tx_hash || '').slice(0, 10);
    const from = (tx.from || tx.from_address || '').slice(0, 8);
    const to = (tx.to || tx.to_address || '').slice(0, 8);
    const value = tx.value || tx.value_native || 0;
    const valueUsd = tx.value_usd || (value * 0.85);
    const token = tx.token || 'MNT';
    const txType = tx.type || tx.tx_type || '';
    const protocol = tx.protocol && tx.protocol !== 'unknown' ? ` · ${tx.protocol}` : '';
    const ai = tx.ai_analysis ? `<div class="text-xs text-blue-600 mt-1">AI: ${tx.ai_analysis}</div>` : '';

    return `
        <div class="card-body hover:bg-gray-50 cursor-pointer feed-item-new ${whaleClass}"
             onclick="window.open('https://mantlescan.xyz/tx/${tx.tx_hash}','_blank')">
            <div class="flex items-center gap-3">
                <span class="font-mono text-xs text-gray-400 w-24 shrink-0" title="${tx.tx_hash}">${hash}...</span>
                <span class="text-xs text-gray-500 flex-1 truncate">${from} → ${to} · ${txType}${protocol}</span>
                <span class="text-xs text-gray-400 shrink-0">${time}</span>
                <span class="text-sm ${amountClass(valueUsd)} shrink-0 text-right w-32">
                    ${value.toFixed(2)} ${token}<br><span class="text-xs">$${valueUsd.toFixed(0)}</span>
                </span>
            </div>
            ${ai}
        </div>
    `;
}

function alertItemHTML(a) {
    const sevClass = `alert-${a.severity || 'low'}`;
    const time = a.created_at ? new Date(a.created_at).toLocaleTimeString() : '';
    const addrLink = a.address
        ? `<a href="/address/${a.address}" class="text-blue-600 hover:underline">${a.address.slice(0, 12)}...</a>`
        : '';
    return `
        <div class="card-body ${sevClass}">
            <div class="flex justify-between">
                <span class="text-sm font-medium">${a.description || a.alert_type}</span>
                <span class="text-xs text-gray-400 shrink-0">${time}</span>
            </div>
            <div class="text-xs text-gray-500 mt-1">${addrLink} · ${a.severity}</div>
        </div>
    `;
}

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
        <a href="/address/${w.address}" class="flex items-center justify-between card-body hover:bg-gray-50 group">
            <div class="flex items-center gap-2 min-w-0">
                <span class="text-xs text-gray-400 w-5 shrink-0">${rank}</span>
                ${rankChange}
                <span class="font-mono text-xs group-hover:text-blue-600 truncate">${addr}...</span>
                <span class="badge shrink-0">${w.category || '-'}</span>
            </div>
            <div class="flex items-center gap-2 shrink-0">
                ${miniSparkline()}
                <span class="text-sm font-semibold w-20 text-right">$${vol.toLocaleString(undefined, {maximumFractionDigits: 0})}</span>
            </div>
        </a>
    `;
}

// --- Pause toggle ---
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

// --- / key to focus search ---
document.addEventListener('keydown', e => {
    if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
        e.preventDefault();
        document.getElementById('searchBox')?.focus();
    }
});

// --- API fetch ---

async function loadInitialData() {
    // Whale list
    try {
        const resp = await fetch('/api/whales?limit=10');
        const data = await resp.json();
        const el = document.getElementById('whaleList');
        if (data.whales?.length) {
            data.whales.forEach((w, i) => { prevWhales[w.address] = i + 1; });
            el.innerHTML = data.whales.map((w, i) => whaleItemHTML(w, i + 1)).join('');
        }
    } catch (e) { console.error('Load whales:', e); }

    // Alerts
    try {
        const resp = await fetch('/api/alerts?limit=10');
        const data = await resp.json();
        const el = document.getElementById('alertList');
        if (data.alerts?.length) {
            el.innerHTML = data.alerts.map(alertItemHTML).join('');
            const badge = document.getElementById('alertBadge');
            badge.textContent = data.alerts.length;
            badge.classList.remove('hidden');
            document.getElementById('alertBannerCount').textContent = data.alerts.length;
            document.getElementById('alertBanner').classList.remove('hidden');
        }
    } catch (e) { console.error('Load alerts:', e); }

    // Recent whale txs
    try {
        const resp = await fetch('/api/transactions/whale?limit=20');
        const data = await resp.json();
        const el = document.getElementById('txFeed');
        if (data.transactions?.length) {
            el.innerHTML = data.transactions.map(tx => txItemHTML(tx)).join('');
            txCount = data.transactions.length;
            document.getElementById('txCount').textContent = txCount + ' 笔';
        }
    } catch (e) { console.error('Load txs:', e); }

    // Latest summary
    try {
        const resp = await fetch('/api/summary/latest');
        const data = await resp.json();
        if (data.summary_text) {
            document.getElementById('summaryText').textContent = data.summary_text;
            document.getElementById('summaryBanner').classList.remove('hidden');
        }
    } catch (e) {}

    // Stats bar
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
        document.getElementById('statTxCount').textContent = txs.length;
        document.getElementById('statVolume').textContent = '$' + totalVolume.toLocaleString(undefined, {maximumFractionDigits: 0});
        document.getElementById('statAddresses').textContent = (whaleData.whales || []).length;
        document.getElementById('statAlerts').textContent = (alertData.alerts || []).length;
    } catch (e) { console.error('Load stats:', e); }
}

// --- WebSocket handler ---

const liveSocket = new LiveSocket((msg) => {
    if (msg.type === 'new_transaction') {
        if (isPaused) return;
        const feed = document.getElementById('txFeed');
        if (feed.dataset.hoverPaused === 'true') return;

        const placeholder = feed.querySelector('.text-center');
        if (placeholder) placeholder.remove();

        feed.insertAdjacentHTML('afterbegin', txItemHTML(msg.data));
        txCount++;
        document.getElementById('txCount').textContent = txCount + ' 笔';

        while (feed.children.length > MAX_FEED_ITEMS) {
            feed.lastElementChild.remove();
        }
    }

    if (msg.type === 'alert') {
        const el = document.getElementById('alertList');
        const placeholder = el.querySelector('.text-center');
        if (placeholder) placeholder.remove();
        el.insertAdjacentHTML('afterbegin', alertItemHTML(msg.data));

        const badge = document.getElementById('alertBadge');
        badge.textContent = parseInt(badge.textContent || '0') + 1;
        badge.classList.remove('hidden');

        document.getElementById('alertBannerCount').textContent = parseInt(badge.textContent);
        document.getElementById('alertBanner').classList.remove('hidden');
    }
});

// --- Search ---
document.getElementById('searchBox')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        const q = e.target.value.trim();
        if (q.startsWith('0x') && q.length === 42) {
            window.location.href = `/address/${q}`;
        } else if (q.length === 66) {
            window.open(`https://mantlescan.xyz/tx/${q}`, '_blank');
        }
    }
});

// --- Init ---
loadInitialData();
