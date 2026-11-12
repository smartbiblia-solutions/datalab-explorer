import * as kshf from "../dist/keshif.min.js";

// --- Helper: Infer column types ---
function inferColumnTypes(data) {
    if (!Array.isArray(data) || data.length === 0) return [];
    const sample = data.slice(0, 10);
    const keys = Object.keys(sample[0]);
    return keys.map(key => {
        let values = sample.map(row => row[key]);
        let type = "string";
        if (values.every(v => typeof v === "number" || (!isNaN(parseFloat(v)) && v !== "" && v !== null))) {
            type = "number";
        } else if (values.every(v => !isNaN(Date.parse(v)))) {
            type = "date";
        }
        return {
            field: key,
            name: key,
            type: type,
            panel: "middle", // default, user can change
            include: false,
            collapsed: false,
            multi: false,
            separator: "|" // Default for multi-cat
        };
    });
}

let originalData = null;
let schemaTable = null;

// --- Show schema editor ---
export function showSchemaEditor(data, initialSummaries = [], initialRecordDisplay = {}) {
    originalData = data;
    $("#kshfDashboard").hide();
    $("#schemaEditorContainer").show();
    $("#editSchemaBtn").hide();
    if (schemaTable) schemaTable.destroy();

    let inferredSchema = inferColumnTypes(data);
    if (initialSummaries && initialSummaries.length > 0) {
        inferredSchema = inferredSchema.map(col => {
            const prev = initialSummaries.find(s => s.name === col.field);
            // If a column from the data matches a summary in the config,
            // merge the config's properties and mark it for inclusion.
            return prev ? { ...col, ...prev, include: true } : col;
        });
    }

    schemaTable = new Tabulator("#schemaEditor", {
        data: inferredSchema,
        layout: "fitDataStretch",
        columns: [
            { title: "Include", field: "include", formatter:"tickCross", editor:true, width:70, headerFilter:"tickCross" },
            { title: "Column Name", field: "field", editor: false, width: 120, headerFilter:"input" },
            { title: "Display Name", field: "name", editor: "input", width: 140, headerFilter:"input" },
            { title: "Type", field: "type", editor: "select", editorParams: {values:["string", "number", "date"]}, width:100, headerFilter:"select", headerFilterParams:{values:["","string","number","date"]} },
            { title: "Panel", field: "panel", editor: "select", editorParams: {values:["left", "middle", "right", "bottom"]}, width:110, headerFilter:"select", headerFilterParams:{values:["","left","middle","right","bottom"]} },
            { title: "Collapsed", field: "collapsed", formatter:"tickCross", editor:true, width:90, headerFilter:"tickCross" },
            { title: "Multi-cat Split", field: "multi", formatter:"tickCross", editor:true, width:110, headerFilter:"tickCross" },
            { 
                title: "Separator", field: "separator", editor: "input", width: 90,
                editable: (cell) => cell.getRow().getData().multi === true,
                validator: [{ type: "minLen", param: 1, message: "Separator required" }],
                headerFilter:"input"
            },
            { 
                title: "Sample Value", 
                field: "sample_value", 
                width: 150, 
                formatter: (cell) => {
                    let field = cell.getRow().getData().field;
                    if (originalData && originalData.length > 0) {
                        let val = originalData[0][field];
                        if (typeof val === 'object' && val !== null) return JSON.stringify(val);
                        if (typeof val === 'string' && val.length > 60) return val.substring(0, 60) + '…';
                        return val !== undefined ? val : "";
                    }
                    return "";
                }
            }
        ],
        height: 370
    });

    // Populate the List View Builder
    const listViewBuilder = $("#listViewBuilder");
    listViewBuilder.empty();
    const listViewConfig = initialRecordDisplay ? initialRecordDisplay.listViewConfig : null;

    inferredSchema.forEach(col => {
        const config = listViewConfig ? listViewConfig.find(c => c.field === col.field) : null;
        const row = `
            <tr>
                <td><input type="checkbox" class="form-check-input" data-field="${col.field}" name="lv_include" ${config && config.include ? 'checked' : ''}></td>
                <td>${col.field}</td>
                <td><input type="text" class="form-control form-control-sm" data-field="${col.field}" name="lv_label" placeholder="Label (e.g. 'Title:')" value="${config && config.label ? config.label : ''}"></td>
                <td>
                    <div class="form-check form-check-inline">
                        <input type="checkbox" class="form-check-input" data-field="${col.field}" name="lv_bold" ${config && config.bold ? 'checked' : ''}>
                        <label class="form-check-label">Bold</label>
                    </div>
                    <div class="form-check form-check-inline">
                        <input type="checkbox" class="form-check-input" data-field="${col.field}" name="lv_newline" ${config && config.newline ? 'checked' : ''}>
                        <label class="form-check-label">New line</label>
                    </div>
                </td>
            </tr>
        `;
        listViewBuilder.append(row);
    });

    // Handle simple case from default config.js where textBy is a string
    if (initialRecordDisplay && typeof initialRecordDisplay.textBy === 'string') {
        const fieldName = initialRecordDisplay.textBy;
        const fieldRow = listViewBuilder.find(`input[data-field='${fieldName}']`).closest('tr');
        if (fieldRow) {
            fieldRow.find('input[name="lv_include"]').prop('checked', true);
        }
    }

    // Set the viewAs radio button
    if (initialRecordDisplay && initialRecordDisplay.viewAs) {
        $(`input[name='viewAs'][value='${initialRecordDisplay.viewAs}']`).prop('checked', true);
    }
}

