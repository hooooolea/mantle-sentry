/* MantleSentry — Dashboard logic */

const MAX_FEED_ITEMS = 100;
let txCount = 0;
let isPaused = false;
let prevWhales = {};
let currentFilter = 'all';   // 筛选 tab 状态

// ── 金额颜色（绿色系，符合金融惯例：大额 = 醒目）
function amountClass(usd) {
    if (usd >= 100000) return 'amt-whale';
    if (usd >= 10000)  return 'amt-high';
    if (usd >= 100)    return 'amt-mid';
    return 'amt-low';
}

// ── 交易类型 badge（CoinGecko-style 彩色 pill）
const TYPE_BADGE = {
    swap:     'badge-type-swap',
    defi:     'badge-type-defi',
    transfer: 'badge-type-transfer',
    bridge:   'badge-type-bridge',
    mint:     'badge-type-mint',
    burn:     'badge-type-burn',
};
function typeBadge(txType) {
    const t = (txType || '').toLowerCase();
    const cls = TYPE_BADGE[t] || 'badge';
    return `<span class="${cls}">${txType || '—'}</span>`;
}

// ── Sparkline SVG（小趋势线）
function miniSparkline() {
    const w = 48, h = 16;
    const pts = [0.3, 0.5, 0.4, 0.7, 0.6, 0.9, 1.0].map((v, i) =>
        `${i * 8},${h - v * (h - 2)}`).join(' ');
    return `<svg width="${w}" height="${h}" class="opacity-50 shrink-0">
        <polyline points="${pts}" fill="none" stroke="#10b981" stroke-width="1.5" stroke-linejoin="round"/>
    </svg>`;
}

// ── Feed item HTML
function txItemHTML(tx, isNew) {
    const time     = tx.timestamp ? new Date(tx.timestamp * 1000).toLocaleTimeString() : new Date().toLocaleTimeString();
    const hash     = (tx.tx_hash || '').slice(0, 10);
    const from     = (tx.from || tx.from_address || '').slice(0, 8);
    const to       = (tx.to || tx.to_address || '').slice(0, 8);
    const value    = tx.value || tx.value_native || 0;
    const valueUsd = tx.value_usd || (value * 0.64);
    const token    = tx.token || 'MNT';
    const txType   = tx.type || tx.tx_type || '';
    const protocol = tx.protocol && tx.protocol !== 'unknown' ? `<span class="text-gray-300 mx-0.5">·</span><span class="text-gray-400">${tx.protocol}</span>` : '';
    const whaleRow = tx.is_whale ? 'row-item-whale' : '';
    const newCls   = isNew ? 'animate-highlight' : '';
    const ai = tx.ai_analysis ? `
        <div class="mt-2 text-xs text-blue-600/80 border border-blue-100 rounded-lg px-3 py-1.5 bg-blue-50/60 ml-24 mr-4">
            <span class="font-semibold text-blue-500">AI</span> ${tx.ai_analysis}
        </div>` : '';

    // 筛选：如果当前有 filter，不匹配则隐藏
    const filterType = (txType || '').toLowerCase();
    const hidden = (
        currentFilter === 'whale'    && !tx.is_whale       ||
        currentFilter === 'swap'     && filterType !== 'swap'     ||
        currentFilter === 'transfer' && filterType !== 'transfer'
    ) ? 'hidden' : '';

    return `
        <div class="row-item ${whaleRow} ${newCls} ${hidden}" data-type="${filterType}" data-whale="${tx.is_whale ? '1' : '0'}"
             onclick="window.open('https://mantlescan.xyz/tx/${tx.tx_hash}','_blank')">
            <div class="grid grid-cols-12 gap-3 items-center">
                <div class="col-span-2">
                    <span class="font-mono-data text-xs text-gray-400" title="${tx.tx_hash}">${hash}…</span>
                </div>
                <div class="col-span-4 flex items-center gap-1 min-w-0">
                    <span class="text-xs text-gray-700 font-mono-data truncate">${from}</span>
                    <span class="text-gray-300 text-xs">→</span>
                    <span class="text-xs text-gray-700 font-mono-data truncate">${to}</span>
                    ${protocol}
                </div>
                <div class="col-span-2 text-right">
                    <div class="font-mono-data text-sm font-semibold ${amountClass(valueUsd)}">${value.toFixed(2)} <span class="text-[10px] font-normal opacity-60">${token}</span></div>
                    <div class="text-xs text-gray-400 font-mono-data">$${valueUsd.toLocaleString(undefined, {maximumFractionDigits: 0})}</div>
                </div>
                <div class="col-span-2">${typeBadge(txType)}</div>
                <div class="col-span-2 text-right">
                    <span class="text-xs text-gray-400 tabular-nums">${time}</span>
                </div>
            </div>
            ${ai}
        </div>
    `;
}

