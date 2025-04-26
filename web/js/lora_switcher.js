import { app } from "../../../../scripts/app.js";
import { $el } from "../../../../scripts/ui.js";
import { api } from "../../../../scripts/api.js";

// Store the app instance
let OshtzApp = null;

// Store fetched LoRA names
let LORA_NAMES = ["None"];

// Fetch LoRA names from the custom endpoint
async function fetchLoraNames() {
    try {
        const response = await api.fetchApi("/oshtz-nodes/get-loras");
        if (response.ok) {
            const data = await response.json();
            if (Array.isArray(data) && data.length > 0) {
                LORA_NAMES = data;
            } else {
                console.error("[LoraSwitcherDynamic] Fetched LoRA list is invalid:", data);
                LORA_NAMES = ["None", "ERROR: Fetch Failed"];
            }
        } else {
            console.error("[LoraSwitcherDynamic] Failed to fetch LoRA list:", response.status, response.statusText);
            LORA_NAMES = ["None", `ERROR: ${response.status}`];
        }
    } catch (error) {
        console.error("[LoraSwitcherDynamic] Error fetching LoRA list:", error);
        LORA_NAMES = ["None", "ERROR: Network Error"];
    }
    return LORA_NAMES;
}

// Helper to get the current LoRA config from custom widgets
function getLoraConfigFromWidgets(node) {
    const config = [];
    if (!node.widgets) return config;

    const rowWidgets = node.widgets.filter(w => w.name?.startsWith("lora_row_"));

    // Sort by index stored in the widget's value
    rowWidgets.sort((a, b) => (a.value?.index ?? 0) - (b.value?.index ?? 0));

    for (const widget of rowWidgets) {
        if (widget.value && typeof widget.value === 'object') {
            config.push({
                lora: widget.value.lora,
                strength: widget.value.strength
            });
        }
    }
    return config;
}

// Helper function to find the hidden config input/widget more reliably
function findHiddenConfigWidget(node) {
    // 1. Check node.properties first (Common for hidden/internal data)
    if (node.properties && node.properties.hasOwnProperty("lora_config")) {
            // Return a mock widget object that interacts with node.properties
            return {
            name: "lora_config",
            type: "HIDDEN_PROPERTY", // Custom type to indicate source
            _node: node, // Store reference to the node
            get value() {
                return this._node.properties["lora_config"];
            },
            set value(newValue) {
                this._node.properties["lora_config"] = newValue;
                // Optionally trigger serialization or update if needed
                // node.setDirtyCanvas(true, true); // Example: Mark canvas dirty
            },
            // Add other methods/properties if needed by the caller, e.g., serializeValue
            serializeValue: function() {
                return this.value;
            }
        };
    }

    // 2. Check widgets array directly by name (Original Step 1)
    let configWidget = node.widgets?.find((w) => w.name === "lora_config");
    if (configWidget) {
        return configWidget;
    }

    // 3. Check if it's represented as an input link (Original Step 2)
    const configInput = node.inputs?.find((i) => i.name === "lora_config");
    if (configInput) {
        // If linked, the widget might still be in node.widgets, find by name again or linked widget name
        configWidget = node.widgets?.find((w) => w.name === "lora_config" || (configInput.widget && w.name === configInput.widget.name));
        if (configWidget) {
            return configWidget;
        }
    }

    // 4. Final check: Find any widget named "lora_config" (Original Step 3)
    configWidget = node.widgets?.find((w) => w.name === "lora_config");
    if (configWidget) {
        return configWidget;
    }

    // 5. Check specifically for a widget of type 'hidden' (less common but possible)
    configWidget = node.widgets?.find((w) => w.type?.toLowerCase() === "hidden" && w.name === "lora_config");
    if (configWidget) {
        return configWidget;
    }

    // If not found after all checks, log and return null
    console.error("[LoraSwitcherDynamic] findHiddenConfigWidget could not find the 'lora_config' widget/property."); // Use error log
    return null;
}

