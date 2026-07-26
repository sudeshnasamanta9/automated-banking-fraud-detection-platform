// Dynamic runtime repository memory matrix container
let ruleTemplatesData = {};
let currentActiveRuleId = '';
let dynamicRowCount = 0;

// PARSES AND LOADS LIVE SYSTEM DATABASE RECORDS
function initializeDatabaseStateRegistry() {
    const dataContainer = document.getElementById('db-rules-payload');
    if (dataContainer && dataContainer.dataset.json) {
        try {
            ruleTemplatesData = JSON.parse(dataContainer.dataset.json);
        } catch (e) {
            console.error("Error reading database payload", e);
            ruleTemplatesData = {};
        }
    }
    
    const keys = Object.keys(ruleTemplatesData);
    if (keys.length > 0) {
        bindSelectedRule(keys[0]);
    } else {
        initializeFreshRuleForm();
    }
}

// CACHES CURRENT USER INPUT TYPING ACTIONS
function preserveActiveFormState(id) {
    if (!id || !ruleTemplatesData[id]) return;
    
    ruleTemplatesData[id].name = document.getElementById('rule_name').value;
    if (!ruleTemplatesData[id].data) ruleTemplatesData[id].data = {};
    
    ruleTemplatesData[id].data.description = document.getElementById('description').value;
    ruleTemplatesData[id].data.risk_score = document.querySelector('select[name="score"]').value;
    
    ruleTemplatesData[id].data.conditions_matrix = [];
    const conditionRows = document.querySelectorAll('#matrix-container .condition-row');
    
    conditionRows.forEach((row, index) => {
        const rowNum = index + 1;
        const paramEl = row.querySelector(`[name="param_${rowNum}"]`);
        const opEl = row.querySelector(`[name="op_${rowNum}"]`);
        const valEl = row.querySelector(`[name="val_${rowNum}"]`);
        const logicalEl = row.querySelector(`[name="logical_${rowNum}"]`);
        
        if (paramEl && paramEl.value) {
            ruleTemplatesData[id].data.conditions_matrix.push({
                field: paramEl.value,
                operator: opEl ? opEl.value : '<',
                value: valEl ? valEl.value : '',
                logical: logicalEl ? logicalEl.value : 'AND'
            });
        }
    });
}

// ADAPTIVE FIELD TYPE DETECTOR
function adaptInputBox(rowNum, forceValue = null) {
    const parameterEl = document.getElementById(`param_${rowNum}`);
    const container = document.getElementById(`container_val_${rowNum}`);
    if (!parameterEl || !container) return;
    
    const parameter = parameterEl.value;
    let val = forceValue !== null ? forceValue : (document.getElementById(`val_${rowNum}`)?.value || '');

    if (['channel', 'occupation', 'dr_cr' , 'narration'].includes(parameter)) {
        const options = {
            'channel': ['Mobile', 'ATM', 'NetBanking', 'UPI', 'Branch', 'POS'],
            'occupation': ['Engineer', 'Doctor', 'Business Owner', 'Manager', 'Teacher', 'Consultant', 'Student', 'Retired'],
            'dr_cr': ['cr', 'dr'],
            'narration':[ 'GST Payment', 
                'Premature FD withdrawal', 
                'Salary Credit',   
                'NEFT Transaction', 
                'Interest Credit']
        };
        container.innerHTML = `<select name="val_${rowNum}" id="val_${rowNum}">` + 
            options[parameter].map(o => `<option value="${o}">${o}</option>`).join('') + `</select>`;
    } else {
        container.innerHTML = `<input type="text" name="val_${rowNum}" id="val_${rowNum}" value="${val}">`;
    }
    if (document.getElementById(`val_${rowNum}`)) document.getElementById(`val_${rowNum}`).value = val;
}