// ── Alert item HTML
function alertItemHTML(a) {
    const sevClass  = `severity-${a.severity || 'low'}`;
    const time      = a.created_at ? new Date(a.created_at).toLocaleTimeString() : '';
    const sevBadge  = `badge-severity-${a.severity || 'low'}`;
    const icons     = { high: '🟠', medium: '🔵', low: '⚪' };
    const icon      = icons[a.severity] || '⚪';
    const addrLink  = a.address
        ? `<a href="/address/${a.address}" class="text-blue-500 hover:underline font-mono-data text-xs">${a.address.slice(0, 12)}…</a>`
        : '';

    return `
        <div class="row-item border-l-2 ${sevClass}" onclick="${a.address ? `window.location.href='/address/${a.address}'` : ''}">
            <div class="flex items-start gap-3">
                <span class="mt-0.5 shrink-0 text-sm">${icon}</span>
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

// ── Whale item HTML
function whaleItemHTML(w, rank) {
    const addr     = w.address.slice(0, 10);
    const prevRank = prevWhales[w.address];
    let rankChange = '';
    if (prevRank !== undefined) {
        if (prevRank > rank)      rankChange = `<span class="rank-up">↑${prevRank - rank}</span>`;
        else if (prevRank < rank) rankChange = `<span class="rank-down">↓${rank - prevRank}</span>`;
        else                      rankChange = `<span class="rank-same">—</span>`;
    }
    const vol = w.total_volume_usd || 0;

    return `
        <a href="/address/${w.address}" class="row-item grid grid-cols-12 gap-2 items-center group">
            <div class="col-span-1 flex items-center gap-1">
                <span class="text-xs text-gray-400 font-mono-data tabular-nums">${rank}</span>
                ${rankChange}
            </div>
            <div class="col-span-4">
                <span class="font-mono-data text-xs text-gray-600 group-hover:text-blue-500 transition-colors">${addr}…</span>
            </div>
            <div class="col-span-2">
                <span class="badge-gradient text-[9px]">${w.category || '—'}</span>
            </div>
            <div class="col-span-5 flex items-center justify-end gap-2">
                ${miniSparkline()}
                <span class="text-sm font-semibold text-gray-900 font-mono-data tabular-nums">$${vol.toLocaleString(undefined, {maximumFractionDigits: 0})}</span>
            </div>
        </a>
    `;
}

// ── Feed 筛选 Tab
document.querySelectorAll('.feed-tab').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.feed-tab').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentFilter = btn.dataset.filter;
        // 根据 filter 显示/隐藏已有的 row-item
        document.querySelectorAll('#txFeed .row-item').forEach(row => {
            const type  = row.dataset.type || '';
            const whale = row.dataset.whale === '1';
            let show = true;
            if (currentFilter === 'whale')    show = whale;
            if (currentFilter === 'swap')     show = type === 'swap';
            if (currentFilter === 'transfer') show = type === 'transfer';
            row.classList.toggle('hidden', !show);
        });
    });
});

// ── Pause / resume
function togglePause() {
    isPaused = !isPaused;
    document.getElementById('pauseBtn').textContent = isPaused ? '继续' : '暂停';
}
document.getElementById('txFeed')?.addEventListener('mouseenter', () => {
    document.getElementById('txFeed').dataset.hoverPaused = 'true';
});
document.getElementById('txFeed')?.addEventListener('mouseleave', () => {
    document.getElementById('txFeed').dataset.hoverPaused = 'false';
});

// ── / 键聚焦搜索
document.addEventListener('keydown', e => {
    if (e.key === '/' && document.activeElement.tagName !== 'INPUT') {
        e.preventDefault();
        document.getElementById('searchBox')?.focus();
    }
});

// ── Search
document.getElementById('searchBox')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        const q = e.target.value.trim();
        if (q.startsWith('0x') && q.length === 42) window.location.href = `/address/${q}`;
        else if (q.length === 66) window.open(`https://mantlescan.xyz/tx/${q}`, '_blank');
    }
});