// Helper to update the hidden config input
function updateHiddenConfig(node) {
    const config = getLoraConfigFromWidgets(node);
    const jsonConfig = JSON.stringify(config);
    
    try {
        // CRITICAL: Update BOTH property and widget as both are used in different scenarios
        
        // 1. Update the property first
        node.properties = node.properties || {};
        node.properties["lora_config"] = jsonConfig;
        
        // 2. Find the widget - it MUST exist for Python to receive the data
        let hiddenWidget = node.widgets?.find(w => w.name === "lora_config");
        
        // If widget doesn't exist, create it
        if (!hiddenWidget) {
            hiddenWidget = node.addWidget("text", "lora_config", jsonConfig, null, {
                multiline: true,
                hidden: true,
                serialize: true
            });
        } else {
            // Update existing widget
            hiddenWidget.value = jsonConfig;
        }
        
        // Ensure widget is properly hidden AND has serialize flag set to true
        if (hiddenWidget) {
            // Ensure serialize flag is set
            if (!hiddenWidget.serialize) {
                hiddenWidget.serialize = true;
            }
            
            // Extra steps to ensure the widget is truly hidden
            hiddenWidget.hidden = true;
            hiddenWidget.type = "hidden";  // Set type explicitly to hidden
            hiddenWidget.computeSize = function(width) { return [0, -4]; }; // Make it take no space
            hiddenWidget.draw = function() {}; // Empty draw function
        }
        
        node.setDirtyCanvas(true, true);
    } catch (e) {
        console.error("[LoraSwitcherDynamic] Failed to update lora_config:", e);
    }
}

