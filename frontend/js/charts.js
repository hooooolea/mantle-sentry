/* MantleSentry — Analysis page charts */

// --- Load data & render ---

async function init() {
    // Daily summary
    try {
        const resp = await fetch('/api/summary/latest');
        const data = await resp.json();
        if (data.summary_text) {
            document.getElementById('dailySummary').textContent = data.summary_text;
        } else {
            document.getElementById('dailySummary').textContent = '暂无摘要数据，等待 AI 生成...';
        }
    } catch (e) {}

    // Whale table + profit chart
    try {
        const resp = await fetch('/api/whales?limit=10');
        const data = await resp.json();
        const whales = data.whales || [];

        // Table
        const tbody = document.getElementById('whaleTable');
        if (whales.length) {
            tbody.innerHTML = whales.map(w => `
                <tr class="hover:bg-gray-50 cursor-pointer" onclick="window.location.href='/address/${w.address}'">
                    <td class="px-4 py-2 font-mono text-xs truncate">${w.address.slice(0, 14)}...</td>
                    <td class="px-4 py-2"><span class="badge">${w.category || '-'}</span></td>
                    <td class="px-4 py-2 font-semibold text-right">$${(w.total_volume_usd||0).toLocaleString()}</td>
                    <td class="px-4 py-2 text-right">${w.tx_count || 0}</td>
                    <td class="px-4 py-2 text-xs text-gray-600 truncate">${w.ai_profile || '-'}</td>
                </tr>
            `).join('');
        }

        // Profit chart
        if (whales.length) {
            const profitChart = echarts.init(document.getElementById('profitChart'));
            profitChart.setOption({
                tooltip: { trigger: 'axis' },
                xAxis: {
                    type: 'category',
                    data: whales.map(w => w.address.slice(0, 8) + '...'),
                    axisLabel: { fontSize: 10 }
                },
                yAxis: { type: 'value', name: '盈利评分' },
                series: [{
                    type: 'bar',
                    data: whales.map(w => w.profit_score || 0),
                    itemStyle: { color: '#3b82f6' }
                }],
                grid: { left: 50, right: 20, top: 30, bottom: 40 }
            });
        }
    } catch (e) { console.error('Load whales:', e); }

    // Volume trend chart (placeholder with recent tx counts)
    try {
        const resp = await fetch('/api/transactions?limit=200');
        const data = await resp.json();
        const txs = data.transactions || [];

        // Group by hour
        const hourly = {};
        txs.forEach(tx => {
            const h = new Date(tx.timestamp * 1000).toISOString().slice(0, 13);
            hourly[h] = (hourly[h] || 0) + (tx.value_usd || 0);
        });
        const hours = Object.keys(hourly).sort();
        const values = hours.map(h => hourly[h]);

        if (hours.length) {
            const volumeChart = echarts.init(document.getElementById('volumeChart'));
            volumeChart.setOption({
                tooltip: { trigger: 'axis', formatter: p => `${p[0].axisValue}<br/>交易量: $${p[0].value.toLocaleString()}` },
                xAxis: {
                    type: 'category',
                    data: hours.map(h => h.slice(11) + ':00'),
                    axisLabel: { fontSize: 10 }
                },
                yAxis: { type: 'value', name: 'USD' },
                series: [{
                    type: 'line',
                    data: values,
                    smooth: true,
                    areaStyle: { opacity: 0.1 },
                    itemStyle: { color: '#10b981' }
                }],
                grid: { left: 70, right: 20, top: 30, bottom: 40 }
            });
        }
    } catch (e) { console.error('Load volume:', e); }
}

init();
