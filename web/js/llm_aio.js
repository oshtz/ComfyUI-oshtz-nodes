import { app } from "../../../../scripts/app.js";
import { api } from "../../../../scripts/api.js";

const MODEL_ENDPOINT = "/oshtz-nodes/llm-models";
const PROVIDER_MODELS = {};
const fetchPromises = {};

async function fetchProviderModels(provider, force = false) {
    if (!provider) {
        return [];
    }
    const cacheKey = `${provider}:${force ? "force" : "cached"}`;
    if (fetchPromises[cacheKey]) {
        return fetchPromises[cacheKey];
    }

    const params = new URLSearchParams({ provider });
    if (force) {
        params.set("force", "1");
    }

    fetchPromises[cacheKey] = api.fetchApi(`${MODEL_ENDPOINT}?${params.toString()}`)
        .then(async (response) => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const data = await response.json();
            const models = Array.isArray(data?.models) ? data.models : [];
            PROVIDER_MODELS[provider] = models;
            return models;
        })
        .catch((err) => {
            console.error(`[LLMAIONode] Failed to fetch ${provider} models:`, err);
            return PROVIDER_MODELS[provider] || [];
        })
        .finally(() => {
            delete fetchPromises[cacheKey];
        });
    return fetchPromises[cacheKey];
}

function updateModelWidget(node, provider, models) {
    const modelWidget = node.widgets?.find((w) => w.name === "model");
    if (!modelWidget || !models?.length) {
        return;
    }

    modelWidget.options = modelWidget.options || {};
    const existingValues = modelWidget.options.values || [];
    const changedLength = existingValues.length !== models.length;
    const changedContent = changedLength || models.some((model, index) => existingValues[index] !== model);
    if (changedContent) {
        modelWidget.options.values = models;
    }
    if (!models.includes(modelWidget.value)) {
        modelWidget.value = models[0] || "";
    }
    node.setDirtyCanvas(true, true);
}

function refreshModelsForProvider(node, provider, force = false) {
    fetchProviderModels(provider, force)
        .then((models) => updateModelWidget(node, provider, models))
        .catch((err) => {
            console.error(`[LLMAIONode] Failed to refresh ${provider} models:`, err);
        });
}

function attachProviderWatcher(node) {
    const providerWidget = node.widgets?.find((w) => w.name === "api_type");
    if (!providerWidget || providerWidget._oshtzProviderWatcherAttached) {
        return;
    }
    providerWidget._oshtzProviderWatcherAttached = true;
    const originalCallback = providerWidget.callback;
    providerWidget.callback = function () {
        originalCallback?.apply(this, arguments);
        refreshModelsForProvider(node, providerWidget.value, providerWidget.value === "openrouter");
    };
}

function initializeNode(node) {
    attachProviderWatcher(node);
    const providerWidget = node.widgets?.find((w) => w.name === "api_type");
    const provider = providerWidget?.value || "openai";
    refreshModelsForProvider(node, provider, provider === "openrouter");
}

app.registerExtension({
    name: "oshtz.LLMAIONode",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        const comfyClass = nodeType.comfyClass || nodeData.name;
        if (comfyClass !== "LLMAIONode") {
            return;
        }

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            onNodeCreated?.apply(this, arguments);
            initializeNode(this);
        };

        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            onConfigure?.apply(this, arguments);
            initializeNode(this);
        };
    },
});