// ── 更新 Ticker Bar
function updateTicker(txs, whales) {
    const totalVol   = txs.reduce((s, t) => s + (t.value_usd || 0), 0);
    const whaleTxs   = txs.filter(t => t.is_whale_tx).length;
    const addrs      = new Set([...txs.map(t => t.from_address), ...txs.map(t => t.to_address)].filter(Boolean)).size;
    document.getElementById('tickerTx').textContent    = txs.length.toLocaleString();
    document.getElementById('tickerVol').textContent   = '$' + (totalVol / 1e6).toFixed(2) + 'M';
    document.getElementById('tickerAddr').textContent  = addrs.toLocaleString();
    document.getElementById('tickerWhale').textContent = whaleTxs.toLocaleString();
}

// ── MNT 价格轮询（每 60 秒）
async function updateMntPrice() {
    try {
        const data = await fetch('/api/price/mnt').then(r => r.json());
        if (data.price) {
            document.getElementById('tickerMntPrice').textContent = '$' + data.price.toFixed(4);
        }
    } catch (e) {}
}
updateMntPrice();
setInterval(updateMntPrice, 60000);

// ── 初始数据加载
async function loadInitialData() {
    // Whales
    try {
        const data = await fetch('/api/whales?limit=10').then(r => r.json());
        const el   = document.getElementById('whaleList');
        if (data.whales?.length) {
            data.whales.forEach((w, i) => { prevWhales[w.address] = i + 1; });
            el.innerHTML = data.whales.map((w, i) => whaleItemHTML(w, i + 1)).join('');
        }
    } catch (e) {}

    // Alerts
    try {
        const data = await fetch('/api/alerts?limit=10').then(r => r.json());
        const el   = document.getElementById('alertList');
        if (data.alerts?.length) {
            el.innerHTML = data.alerts.map(alertItemHTML).join('');
            document.getElementById('alertBadge').textContent = data.alerts.length;
            document.getElementById('alertBadge').classList.remove('hidden');
            document.getElementById('alertBannerCount').textContent = data.alerts.length;
            document.getElementById('alertBanner').classList.remove('hidden');
        }
    } catch (e) {}

    // Recent whale txs for feed
    try {
        const data = await fetch('/api/transactions/whale?limit=20').then(r => r.json());
        const el   = document.getElementById('txFeed');
        if (data.transactions?.length) {
            el.innerHTML = data.transactions.map(tx => txItemHTML(tx)).join('');
            txCount = data.transactions.length;
            document.getElementById('txCount').textContent = txCount + ' 笔';
        }
    } catch (e) {}

    // Stats + Ticker
    try {
        const [txData, whaleData, alertData] = await Promise.all([
            fetch('/api/transactions?limit=200').then(r => r.json()),
            fetch('/api/whales?limit=50').then(r => r.json()),
            fetch('/api/alerts?limit=50').then(r => r.json()),
        ]);
        const txs        = txData.transactions || [];
        const totalVolume = txs.reduce((s, t) => s + (t.value_usd || 0), 0);
        document.getElementById('statTxCount').textContent  = txs.length.toLocaleString();
        document.getElementById('statVolume').textContent   = '$' + totalVolume.toLocaleString(undefined, {maximumFractionDigits: 0});
        document.getElementById('statAddresses').textContent = (whaleData.whales || []).length;
        document.getElementById('statAlerts').textContent   = (alertData.alerts || []).length;
        updateTicker(txs, whaleData.whales || []);
    } catch (e) {}
}

// ── WebSocket 实时推送
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
        document.getElementById('tickerTx').textContent = txCount.toLocaleString();
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

loadInitialData();
