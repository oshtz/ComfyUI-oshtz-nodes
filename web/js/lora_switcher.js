import { app } from "../../../../scripts/app.js";
import { $el } from "../../../../scripts/ui.js";
import { api } from "../../../../scripts/api.js";

const DEFAULT_LORA_WIDGET_DATA = {
    lora: "None",
    strength: 1.0,
};

const LORA_SWITCHER_STYLE = {
    rowBackgroundColor: null,
    widgetOutlineColor: LiteGraph.WIDGET_OUTLINE_COLOR,
    combo: {
        backgroundColor: "#353535",
        textColor: "#DDD",
        arrowColor: "#AAA",
    },
    number: {
        backgroundColor: "#353535",
        textColor: "#DDD",
    },
    removeButton: {
        backgroundColor: "#F44336",
        textColor: "#FFFFFF",
        outlineColor: LiteGraph.WIDGET_OUTLINE_COLOR,
    },
    addButton: {
        backgroundColor: "#4CAF50",
        textColor: "#FFFFFF",
        outlineColor: LiteGraph.WIDGET_OUTLINE_COLOR,
    }
};

if (!window.LiteGraph) window.LiteGraph = {};



// Patch LiteGraph to force widget draw calls
function patchLiteGraphWidgetDraw() {
    if (LiteGraph._oshtz_widget_draw_patched) return;
    LiteGraph._oshtz_widget_draw_patched = true;

    const originalDrawNodeWidgets = LiteGraph.drawNodeWidgets;
    LiteGraph.drawNodeWidgets = function(node, ctx, posY) {
        const res = originalDrawNodeWidgets.call(this, node, ctx, posY);
        if (!node.widgets) return res;
        for (const widget of node.widgets) {
            if (typeof widget.draw === "function") {
                try {
                    widget.draw(ctx, node, node.size[0], widget.last_y ?? 0, widget.size ? widget.size[1] : LiteGraph.NODE_WIDGET_HEIGHT);
                } catch (e) {
                    console.warn("Widget draw error", e);
                }
            }
        }
        return res;
    };
}

patchLiteGraphWidgetDraw();