// ENDLESS DYNAMIC MATRIX FIELD EXTENDER
function addNewFieldRow(data = null) {
    dynamicRowCount++;
    const currentNum = dynamicRowCount;
    const container = document.getElementById('matrix-container');
    
    const newRow = document.createElement('div');
    newRow.className = 'condition-row';
    newRow.innerHTML = `
        <select name="param_${currentNum}" id="param_${currentNum}" onchange="adaptInputBox(${currentNum})">
            <option value="" selected>-- Select Field --</option>
            <option value="account_opening_days">Account Opening Date (Days)</option>
            <option value="narration">Narration Keyword String</option>
            <option value="dr_cr">Debit/Credit Type (DR/CR)</option>
            <option value="cumulative_credit_inr">Cumulative Credit Inflow (₹)</option>
            <option value="cumulative_debit_inr">Cumulative Debit Outflow (₹)</option>
            <option value="channel">Transaction Channel</option>
            <option value="txn_amount">Transaction Amount</option>
            <option value="occupation">Occupation</option>
        </select>
        <select name="op_${currentNum}" id="op_${currentNum}">
            <option value="<=">&lt;=</option>
            <option value=">=">&gt;=</option>
            <option value="=">=</option>
            <option value="!=">!=</option>
            <option value="CONTAINS">CONTAINS</option>
        </select>
        <div class="input-container" id="container_val_${currentNum}">
            <input type="text" name="val_${currentNum}" id="val_${currentNum}" value="">
        </div>
        <select name="logical_${currentNum}" id="logical_${currentNum}">
            <option value="AND">AND</option>
            <option value="END">END</option>
        </select>
    `;
    container.appendChild(newRow);

    if (data) {
        document.getElementById(`param_${currentNum}`).value = data.field || '';
        adaptInputBox(currentNum, data.value || '');
        document.getElementById(`op_${currentNum}`).value = data.operator || '<=';
        document.getElementById(`logical_${currentNum}`).value = data.logical || 'AND';
    }
}

// BIND DATA TO UI
function bindSelectedRule(id, event = null) {
    if (currentActiveRuleId && currentActiveRuleId !== id) {
        preserveActiveFormState(currentActiveRuleId);
    }
    
    const payload = ruleTemplatesData[id];
    if (!payload) return;

    currentActiveRuleId = id;

    // Update form fields
    document.getElementById('rule_id').value = id;
    document.getElementById('rule_name').value = payload.name || '';
    document.getElementById('description').value = payload.data?.description || '';
    document.querySelector('select[name="score"]').value = payload.data?.risk_score || 'MEDIUM';
    
    // Refresh matrix
    document.getElementById('matrix-container').innerHTML = '';
    dynamicRowCount = 0;
    
    const conditions = payload.data?.conditions_matrix || [];
    if (conditions.length > 0) {
        conditions.forEach(cond => addNewFieldRow(cond));
    } else {
        addNewFieldRow({});
    }

    // UPDATED: Robust Active Card Highlighting
    document.querySelectorAll('.rule-card').forEach(c => c.classList.remove('active-card'));
    
    // If the click event exists, highlight that target
    if (event && event.currentTarget) {
        event.currentTarget.classList.add('active-card');
    } else {
        // Otherwise, find the card that corresponds to this ID in the DOM
        const cards = document.querySelectorAll('.rule-card');
        cards.forEach(card => {
            // Check if the onclick string contains this specific ID
            const onclickAttr = card.getAttribute('onclick') || '';
            if (onclickAttr.includes(`'${id}'`)) {
                card.classList.add('active-card');
            }
        });
    }
}
function initializeFreshRuleForm() {
    // 1. Preserve the current state before creating a new one
    if (currentActiveRuleId) {
        preserveActiveFormState(currentActiveRuleId);
    }

    // 2. Generate a unique ID
    const customId = 'rule_custom_' + Math.floor(Math.random() * 1000);
    
    // 3. Initialize data structure
    ruleTemplatesData[customId] = { 
        name: 'New Rule', 
        data: { description: '', risk_score: 'MEDIUM', conditions_matrix: [] } 
    };
    
    // 4. Create the Sidebar Card Element
    const sidebar = document.querySelector('.sidebar');
    const createBtn = sidebar.querySelector('.btn-success');
    
    const newCard = document.createElement('div');
    newCard.className = 'rule-card active-card'; // Add active-card class immediately
    newCard.setAttribute('onclick', `bindSelectedRule('${customId}', event)`);
    newCard.innerHTML = `
       <div style="width: 100%; white-space: normal; overflow: visible;">
        <strong id="card_label_${customId}">New Rule</strong>
        <span id="card_span_${customId}">(No Description)</span>
    </div>
    `;
    
    // 5. Insert the new card into the sidebar before the "+ Create" button
    sidebar.insertBefore(newCard, createBtn);
    
    // 6. Refresh the form to clear it for the new rule
    bindSelectedRule(customId);
}

// EVENT LISTENERS
document.getElementById('rule_name').addEventListener('input', e => {
    const label = document.getElementById(`card_label_${currentActiveRuleId}`);
    if (label) label.innerText = e.target.value || 'New Rule';
});

document.getElementById('description').addEventListener('input', e => {
    const span = document.getElementById(`card_span_${currentActiveRuleId}`);
    if (span) span.innerText = e.target.value || '(No Description)';
});

function triggerRuleDeletion() {
    if (confirm("Delete this rule?")) window.location.href = `/delete-rule/${currentActiveRuleId}`;
}

window.onload = initializeDatabaseStateRegistry;