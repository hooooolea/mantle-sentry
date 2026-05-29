/* MantleSentry — Dashboard logic */

const MAX_FEED_ITEMS = 100;
let txCount = 0;

// --- Render helpers ---

function txItemHTML(tx) {
    const whaleClass = tx.is_whale ? 'tx-whale' : '';
    const time = tx.timestamp ? new Date(tx.timestamp * 1000).toLocaleTimeString() : new Date().toLocaleTimeString();
    const hash = (tx.tx_hash || '').slice(0, 14);
    const from = (tx.from || tx.from_address || '').slice(0, 10);
    const to = (tx.to || tx.to_address || '').slice(0, 10);
    const value = tx.value || tx.value_native || 0;
    const valueUsd = tx.value_usd || (value * 0.85);
    const token = tx.token || 'MNT';
    const txType = tx.type || tx.tx_type || '';
    const protocol = tx.protocol && tx.protocol !== 'unknown' ? `<span class="badge">${tx.protocol}</span>` : '';
    const ai = tx.ai_analysis ? `<div class="text-xs text-blue-600 mt-1">AI: ${tx.ai_analysis}</div>` : '';

    return `
        <div class="p-3 hover:bg-gray-50 cursor-pointer feed-item-new ${whaleClass}"
             onclick="window.open('https://mantlescan.xyz/tx/${tx.tx_hash}','_blank')">
            <div class="flex justify-between items-center">
                <span class="font-mono text-xs text-gray-600">${hash}...</span>
                <span class="text-sm font-semibold ${valueUsd >= 10000 ? 'text-red-600' : 'text-gray-800'}">${value.toFixed(4)} ${token} <span class="text-xs text-gray-400">($${valueUsd.toFixed(2)})</span></span>
            </div>
            <div class="text-xs text-gray-500 mt-1">${from}... → ${to}... · ${txType} ${protocol} · ${time}</div>
            ${ai}
        </div>
    `;
}

function alertItemHTML(a) {
    const sevClass = `alert-${a.severity || 'low'}`;
    return `
        <div class="p-3 ${sevClass}">
            <div class="text-sm font-medium">${a.description || a.alert_type}</div>
            <div class="text-xs text-gray-500 mt-1">${a.address ? a.address.slice(0, 12) + '...' : ''} · ${a.severity}</div>
        </div>
    `;
}

function whaleItemHTML(w, rank) {
    return `
        <a href="/address/${w.address}" class="flex items-center justify-between p-3 hover:bg-gray-50 group">
            <div class="flex items-center gap-2">
                <span class="text-xs text-gray-400 w-5">${rank}</span>
                <span class="font-mono text-xs group-hover:text-blue-600">${w.address.slice(0, 10)}...</span>
                <span class="badge">${w.category || '-'}</span>
            </div>
            <span class="text-sm font-semibold">$${(w.total_volume_usd || 0).toLocaleString()}</span>
        </a>
    `;
}

// --- API fetch ---

async function loadInitialData() {
    // Whale list
    try {
        const resp = await fetch('/api/whales?limit=10');
        const data = await resp.json();
        const el = document.getElementById('whaleList');
        if (data.whales?.length) {
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
}

// --- WebSocket handler ---

const liveSocket = new LiveSocket((msg) => {
    if (msg.type === 'new_transaction') {
        const feed = document.getElementById('txFeed');
        // Remove placeholder
        const placeholder = feed.querySelector('.text-center');
        if (placeholder) placeholder.remove();

        feed.insertAdjacentHTML('afterbegin', txItemHTML(msg.data));
        txCount++;
        document.getElementById('txCount').textContent = txCount + ' 笔';

        // Trim old items
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
