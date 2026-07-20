const ws = new WebSocket("wss://voice-server.my-ac2-in-l.workers.dev/ws");

ws.onopen = () => {
    console.log("Connected!");

    ws.send("سلام از مرورگر");
};

ws.onmessage = (event) => {
    console.log("Server:", event.data);
};

ws.onclose = () => {
    console.log("Disconnected");
};
