/* WebSocket client — auto-reconnect */

class LiveSocket {
    constructor(onMessage) {
        this.onMessage = onMessage;
        this.ws = null;
        this.reconnectDelay = 1000;
        this.connect();
    }

    connect() {
        const proto = location.protocol === 'https:' ? 'wss' : 'ws';
        this.ws = new WebSocket(`${proto}://${location.host}/ws/live`);

        this.ws.onopen = () => {
            console.log('[WS] Connected');
            this.reconnectDelay = 1000;
            const dot = document.getElementById('statusDot');
            if (dot) { dot.classList.remove('bg-gray-400'); dot.classList.add('bg-green-500'); }
        };

        this.ws.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);
                this.onMessage(data);
            } catch (err) {
                console.error('[WS] Parse error:', err);
            }
        };

        this.ws.onclose = () => {
            console.log('[WS] Disconnected, reconnecting...');
            const dot = document.getElementById('statusDot');
            if (dot) { dot.classList.remove('bg-green-500'); dot.classList.add('bg-gray-400'); }
            setTimeout(() => this.connect(), this.reconnectDelay);
            this.reconnectDelay = Math.min(this.reconnectDelay * 2, 10000);
        };

        this.ws.onerror = () => this.ws.close();
    }

    send(data) {
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    }
}