// NEW function to create the widget object (based on old addLoraRow logic)
function createLoraRowWidget(node, index, initialValue = { lora: "None", strength: 1.0 }) {
    const widgetName = `lora_row_${index}`;

    const widget = {
        name: widgetName,
        type: `CUSTOM`,
        value: { ...initialValue, index: index },
        serialize: false, // Prevent direct serialization of this custom widget

        draw: function (ctx, node, widgetWidth, widgetY, widgetHeight) {
            const margin = 10;
            const line_y = widgetY + widgetHeight * 0.5; // Center vertically for text
            const rect = [margin, widgetY, widgetWidth - margin * 2, widgetHeight]; // Example bounding box
            
            // Draw background for the entire widget
            ctx.fillStyle = "rgba(0, 0, 0, 0.3)";
            ctx.fillRect(rect[0], rect[1], rect[2], rect[3]);
            
            // Define index area width and adjust other areas
            const indexWidth = widgetWidth * 0.1;
            const nameWidth = widgetWidth * 0.5;
            const strengthWidth = widgetWidth * 0.2;
            const removeWidth = widgetWidth * 0.1;
            
            // Calculate positions
            const indexX = rect[0];
            const nameX = indexX + indexWidth;
            const strengthX = nameX + nameWidth;
            const removeX = strengthX + strengthWidth;
            
            // Define clickable areas based on layout
            this.hitAreas = this.hitAreas || {}; // Ensure hitAreas exists
            this.hitAreas.index = [indexX, rect[1], indexWidth, rect[3]]; // Make index number clickable too
            this.hitAreas.name = [nameX, rect[1], nameWidth, rect[3]];
            this.hitAreas.strength = [strengthX, rect[1], strengthWidth, rect[3]];
            this.hitAreas.remove = [removeX, rect[1], removeWidth, rect[3]];
            
            // Draw index number with background circle
            const activeIndex = this.value.index + 1; // +1 because active_index is 1-based (0=bypass)
            const circleX = indexX + indexWidth / 2;
            const circleY = line_y;
            const circleRadius = Math.min(indexWidth, widgetHeight) * 0.4;
            
            // Draw circle background for index
            ctx.fillStyle = "#4488ff"; // Bright blue background for index
            ctx.beginPath();
            ctx.arc(circleX, circleY, circleRadius, 0, Math.PI * 2);
            ctx.fill();
            
            // Draw index text
            ctx.fillStyle = "#FFF"; // White text for index number
            ctx.font = "bold 14px Arial";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(activeIndex.toString(), circleX, circleY);
            
            // Helper function to truncate text with ellipsis
            function truncateText(text, maxLength) {
                if (!text) return "None";
                
                // Remove .safetensors extension to save space
                text = text.replace('.safetensors', '');
                
                if (text.length <= maxLength) return text;
                return text.substring(0, maxLength - 3) + "...";
            }
            
            // Draw content (LoRA name, strength, remove button)
            ctx.fillStyle = "#DDD"; // Text color for other elements
            ctx.font = "14px Arial";
            ctx.textAlign = "left";
            ctx.textBaseline = "middle";
            
            // Store full name for tooltip and truncate for display
            const fullLoraName = this.value.lora || "None";
            const truncatedName = truncateText(fullLoraName, 15); // Limit to 15 chars + ellipsis
            
            // Draw truncated LoRA name
            ctx.fillText(truncatedName, nameX + 5, line_y); // Add padding
            
            // Store the full name for potential tooltip functionality
            this.fullLoraName = fullLoraName;
            
            ctx.textAlign = "center";
            ctx.fillText(this.value.strength.toFixed(2), strengthX + strengthWidth / 2, line_y);
            
            ctx.fillStyle = "#F55"; // Red for remove button
            ctx.textAlign = "center";
            ctx.fillText(" X ", removeX + removeWidth / 2, line_y);
        },
        mouse: function (event, pos, node) {
            const widgetHeight = LiteGraph.NODE_WIDGET_HEIGHT; // Or your calculated height
            const widgetY = this.last_y || 0; // Use stored Y position
            
            // Show tooltip on hover over name area
            if (event.type === 'mousemove') {
                for (const areaName in this.hitAreas) {
                    const area = this.hitAreas[areaName];
                    if (pos[0] >= area[0] && pos[0] <= area[0] + area[2] && // Check X
                        pos[1] >= widgetY && pos[1] <= widgetY + widgetHeight) { // Check Y relative to widget
                        
                        if (areaName === 'name' && this.fullLoraName && this.fullLoraName !== "None") {
                            // Set tooltip for the full LoRA name
                            const canvas = node.graph.canvas;
                            if (canvas) {
                                canvas.canvas.title = this.fullLoraName;
                                canvas.setDirty(true, false); // Request redraw without propagating
                            }
                            return true;
                        }
                    }
                }
                
                // Clear tooltip when not over the name area
                const canvas = node.graph.canvas;
                if (canvas && canvas.canvas.title) {
                    canvas.canvas.title = "";
                }
            }
            
            if (event.type === 'pointerdown') {
                for (const areaName in this.hitAreas) {
                    const area = this.hitAreas[areaName];
                    if (pos[0] >= area[0] && pos[0] <= area[0] + area[2] && // Check X
                        pos[1] >= widgetY && pos[1] <= widgetY + widgetHeight) { // Check Y relative to widget

                        if (areaName === 'name') {
                            // Fetch latest LoRA names first, then show menu
                            fetchLoraNames().then(loraNames => {
                                // Format the names for the menu
                                const menuItems = loraNames.map(name => {
                                    return {
                                        content: name,
                                        callback: () => {
                                            this.value.lora = name;
                                            updateHiddenConfig(node);
                                            node.setDirtyCanvas(true, true);
                                        }
                                    };
                                });
                                
                                // Use LiteGraph.ContextMenu for LoRA selection with formatted items
                                new LiteGraph.ContextMenu(menuItems, {
                                    event: event,
                                    callback: null, // We use the per-item callbacks instead
                                    node: node
                                });
                            });
                        } else if (areaName === 'strength') {
                            const newValue = prompt("Enter new strength:", this.value.strength);
                            if (newValue !== null) {
                                const numValue = parseFloat(newValue);
                                if (!isNaN(numValue)) {
                                    this.value.strength = numValue;
                                    updateHiddenConfig(node);
                                    node.setDirtyCanvas(true, true);
                                }
                            }
                        } else if (areaName === 'remove') {
                            const indexToRemove = node.widgets.indexOf(this);
                            if (indexToRemove > -1) {
                                node.widgets.splice(indexToRemove, 1);
                                // Re-index remaining widgets (important!)
                                node.widgets.filter(w => w.type === 'CUSTOM').forEach((w, i) => {
                                    if (w.value) w.value.index = i;
                                    w.name = `lora_row_${i}`;
                                });
                                updateHiddenConfig(node);
                                node.setDirtyCanvas(true, true);
                            }
                        }
                        return true; // Indicate event handled
                    }
                }
            }
            return false; // Event not handled by this widget
        },
    };
    return widget;
}

