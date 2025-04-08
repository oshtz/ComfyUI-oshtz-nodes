/* Entry point for all web components */
// Dynamically inject oshtz-nodes CSS
const oshtzCssUrl = "/extensions/ComfyUI-oshtz-nodes/css/oshtz-nodes.css";
const link = document.createElement("link");
link.rel = "stylesheet";
link.href = oshtzCssUrl;
link.type = "text/css";
link.onload = () => console.log("[oshtz-nodes] CSS loaded:", oshtzCssUrl);
link.onerror = (e) => console.error("[oshtz-nodes] Failed to load CSS:", oshtzCssUrl, e);
document.head.appendChild(link);

import "./js/lora_switcher.js";
