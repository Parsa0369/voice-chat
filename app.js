function log(message) {
    let box = document.getElementById("logs");

    if (!box) {
        box = document.createElement("div");
        box.id = "logs";
        box.style.background = "#111";
        box.style.color = "#0f0";
        box.style.padding = "10px";
        box.style.margin = "10px";
        box.style.fontFamily = "Consolas";
        box.style.whiteSpace = "pre-wrap";
        box.style.border = "1px solid #555";
        document.body.prepend(box);
    }

    const time = new Date().toLocaleTimeString();

    box.innerHTML += `[${time}] ${message}<br>`;
}

log("🚀 شروع برنامه");

const ws = new WebSocket("wss://voice-server.my-ac2-in-l.workers.dev/ws");

ws.onopen = () => {
    log("✅ اتصال برقرار شد");
    ws.send("سلام از GitHub Pages");
};

ws.onmessage = (event) => {
    log("📨 پیام سرور:");
    log(event.data);
};

ws.onerror = (error) => {
    log("❌ خطا در WebSocket");
    console.error(error);
};

ws.onclose = (event) => {
    log("🔒 اتصال بسته شد");
    log("Code: " + event.code);
    log("Reason: " + event.reason);
};
