import { app } from "../../../../scripts/app.js";
import { api } from "../../../../scripts/api.js";

const MODEL_ENDPOINT = "/oshtz-nodes/llm-models";
const REFRESH_WIDGET_LABEL = "Refresh Models";
const TOAST_SUMMARY = "LLM AIO";
const TOAST_LIFE = 5000;
let PROVIDER_MODELS = {};
let fetchPromise = null;

function toErrorMessage(err, fallback = "Unexpected error") {
    if (!err) {
        return fallback;
    }
    if (typeof err === "string") {
        return err;
    }
    if (err.detail) {
        return err.detail;
    }
    if (err.message) {
        return err.message;
    }
    return fallback;
}

function showErrorToast(detail, severity = "error") {
    const message = detail || "Something went wrong";
    const toastManager = app?.extensionManager?.toast;
    if (toastManager?.add) {
        toastManager.add({
            severity,
            summary: TOAST_SUMMARY,
            detail: message,
            life: TOAST_LIFE,
        });
        return;
    }
    if (app?.ui?.showToast) {
        app.ui.showToast(message);
        return;
    }
    if (app?.ui?.dialog?.show) {
        app.ui.dialog.show(`${TOAST_SUMMARY}: ${message}`);
    }
}

function handleModelRefreshError(provider, error) {
    const normalized = normalizeProvider(provider) || "provider";
    console.error(`[LLMAIONode] Failed to refresh ${normalized} models:`, error);
    showErrorToast(toErrorMessage(error, `Failed to refresh ${normalized} models`));
}

function findWidget(node, name) {
    return node.widgets?.find((w) => w.name === name);
}

function getRefreshButton(node) {
    return node.widgets?.find((w) => w.name === REFRESH_WIDGET_LABEL && w.type === "button");
}

function getOpenAIApiKey(node) {
    const widget = findWidget(node, "openai_api_key");
    const value = widget?.value ?? "";
    return typeof value === "string" ? value.trim() : "";
}

function getAnthropicApiKey(node) {
    const widget = findWidget(node, "anthropic_api_key");
    const value = widget?.value ?? "";
    return typeof value === "string" ? value.trim() : "";
}

function getGeminiApiKey(node) {
    const widget = findWidget(node, "gemini_api_key");
    const value = widget?.value ?? "";
    return typeof value === "string" ? value.trim() : "";
}

function normalizeProvider(provider) {
    if (!provider && provider !== 0) {
        return "";
    }
    const value = provider.toString().toLowerCase();
    if (value === "claude") {
        return "anthropic";
    }
    return value;
}

async function requestModels({ provider, force = false, openaiApiKey = "", anthropicApiKey = "", geminiApiKey = "" } = {}) {
    const normalized = normalizeProvider(provider) || undefined;
    const trimmedKey = typeof openaiApiKey === "string" ? openaiApiKey.trim() : "";
    const trimmedAnthropicKey = typeof anthropicApiKey === "string" ? anthropicApiKey.trim() : "";
    const trimmedGeminiKey = typeof geminiApiKey === "string" ? geminiApiKey.trim() : "";
    const useSecureRequest =
        (normalized === "openai" && trimmedKey) ||
        (normalized === "anthropic" && trimmedAnthropicKey) ||
        (normalized === "gemini" && trimmedGeminiKey);
    let url = MODEL_ENDPOINT;
    let options;
    if (useSecureRequest) {
        const payload = {
            provider: normalized,
            force: force ? 1 : 0,
        };
        if (trimmedKey) {
            payload.openai_api_key = trimmedKey;
        }
        if (trimmedAnthropicKey) {
            payload.anthropic_api_key = trimmedAnthropicKey;
        }
        if (trimmedGeminiKey) {
            payload.gemini_api_key = trimmedGeminiKey;
        }
        options = {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        };
    } else {
        const params = new URLSearchParams();
        if (normalized) {
            params.set("provider", normalized);
        }
        if (force) {
            params.set("force", "1");
        }
        const query = params.toString();
        if (query) {
            url = `${MODEL_ENDPOINT}?${query}`;
        }
    }
    const response = await api.fetchApi(url, options);
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    if (normalized) {
        const responseProvider = normalizeProvider(data?.provider ?? normalized);
        const models = (data && data.models) || [];
        if (responseProvider) {
            PROVIDER_MODELS[responseProvider] = models;
        }
        const errorMessage = typeof data?.error === "string" ? data.error.trim() : "";
        if (errorMessage) {
            showErrorToast(errorMessage);
        }
        return models;
    }
    const normalizedMap = {};
    Object.entries(data || {}).forEach(([key, value]) => {
        const normalizedKey = normalizeProvider(key);
        if (normalizedKey) {
            normalizedMap[normalizedKey] = value;
        }
    });
    PROVIDER_MODELS = normalizedMap;
    return PROVIDER_MODELS;
}