async function patchLoraSwitcherDynamic(nodeType) {
    if (!nodeType || nodeType.prototype._oshtz_patched) return;
    console.log("[LoraSwitcherDynamic] Patch applied");
    nodeType.prototype._oshtz_patched = true;

    const onNodeCreated = nodeType.prototype.onNodeCreated;
    const onConfigure = nodeType.prototype.configure;
    const onExecute = nodeType.prototype.onExecute;
    const onDrawForegroundOriginal = nodeType.prototype.onDrawForeground;

    nodeType.prototype.onNodeCreated = function() {
        onNodeCreated?.apply(this, arguments);
        this.lora_count = 0;

        const addLoraButton = this.addWidget("button", "+ Add LoRA", null, () => this.addLoraWidgets());
        addLoraButton.draw = function(ctx, node, widget_width, y, widget_height) {
            const margin = 10;
            const styles = LORA_SWITCHER_STYLE.addButton;
            const outline_color = styles.outlineColor;
            const background_color = styles.backgroundColor;
            const text_color = styles.textColor;
            const text = this.label || this.name;
            const pos = this.pos || [margin, y];
            const size = this.size || [widget_width - margin * 2, widget_height];
            const button_bounding = [pos[0], pos[1], size[0], size[1]];

            ctx.fillStyle = background_color;
            ctx.fillRect(...button_bounding);
            ctx.strokeStyle = outline_color;
            ctx.strokeRect(...button_bounding);

            if (text) {
                ctx.fillStyle = text_color;
                ctx.textAlign = "center";
                ctx.font = node.canvas.button_font || "14px Arial";
                ctx.fillText(text, pos[0] + size[0] * 0.5, pos[1] + size[1] * 0.7);
            }
        };
        this.widgets_values = this.widgets_values || [];
    };

    nodeType.prototype.computeSize = function(out) {
        let width = LiteGraph.NODE_WIDTH;
        let height = LiteGraph.NODE_TITLE_HEIGHT;
        let widgets_height = 0;
        let maxWidgetWidth = 0;
        const loraRowPadding = 5;

        if (this.widgets && this.widgets.length > 0) {
            for (let i = 0; i < this.widgets.length; ++i) {
                const widget = this.widgets[i];
                if (widget.name && widget.name.endsWith("_num")) continue;

                let widgetHeight = 0;
                let widgetWidth = 0;

                if (widget.computeSize) {
                    const computed = widget.computeSize(this.size ? this.size[0] : width);
                    widgetWidth = computed[0];
                    widgetHeight = computed[1];
                } else {
                    widgetHeight = LiteGraph.NODE_WIDGET_HEIGHT;
                    widgetWidth = this.size ? this.size[0] : width;
                }

                widgets_height += widgetHeight + LiteGraph.NODE_WIDGET_PADDING;

                if (widget.name && widget.name.endsWith("_remove")) {
                    widgets_height += loraRowPadding;
                }
                maxWidgetWidth = Math.max(maxWidgetWidth, widgetWidth);
            }
            if (widgets_height > 0) {
                widgets_height += LiteGraph.NODE_WIDGET_PADDING;
            }
        }

        height += widgets_height;

        const inputsHeight = this.inputs ? this.inputs.length * LiteGraph.NODE_SLOT_HEIGHT : 0;
        const outputsHeight = this.outputs ? this.outputs.length * LiteGraph.NODE_SLOT_HEIGHT : 0;
        height = Math.max(height, inputsHeight + LiteGraph.NODE_TITLE_HEIGHT);
        height = Math.max(height, outputsHeight + LiteGraph.NODE_TITLE_HEIGHT);
        height += LiteGraph.NODE_TITLE_HEIGHT * 0.5;
        width = Math.max(width, maxWidgetWidth);
        width = isFinite(width) ? width : LiteGraph.NODE_WIDTH;
        height = isFinite(height) ? height : 100;

        const finalSize = [width, height];
        if (out) {
            out[0] = finalSize[0];
            out[1] = finalSize[1];
        }
        return finalSize;
    };

    nodeType.prototype.configure = async function(info) {
        this.widgets = this.widgets?.filter(w => !w.name || (!w.name.startsWith("lora_") && w.name !== "+ Add LoRA")) || [];
        this.lora_count = 0;

        onConfigure?.apply(this, arguments);

        if (!this.widgets.find(w => w.name === "+ Add LoRA")) {
            this.addWidget("button", "+ Add LoRA", null, () => this.addLoraWidgets());
        }

        const loraValuesToRestore = info.widgets_values || [];
        if (loraValuesToRestore.length > 0) {
            console.log("[LoraSwitcherDynamic] Restoring LoRA widgets from widgets_values:", loraValuesToRestore);
            await Promise.all(loraValuesToRestore.map(loraData => {
                if (typeof loraData === 'object' && loraData !== null && 'lora' in loraData && 'strength' in loraData) {
                    return this.addLoraWidgets(loraData);
                } else {
                    console.warn("[LoraSwitcherDynamic] Skipping invalid saved LoRA data during configure:", loraData);
                    return Promise.resolve();
                }
            }));
        } else {
            console.log("[LoraSwitcherDynamic] No valid widgets_values found to restore LoRAs during configure.");
        }
        this.setDirtyCanvas(true, true);
    };

    nodeType.prototype.addLoraWidgets = async function(initialValue = null) {
        this.lora_count++;
        const index = this.lora_count;
        const prefix = `lora_${index}`;
        const defaultValue = initialValue || { ...DEFAULT_LORA_WIDGET_DATA };

        let lora_names = ["None"];
        try {
            const response = await api.fetchApi("/oshtz-nodes/get-loras");
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const custom_loras = await response.json();
            if (!custom_loras.includes("None")) {
                lora_names = ["None", ...custom_loras];
            } else {
                lora_names = custom_loras;
            }
            console.log("[LoraSwitcherDynamic] Fetched LoRAs via custom /oshtz-nodes/get-loras");
        } catch (error) {
            console.error("[LoraSwitcherDynamic] Failed to fetch LoRA names via custom endpoint:", error);
        }

        const nameWidget = this.addWidget(
            "combo", `${prefix}_name`, defaultValue.lora, (value) => {},
            { values: lora_names, serialize: false }
        );
        if (!lora_names.includes(defaultValue.lora)) nameWidget.value = "None";
        nameWidget.draw = function(ctx, node, widget_width, y, widget_height) {
            const styles = LORA_SWITCHER_STYLE.combo;
            const outline_color = LORA_SWITCHER_STYLE.widgetOutlineColor;
            const bounds = [this.pos[0], this.pos[1], this.size[0], this.size[1]];

            ctx.fillStyle = styles.backgroundColor;
            ctx.fillRect(...bounds);
            ctx.strokeStyle = outline_color;
            ctx.strokeRect(...bounds);

            ctx.fillStyle = styles.textColor;
            ctx.textAlign = "left";
            ctx.font = node.canvas.button_font || "14px Arial";
            const text_offset_x = 5;
            ctx.fillText(this.value, bounds[0] + text_offset_x, bounds[1] + widget_height * 0.7);
        };

        const strengthWidget = this.addWidget("number", `${prefix}_strength`, defaultValue.strength, (v) => {}, {
            min: -10.0, max: 10.0, step: 0.01, precision: 2, serialize: true
        });
        strengthWidget.draw = function(ctx, node, widget_width, y, widget_height) {
            const styles = LORA_SWITCHER_STYLE.number;
            const outline_color = LORA_SWITCHER_STYLE.widgetOutlineColor;
            const bounds = [this.pos[0], this.pos[1], this.size[0], this.size[1]];

            ctx.fillStyle = styles.backgroundColor;
            ctx.fillRect(...bounds);
            ctx.strokeStyle = outline_color;
            ctx.strokeRect(...bounds);

            ctx.fillStyle = styles.textColor;
            ctx.textAlign = "center";
            ctx.font = node.canvas.button_font || "14px Arial";
            ctx.fillText(this.value.toFixed(this.options.precision || 2), bounds[0] + bounds[2] * 0.5, bounds[1] + widget_height * 0.7);
        };

        const removeWidget = this.addWidget("button", `${prefix}_remove`, `Remove LoRA ${index}`, () => {
            this.removeLoraWidget(index);
        }, { serialize: false });
        removeWidget.draw = function(ctx, node, widget_width, y, widget_height) {
            const styles = LORA_SWITCHER_STYLE.removeButton;
            const outline_color = styles.outlineColor;
            const background_color = styles.backgroundColor;
            const text_color = styles.textColor;
            const text = this.label || this.name;
            const bounds = [this.pos[0], this.pos[1], this.size[0], this.size[1]];

            ctx.fillStyle = background_color;
            ctx.fillRect(...bounds);
            ctx.strokeStyle = outline_color;
            ctx.strokeRect(...bounds);

            if (text) {
                ctx.fillStyle = text_color;
                ctx.textAlign = "center";
                ctx.font = node.canvas.button_font || "14px Arial";
                ctx.fillText(text, bounds[0] + bounds[2] * 0.5, bounds[1] + bounds[3] * 0.7);
            }
        };

        const buttonIndex = this.widgets.findIndex(w => w.name === "+ Add LoRA");
        const insertIndex = (buttonIndex === -1) ? this.widgets.length : buttonIndex;
        const addedWidgets = [nameWidget, strengthWidget, removeWidget];
        const currentIndices = addedWidgets.map(w => this.widgets.indexOf(w)).filter(i => i !== -1).sort((a, b) => a - b);

        if (currentIndices.length === addedWidgets.length && currentIndices[0] >= insertIndex) {
            for (let i = addedWidgets.length - 1; i >= 0; i--) {
                const widgetToRemove = addedWidgets[i];
                const idxToRemove = this.widgets.indexOf(widgetToRemove);
                if (idxToRemove !== -1) this.widgets.splice(idxToRemove, 1);
            }
            this.widgets.splice(insertIndex, 0, ...addedWidgets);
        } else if (currentIndices.length !== addedWidgets.length) {
            console.error("[LoraSwitcherDynamic] Error finding newly added widgets to move them.");
            this.widgets = this.widgets.filter(w => !addedWidgets.includes(w));
            this.widgets.splice(insertIndex, 0, ...addedWidgets);
        }
        this.updateWidgetsValues?.();
        this.setDirtyCanvas(true, true);
    };

    nodeType.prototype.removeLoraWidget = function(indexToRemove) {
        const prefix = `lora_${indexToRemove}`;
        const widgetsToRemove = this.widgets.filter(w => w.name && w.name.startsWith(prefix) && !w.name.endsWith("_num"));
        if (widgetsToRemove.length > 0) {
            this.widgets = this.widgets.filter(w => !widgetsToRemove.includes(w));
            this.renumberLoraWidgets();
            this.updateWidgetsValues?.();
            this.setDirtyCanvas(true, true);
        } else {
            console.warn(`[LoraSwitcherDynamic] Could not find widgets to remove for index ${indexToRemove}`);
        }
    };

    nodeType.prototype.renumberLoraWidgets = function() {
        let currentLoraIndex = 1;
        const loraWidgetGroups = {};

        this.widgets.forEach(widget => {
            if (widget.name && widget.name.startsWith("lora_")) {
                const parts = widget.name.split('_');
                if (parts.length >= 3) {
                    const index = parseInt(parts[1], 10);
                    const type = parts.slice(2).join('_');
                    if (!isNaN(index) && type && type !== 'num') {
                        if (!loraWidgetGroups[index]) loraWidgetGroups[index] = {};
                        loraWidgetGroups[index][type] = widget;
    nodeType.prototype.updateWidgetsValues = function() {
        const loraData = [];
        for (let i = 1; i <= this.lora_count; i++) {
            const nameWidget = this.widgets.find(w => w.name === `lora_${i}_name`);
            const strengthWidget = this.widgets.find(w => w.name === `lora_${i}_strength`);
            if (nameWidget && strengthWidget) {
                loraData.push({ lora: nameWidget.value || "None", strength: strengthWidget.value });
            }
        }
        this.widgets_values = loraData;
        console.log("[LoraSwitcherDynamic] widgets_values updated:", JSON.stringify(this.widgets_values));
    };
}
                }
            }
        });

        const sortedIndices = Object.keys(loraWidgetGroups).map(Number).sort((a, b) => a - b);
        sortedIndices.forEach(originalIndex => {
            const group = loraWidgetGroups[originalIndex];
            const newPrefix = `lora_${currentLoraIndex}`;
            const newIndex = currentLoraIndex;

            if (group.name) group.name.name = `${newPrefix}_name`;
            if (group.strength) group.strength.name = `${newPrefix}_strength`;
            if (group.remove) {
                group.remove.name = `${newPrefix}_remove`;
                group.remove.callback = () => { this.removeLoraWidget(newIndex); };
            }
            currentLoraIndex++;
        });
        this.lora_count = currentLoraIndex - 1;
    };

    nodeType.prototype.onExecute = function() {
        const loraData = [];
        for (let i = 1; i <= this.lora_count; i++) {
            const nameWidget = this.widgets.find(w => w.name === `lora_${i}_name`);
            const strengthWidget = this.widgets.find(w => w.name === `lora_${i}_strength`);
            if (nameWidget && strengthWidget) {
                loraData.push({ lora: nameWidget.value || "None", strength: strengthWidget.value });
            }
        }
        this.widgets_values = loraData;
        console.log("[LoraSwitcherDynamic] Data being set in onExecute:", JSON.stringify(this.widgets_values));
        return onExecute?.apply(this, arguments);
    };

    nodeType.prototype.onDrawForeground = function(ctx) {
        onDrawForegroundOriginal?.apply(this, arguments);
        if (!this.widgets) return;

        const activeIndexWidget = this.widgets.find(w => w.name === "active_index");
        const widgetHeight = LiteGraph.NODE_WIDGET_HEIGHT;
        const standardPadding = LiteGraph.NODE_WIDGET_PADDING;
        let rowStartY = LiteGraph.NODE_TITLE_HEIGHT + standardPadding;

        if (activeIndexWidget) {
            activeIndexWidget.last_y = rowStartY;
            rowStartY += (activeIndexWidget.computeSize ? activeIndexWidget.computeSize()[1] : widgetHeight) + standardPadding;
        }

        const loraRowPadding = 5;
        const rowTotalHeight = widgetHeight + standardPadding + loraRowPadding;
        const nodeWidth = this.size[0];
        const margin = 10;
        const spacing = 5;
        const removeWidth = 60;
        const strengthWidth = 60;
        const nameWidth = nodeWidth - margin * 2 - strengthWidth - removeWidth - spacing * 2;

        let currentY = rowStartY;
        let currentLoraIndex = 1;
        let lastLoraWidgetY = 0;

        while (true) {
            const prefix = `lora_${currentLoraIndex}`;
            const nameWidget = this.widgets.find(w => w.name === `${prefix}_name`);
            const strengthWidget = this.widgets.find(w => w.name === `${prefix}_strength`);
            const removeWidget = this.widgets.find(w => w.name === `${prefix}_remove`);

            if (!nameWidget || !strengthWidget || !removeWidget) break;

            let currentX = margin;

            nameWidget.last_y = currentY;
            nameWidget.pos = [currentX, currentY];
            nameWidget.size = [nameWidth, widgetHeight];
            currentX += nameWidth + spacing;

            strengthWidget.last_y = currentY;
            strengthWidget.pos = [currentX, currentY];
            strengthWidget.size = [strengthWidth, widgetHeight];
            currentX += strengthWidth + spacing;

            removeWidget.last_y = currentY;
            removeWidget.pos = [currentX, currentY];
            removeWidget.size = [removeWidth, widgetHeight];

            lastLoraWidgetY = currentY;
            currentY += rowTotalHeight;
            currentLoraIndex++;
        }

        const addButton = this.widgets.find(w => w.name === "+ Add LoRA");
        if (addButton) {
            const buttonY = (lastLoraWidgetY > 0) ? lastLoraWidgetY + rowTotalHeight : rowStartY;
            addButton.last_y = buttonY;
            addButton.pos = [margin, buttonY];
            addButton.size = [nodeWidth - margin * 2, widgetHeight];
        }
    };

    const originalSerialize = nodeType.prototype.serialize;
    nodeType.prototype.serialize = function() {
        const info = originalSerialize ? originalSerialize.call(this) : {};
        info.widgets_values = this.widgets_values || [];
        return info;
    };
}

// Immediately patch if node already registered
const existing = LiteGraph.registered_node_types?.["oshtz Nodes/LoraSwitcherDynamic"];
if (existing) {
    patchLoraSwitcherDynamic(existing);
}

// Register extension to patch when node is registered
app.registerExtension({
    name: "OshtzNodes.LoraSwitcherDynamic",
    async beforeRegisterNodeDef(nodeType, nodeData, appRef) {
        if (nodeData.name === "LoraSwitcherDynamic") {
            patchLoraSwitcherDynamic(nodeType);
        }
    }
});