// NEW function to add standard widgets (button)
function addStandardWidgets(node) {
    const buttonName = "+ Add LoRA";
    
    // Check if button already exists to prevent duplicates
    const existingButton = node.widgets?.find(w => 
        w.type === "button" && 
        w.name === buttonName
    );
    
    if (existingButton) {
        return existingButton;
    }
    
    const buttonWidget = node.addWidget(
        "button",
        buttonName,
        buttonName,
        () => {
            const nextIndex = node.widgets.filter(w => w.type === 'CUSTOM').length;
            const newWidgetObject = createLoraRowWidget(node, nextIndex);
            node.addCustomWidget(newWidgetObject); // Add the actual custom widget instance
            updateHiddenConfig(node);
            node.setDirtyCanvas(true, true);
        },
        {}
    );
    return buttonWidget;
}

// Ensure LoRA names are loaded on startup
fetchLoraNames().catch(err => {
    console.error("[LoraSwitcherDynamic] Failed to fetch initial LoRA list:", err);
});

// Register the extension
app.registerExtension({
    name: "oshtz.LoraSwitcherDynamic",
    async beforeRegisterNodeDef(nodeType, nodeData, appInstance) {
        // Store the app instance for later use in widget handlers
        OshtzApp = appInstance;
        
        // Store LoRA names in the extension for global access
        this.lora_names = await fetchLoraNames().catch(() => ["None"]);

        // Check if the node type matches
        if (nodeData.name === 'LoraSwitcherDynamic') {
            // --- Modify onNodeCreated ---
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                onNodeCreated?.apply(this, arguments);

                // Add standard widgets (button)
                addStandardWidgets(this);

                // Initialize an empty lora_config hidden widget
                // This is CRITICAL - it needs to exist for the data to be passed to Python
                const configWidget = this.addWidget("text", "lora_config", "[]", () => {}, {
                    multiline: true,
                    hidden: true,
                    serialize: true
                });
                
                // Extra steps to ensure the widget is truly hidden from the beginning
                if (configWidget) {
                    configWidget.hidden = true;
                    configWidget.type = "hidden";  // Set type explicitly to hidden
                    configWidget.computeSize = function(width) { return [0, -4]; }; // Make it take no space
                    configWidget.draw = function() {}; // Empty draw function
                }

                // Also set property for backward compatibility
                this.properties = this.properties || {};
                this.properties["lora_config"] = "[]";
                
                // Initial size adjustment
                const computed = this.computeSize();
                this.size = this.size || [0, 0];
                this.size[0] = Math.max(this.size[0], computed?.[0] || 200);
                this.size[1] = Math.max(this.size[1], computed?.[1] || 80);
                this.setDirtyCanvas(true, true);
            };

            // --- Modify onConfigure ---
            const onConfigure = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function (info) {
                 // Call original first IF it exists and does something important
                 // onConfigure?.apply(this, arguments); // Maybe skip if it interferes? Test needed.

                 // Store size before modifying
                 const originalSize = [...(this.size || [0,0])];
                 // Don't clear existing widgets as we want to preserve them

                 // Get saved configuration from properties (more reliable than widget_values)
                 let savedConfig = [];
                 if (this.properties && this.properties["lora_config"]) {
                     try {
                         savedConfig = JSON.parse(this.properties["lora_config"]);
                         if (!Array.isArray(savedConfig)) savedConfig = []; // Ensure it's an array
                     } catch (e) {
                         console.error("[LoraSwitcherDynamic] Failed to parse saved config from properties:", e, "Config was:", this.properties["lora_config"]);
                         savedConfig = [];
                     }
                 } else {
                      savedConfig = [];
                 }

                 // Re-add the standard widgets (button)
                 addStandardWidgets(this);

                 // Find existing LoRA row widgets
                 const existingLoraWidgets = this.widgets?.filter(w => w.type === 'CUSTOM' && w.name?.startsWith('lora_row_')) || [];
                 
                 // Update existing widgets or create new ones as needed
                 for (let i = 0; i < savedConfig.length; i++) {
                     const loraData = savedConfig[i];
                     const cleanData = {
                         lora: loraData.lora || "None",
                         strength: typeof loraData.strength === 'number' ? loraData.strength : 1.0
                     };
                     
                     // Find existing widget with this index
                     const existingWidget = existingLoraWidgets.find(w => w.value?.index === i);
                     
                     if (existingWidget) {
                         // Update existing widget instead of creating a new one
                         existingWidget.value = { ...cleanData, index: i };
                     } else {
                         // Create new widget if none exists at this index
                         const loraWidgetObject = createLoraRowWidget(this, i, cleanData);
                         this.addCustomWidget(loraWidgetObject);
                     }
                 }
                 
                 // Remove any excess widgets if needed
                 const allWidgets = [...this.widgets];
                 for (const widget of allWidgets) {
                     if (widget.type === 'CUSTOM' && widget.name?.startsWith('lora_row_')) {
                         const index = widget.value?.index;
                         if (index !== undefined && index >= savedConfig.length) {
                             const widgetIndex = this.widgets.indexOf(widget);
                             if (widgetIndex > -1) {
                                 this.removeWidget(widgetIndex);
                             }
                         }
                     }
                 }

                 // Get current config from the widgets to ensure it reflects the current state
                 const currentConfig = this.widgets
                     .filter(w => w.type === 'CUSTOM' && w.name?.startsWith('lora_row_')) // Get only our custom LoRA rows
                     .map(w => w.value) // Extract their value object
                     .sort((a, b) => a.index - b.index); // Ensure order by index
                 
                 // Convert to JSON string for storage
                 const jsonConfig = JSON.stringify(currentConfig);
                 
                 // IMPORTANT: We MUST update both the property and the hidden widget
                 // Update the property
                 this.properties = this.properties || {};
                 this.properties["lora_config"] = jsonConfig;
                 
                 // Remove any existing lora_config widget first to avoid duplicates
                 const existingConfigWidget = this.widgets.find(w => w.name === "lora_config");
                 if (existingConfigWidget) {
                     const widgetIndex = this.widgets.indexOf(existingConfigWidget);
                     if (widgetIndex > -1) {
                         this.widgets.splice(widgetIndex, 1);
                     }
                 }
                 
                 // Add the hidden widget with the JSON config - CRITICAL for data to be passed to Python
                 const configWidget = this.addWidget("text", "lora_config", jsonConfig, null, {
                     multiline: true,
                     hidden: true, 
                     serialize: true // This is crucial - tells ComfyUI to pass this to Python!
                 });
                 
                 // Extra steps to ensure the widget is truly hidden
                 if (configWidget) {
                     configWidget.hidden = true;
                     configWidget.type = "hidden";  // Set type explicitly to hidden
                     configWidget.computeSize = function(width) { return [0, -4]; }; // Make it take no space
                     configWidget.draw = function() {}; // Empty draw function
                 }


                 // Optional: Refresh LoRA names list
                 fetchLoraNames().then(names => {
                    // Add safety check to prevent "extensions['oshtz.LoraSwitcherDynamic'] is undefined" error
                    if (app && app.extensions && app.extensions["oshtz.LoraSwitcherDynamic"]) {
                        app.extensions["oshtz.LoraSwitcherDynamic"].lora_names = names || [];
                    } else {
                        console.warn("[LoraSwitcherDynamic] Extension not found when refreshing LoRA names list");
                        // Store names locally as fallback
                        LORA_NAMES = names || ["None"];
                    }
                 }).catch(err => {
                    console.error("[LoraSwitcherDynamic] Error refreshing LoRA names list:", err);
                 });

                 // Adjust size after adding widgets
                 const computed = this.computeSize();
                 this.size = [
                     Math.max(originalSize[0], computed?.[0] || 200),
                     Math.max(originalSize[1], computed?.[1] || 80)
                 ];

                 this.setDirtyCanvas(true, true);
            };

            // --- Overwrite onSerialize to store config in properties --- 
            const onSerialize = nodeType.prototype.onSerialize;
            nodeType.prototype.onSerialize = function(o) {
                // Call original if needed
                onSerialize?.apply(this, arguments);

                // REMOVED: Logic that searched for lora_config widget and manually set properties.
                // This is now handled correctly by updateHiddenConfig directly modifying node.properties.
                // ComfyUI's default serialization will save node.properties.
            }

            // --- Keep nodeCreated callback ---
            nodeType.prototype.nodeCreated = function(node, app) {
                if (node.constructor.nodeData.name === "LoraSwitcherDynamic") {
                    // Initial update might be useful if properties aren't loaded yet
                    // updateHiddenConfig(node);
                }
            }
        }
    },
});