async function fetchModelMap(force = false) {
    if (fetchPromise && !force) {
        return fetchPromise;
    }
    fetchPromise = requestModels({ force })
        .catch((err) => {
            console.error("[LLMAIONode] Failed to fetch model map:", err);
            showErrorToast(toErrorMessage(err, "Failed to fetch model list"));
            return PROVIDER_MODELS;
        })
        .finally(() => {
            fetchPromise = null;
        });
    return fetchPromise;
}

function getProviderModels(provider) {
    const normalized = normalizeProvider(provider);
    return (PROVIDER_MODELS && normalized && PROVIDER_MODELS[normalized]) || [];
}

function refreshProviderModels(node, provider) {
    const normalized = normalizeProvider(provider);
    if (normalized === "openai") {
        const apiKey = getOpenAIApiKey(node);
        if (!apiKey) {
            return Promise.resolve([]);
        }
        return requestModels({ provider: normalized, force: true, openaiApiKey: apiKey });
    }
    if (normalized === "anthropic") {
        const apiKey = getAnthropicApiKey(node);
        if (!apiKey) {
            return Promise.resolve([]);
        }
        return requestModels({ provider: normalized, force: true, anthropicApiKey: apiKey });
    }
    if (normalized === "gemini") {
        const apiKey = getGeminiApiKey(node);
        if (!apiKey) {
            return Promise.resolve([]);
        }
        return requestModels({ provider: normalized, force: true, geminiApiKey: apiKey });
    }
    if (normalized === "openrouter") {
        return requestModels({ provider: normalized, force: true });
    }
    return Promise.resolve([]);
}

function canRefreshProvider(node, provider) {
    const normalized = normalizeProvider(provider);
    if (normalized === "openai") {
        return !!getOpenAIApiKey(node);
    }
    if (normalized === "anthropic") {
        return !!getAnthropicApiKey(node);
    }
    if (normalized === "gemini") {
        return !!getGeminiApiKey(node);
    }
    if (normalized === "openrouter") {
        return true;
    }
    return false;
}

function updateRefreshButtonState(node) {
    const button = getRefreshButton(node);
    if (!button) {
        return;
    }
    const providerWidget = findWidget(node, "api_type");
    const provider = providerWidget?.value;
    const normalized = normalizeProvider(provider);
    button.disabled = !canRefreshProvider(node, normalized);
}

function handleRefreshButtonClick(node, button) {
    const providerWidget = findWidget(node, "api_type");
    const provider = providerWidget?.value;
    const normalized = normalizeProvider(provider);
    if (!normalized || !canRefreshProvider(node, normalized)) {
        console.warn("[LLMAIONode] Refresh requested without a valid provider/API key");
        updateRefreshButtonState(node);
        return;
    }
    button.disabled = true;
    refreshProviderModels(node, normalized)
        .then(() => updateModelWidget(node, normalized, false))
        .catch((err) => {
            console.error(`[LLMAIONode] Manual refresh failed for ${normalized}:`, err);
            showErrorToast(toErrorMessage(err, `Manual refresh failed for ${normalized}`));
        })
        .finally(() => {
            updateRefreshButtonState(node);
        });
}

function ensureRefreshButton(node) {
    let button = getRefreshButton(node);
    if (button) {
        return button;
    }
    let buttonRef;
    const onClick = () => handleRefreshButtonClick(node, buttonRef);
    buttonRef = node.addWidget("button", REFRESH_WIDGET_LABEL, REFRESH_WIDGET_LABEL, onClick, {
        serialize: false,
    });
    buttonRef.serialize = false;
    buttonRef.disabled = true;
    return buttonRef;
}

function updateModelWidget(node, provider, attemptRefresh = true) {
    const modelWidget = findWidget(node, "model");
    if (!modelWidget) {
        return;
    }
    const normalized = normalizeProvider(provider);
    updateRefreshButtonState(node);
    const models = getProviderModels(normalized);
    if (!models.length) {
        modelWidget.options = modelWidget.options || {};
        if (modelWidget.options.values && modelWidget.options.values.length) {
            modelWidget.options.values = [];
            modelWidget.value = "";
        }

        node.setDirtyCanvas(true, true);
        if (attemptRefresh && (normalized === "openrouter" || normalized === "openai" || normalized === "anthropic" || normalized === "gemini")) {
            refreshProviderModels(node, normalized)
                .then(() => updateModelWidget(node, normalized, false))
                .catch((err) => {
                    handleModelRefreshError(normalized, err);
                });
        }
        return;
    }

    modelWidget.options = modelWidget.options || {};
    const existingValues = modelWidget.options.values || [];
    const changedLength = existingValues.length !== models.length;
    const changedContent = changedLength || models.some((m, idx) => existingValues[idx] !== m);
    if (changedContent) {
        modelWidget.options.values = models;
    }
    if (modelWidget.type !== "combo") {
        modelWidget.type = "combo";
    }
    if (!models.includes(modelWidget.value)) {
        modelWidget.value = models[0] || "";
    }
    node.setDirtyCanvas(true, true);
}