function cleanDataWithSchema(data, schema) {
    if (!data || !schema) return [];

    const schemaMap = new Map(schema.map(item => [item.field, item]));

    return data.map(row => {
        const newRow = { ...row };
        for (const key in newRow) {
            if (schemaMap.has(key)) {
                const colSchema = schemaMap.get(key);
                const value = newRow[key];

                if (colSchema.type === 'number') {
                    newRow[key] = parseFloat(value);
                } else if (colSchema.type === 'date') {
                    if (!(value instanceof Date)) {
                       const parsedDate = Date.parse(value);
                       if (!isNaN(parsedDate)) {
                           newRow[key] = new Date(parsedDate);
                       }
                    }
                }
            }
        }
        return newRow;
    });
}

function generateRecordDisplayText(config) {
    let functionBody = 'var str = "";\n';
    config.forEach(item => {
        if (item.include) {
            let label = item.label ? `'${item.label.replace(/'/g, "\\'")} '` : '""';
            let value = `this["${item.field}"]`;
            
            if (item.bold) {
                value = `'<b>' + ${label} + ${value} + '</b>'`;
            } else {
                value = `${label} + ${value}`;
            }

            functionBody += `str += '<div>' + ${value} + '</div>';\n`;

            if (item.newline) {
                functionBody += `str += '<br>';\n`;
            }
        }
    });
    functionBody += 'return str;';
    try {
        return new Function(functionBody);
    } catch (e) {
        console.error("Error creating function:", functionBody);
        throw e;
    }
}

// --- Generate summaries config ---
function generateSummaries(schema) {
    return schema.filter(col => col.include).map(col => {
        const summary = {
            name: col.name,
            panel: col.panel,
            collapsed: !!col.collapsed
        };
        // Value generator logic
        if (col.multi) {
            // Use custom separator if set, else default '|'
            summary.value = new Function(`return function () {
                if(this["${col.field}"]){
                    return this["${col.field}"].split("${col.separator ? col.separator.replace(/\\/g, "\\\\").replace(/"/g, '\\"') : '|'}");
                }
            }`)();
        } else if (col.type === "date") {
            summary.value = new Function(`return function () {
                if(this["${col.field}"]){
                    return new Date(Date.parse(this["${col.field}"]));
                }
            }`)();
        } else {
            summary.value = col.field;
        }
        return summary;
    });
}

