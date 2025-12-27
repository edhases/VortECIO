<script>
    import { createEventDispatcher } from 'svelte';
    import { t, locale } from '../i18n/store.js';

    export let showModal = false;
    export let settings = {};

    const dispatch = createEventDispatcher();

    let localSettings = { ...settings };

    function handleSave() {
        dispatch('save', localSettings);
    }

    function handleCancel() {
        localSettings = { ...settings }; // Reset changes
        dispatch('close');
    }

    // Update local copy if the main settings object changes from outside
    $: if (settings) {
        localSettings = { ...settings };
    }
</script>

{#if showModal}
<div class="modal-backdrop">
    <div class="modal">
        <h2>{$t.settings_title}</h2>

        <div class="form-group">
            <label for="language">{$t.lang_label}</label>
            <select id="language" bind:value={localSettings.Language}>
                <option value="en">English</option>
                <option value="ua">Українська</option>
            </select>
        </div>

        <div class="form-group">
            <label for="autostart">{$t.autostart_label}</label>
            <input type="checkbox" id="autostart" bind:checked={localSettings.AutoStart} />
        </div>

        <div class="form-group">
            <label for="critical-temp">{$t.critical_temp_label}</label>
            <input type="number" id="critical-temp" bind:value={localSettings.CriticalTemp} min="70" max="100" />
        </div>

        <div class="form-group">
            <label for="safety-action">{$t.safety_action_label}</label>
            <select id="safety-action" bind:value={localSettings.SafetyAction}>
                <option value="bios_control">{$t.action_bios}</option>
                <option value="force_full_speed">{$t.action_max}</option>
            </select>
        </div>

        <div class="modal-actions">
            <button on:click={handleSave}>{$t.save_btn}</button>
            <button on:click={handleCancel} class="cancel-btn">{$t.cancel_btn}</button>
        </div>
    </div>
</div>
{/if}

<style>
    .modal-backdrop {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.6);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 100;
    }
    .modal {
        background-color: #2c3e50;
        padding: 24px;
        border-radius: 8px;
        width: 90%;
        max-width: 400px;
        border: 1px solid #445566;
    }
    h2 {
        margin-top: 0;
        color: #ecf0f1;
    }
    .form-group {
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    label {
        color: #bdc3c7;
    }
    input, select {
        padding: 8px;
        border-radius: 4px;
        border: 1px solid #4a627a;
        background-color: #34495e;
        color: #ecf0f1;
        width: 50%;
    }
    input[type="checkbox"] {
        width: auto;
        height: 20px;
        width: 20px;
    }
    .modal-actions {
        display: flex;
        justify-content: flex-end;
        gap: 12px;
        margin-top: 24px;
    }
    button {
        background-color: #61afef;
        color: #1b2636;
        border: none;
        padding: 10px 16px;
        border-radius: 4px;
        cursor: pointer;
        font-weight: bold;
    }
    button:hover {
        background-color: #7abfff;
    }
    .cancel-btn {
        background-color: #7f8c8d;
    }
    .cancel-btn:hover {
        background-color: #95a5a6;
    }
</style>