function attachProviderWatcher(node) {
    const providerWidget = findWidget(node, "api_type");
    if (!providerWidget || providerWidget._oshtzProviderWatcherAttached) {
        return;
    }
    providerWidget._oshtzProviderWatcherAttached = true;
    const originalCallback = providerWidget.callback;
    providerWidget.callback = function () {
        originalCallback?.apply(this, arguments);
        const provider = providerWidget.value;
        const normalized = normalizeProvider(provider);
        if (normalized === "openrouter" || normalized === "openai" || normalized === "anthropic" || normalized === "gemini") {
            updateModelWidget(node, normalized, true);
        } else {
            updateModelWidget(node, normalized, false);
        }
        updateRefreshButtonState(node);
    };
}

function attachOpenAIKeyWatcher(node) {
    const keyWidget = findWidget(node, "openai_api_key");
    if (!keyWidget || keyWidget._oshtzOpenAIWatcherAttached) {
        return;
    }
    keyWidget._oshtzOpenAIWatcherAttached = true;
    const originalCallback = keyWidget.callback;
    keyWidget.callback = function () {
        originalCallback?.apply(this, arguments);
        const providerWidget = findWidget(node, "api_type");
        const provider = providerWidget?.value;
        const normalized = normalizeProvider(provider);
        if (normalized === "openai") {
            updateModelWidget(node, normalized, true);
        }
        updateRefreshButtonState(node);
    };
}

function attachAnthropicKeyWatcher(node) {
    const keyWidget = findWidget(node, "anthropic_api_key");
    if (!keyWidget || keyWidget._oshtzAnthropicWatcherAttached) {
        return;
    }
    keyWidget._oshtzAnthropicWatcherAttached = true;
    const originalCallback = keyWidget.callback;
    keyWidget.callback = function () {
        originalCallback?.apply(this, arguments);
        const providerWidget = findWidget(node, "api_type");
        const provider = providerWidget?.value;
        const normalized = normalizeProvider(provider);
        if (normalized === "anthropic") {
            updateModelWidget(node, normalized, true);
        }
        updateRefreshButtonState(node);
    };
}

function attachGeminiKeyWatcher(node) {
    const keyWidget = findWidget(node, "gemini_api_key");
    if (!keyWidget || keyWidget._oshtzGeminiWatcherAttached) {
        return;
    }
    keyWidget._oshtzGeminiWatcherAttached = true;
    const originalCallback = keyWidget.callback;
    keyWidget.callback = function () {
        originalCallback?.apply(this, arguments);
        const providerWidget = findWidget(node, "api_type");
        const provider = providerWidget?.value;
        const normalized = normalizeProvider(provider);
        if (normalized === "gemini") {
            updateModelWidget(node, normalized, true);
        }
        updateRefreshButtonState(node);
    };
}

function initializeNode(node) {
    attachProviderWatcher(node);
    attachOpenAIKeyWatcher(node);
    attachAnthropicKeyWatcher(node);
    attachGeminiKeyWatcher(node);
    ensureRefreshButton(node);
    const providerWidget = findWidget(node, "api_type");
    let providerValue = "openai";
    if (providerWidget) {
        const normalizedValue = normalizeProvider(providerWidget.value || "openai") || "openai";
        if (providerWidget.value !== normalizedValue) {
            providerWidget.value = normalizedValue;
        }
        providerValue = normalizedValue;
    }
    const normalized = normalizeProvider(providerValue || "openai") || "openai";
    const attemptRefresh = normalized === "openrouter" || normalized === "openai" || normalized === "anthropic" || normalized === "gemini";
    updateModelWidget(node, normalized, attemptRefresh);
}

fetchModelMap().catch((err) => {
    console.error("[LLMAIONode] Initial model fetch failed:", err);
    showErrorToast(toErrorMessage(err, "Initial model fetch failed"));
});

app.registerExtension({
    name: "oshtz.LLMAIONode",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "LLMAIONode") {
            return;
        }
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            onNodeCreated?.apply(this, arguments);
            const node = this;
            node.__oshtzConfigured = false;
            if (node.__oshtzInitTimer) {
                clearTimeout(node.__oshtzInitTimer);
            }
            node.__oshtzInitTimer = setTimeout(() => {
                node.__oshtzInitTimer = null;
                if (!node.__oshtzConfigured) {
                    initializeNode(node);
                }
            }, 0);
        };

        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            onConfigure?.apply(this, arguments);
            this.__oshtzConfigured = true;
            if (this.__oshtzInitTimer) {
                clearTimeout(this.__oshtzInitTimer);
                this.__oshtzInitTimer = null;
            }
            initializeNode(this);
        };
    },
});