function exportConfig(summaries, recordDisplay, listViewConfig) {
    let js = "var summaries = " + JSON.stringify(summaries, null, 2) + ";\n\n";

    // Manually construct the recordDisplay object string to handle the function
    let recordDisplayString = `{\n`;
    recordDisplayString += `    viewAs: "${recordDisplay.viewAs}",\n`;
    recordDisplayString += `    textBy: ${recordDisplay.textBy.toString()},\n`;
    // Store the listViewConfig so the editor can be repopulated later
    recordDisplayString += `    listViewConfig: ${JSON.stringify(listViewConfig, null, 2)}\n`;
    recordDisplayString += `}`;

    js += `var recordDisplay = ${recordDisplayString};\n`;

    const blob = new Blob([js], { type: "text/javascript" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "config.js";
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { document.body.removeChild(a); URL.revokeObjectURL(url); }, 100);
}

// --- Export config button logic ---
$("#exportConfigBtn").on("click", function() {
    if (!schemaTable) return;
    const schema = schemaTable.getData();
    const dashSummaries = generateSummaries(schema);

    // Build recordDisplay config
    const viewAs = $("input[name='viewAs']:checked").val();
    const listViewConfig = [];
    $("#listViewBuilder tr").each(function() {
        const include = $(this).find("input[name='lv_include']").is(":checked");
        const field = $(this).find("input[name='lv_include']").data('field');
        const label = $(this).find("input[name='lv_label']").val();
        const bold = $(this).find("input[name='lv_bold']").is(":checked");
        const newline = $(this).find("input[name='lv_newline']").is(":checked");
        listViewConfig.push({ include, field, label, bold, newline });
    });

    const recordDisplayText = generateRecordDisplayText(listViewConfig);
    const recordDisplay = {
        viewAs: viewAs,
        textBy: recordDisplayText
    };

    exportConfig(dashSummaries, recordDisplay, listViewConfig);
});

// --- Confirm schema and show dashboard ---
$("#confirmSchemaBtn").on("click", function() {
    const schema = schemaTable.getData();

    const cleanedData = cleanDataWithSchema(originalData, schema);
    const dashSummaries = generateSummaries(schema);

    // Build recordDisplay config
    const viewAs = $("input[name='viewAs']:checked").val();
    const listViewConfig = [];
    $("#listViewBuilder tr").each(function() {
        const include = $(this).find("input[name='lv_include']").is(":checked");
        const field = $(this).find("input[name='lv_include']").data('field');
        const label = $(this).find("input[name='lv_label']").val();
        const bold = $(this).find("input[name='lv_bold']").is(":checked");
        const newline = $(this).find("input[name='lv_newline']").is(":checked");
        listViewConfig.push({ include, field, label, bold, newline });
    });

    const recordDisplayText = generateRecordDisplayText(listViewConfig);
    const recordDisplay = {
        viewAs: viewAs,
        textBy: recordDisplayText
    };

    $("#schemaEditorContainer").hide();
    $("#kshfDashboard").show();
    $("#editSchemaBtn").show();
    initializeDashboard(cleanedData, dashSummaries, recordDisplay);
});

$("#editSchemaBtn").on("click", function() {
    $("#kshfDashboard").hide();
    $("#editSchemaBtn").hide();
    $("#schemaEditorContainer").show();
});

// --- File upload handler ---
function handleFileUpload(file) {
    const reader = new FileReader();
    reader.onload = function (event) {
        const content = event.target.result;
        let data;
        const fileExtension = file.name.split('.').pop().toLowerCase();
        if (fileExtension === "json") {
            data = JSON.parse(content);
        } else if (fileExtension === "csv" || fileExtension === "tsv") {
            data = Papa.parse(content, { header: true, skipEmptyLines: true }).data;
        } else if (fileExtension === "xlsx" || fileExtension === "xls") {
            const workbook = XLSX.read(content, { type: 'binary' });
            const firstSheetName = workbook.SheetNames[0];
            const worksheet = workbook.Sheets[firstSheetName];
            data = XLSX.utils.sheet_to_json(worksheet);
        } else {
            alert("Unsupported file type. Please upload a CSV, TSV, JSON or Excel file.");
            return;
        }
        showSchemaEditor(data);
    };
    reader.onerror = function () { console.error("Error reading file:", reader.error); };
    if (["xlsx", "xls"].includes(file.name.split('.').pop().toLowerCase())) {
        reader.readAsBinaryString(file);
    } else {
        reader.readAsText(file);
    }
}

// --- File upload binding ---
$("#submit_static_data").on("click", function () {
    const fileInput = document.getElementById("anyFile");
    const file = fileInput.files[0];
    if (file) {
        handleFileUpload(file);
    } else {
        alert("Please select a file to upload.");
    }
});

// --- Keshif Dashboard Initialization ---
export function initializeDashboard(data, summaries, recordDisplay) {
    if(window.dashboard && window.dashboard.destroy) window.dashboard.destroy();
    kshf.Base.defaultBarHeight = 15;

    // Ensure recordDisplay is an object, even if it's empty
    const displayConfig = recordDisplay || {};

    window.dashboard = new kshf.Browser({
        barChartWidth: 100,
        leftPanelLabelWidth: 160,
        leftPanelLabelHeight: 200,
        rightPanelLabelWidth: 160,
        middlePanelLabelWidth: 160,
        summaries: summaries,
        recordDisplay: displayConfig,
        source: [{
            name: "Custom",
            id: "id",
            load: function () {
                if (Array.isArray(data)) {
                    data.forEach((d) => this.createRecord(d));
                }
            }
        }]
    });
}