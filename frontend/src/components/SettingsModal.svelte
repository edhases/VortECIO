<script>
    import { createEventDispatcher, onMount } from 'svelte';
    import { t } from '../i18n/store.js';
    import { GetSensorPlugins } from "../../wailsjs/go/main/App";

    export let settings = {};

    const dispatch = createEventDispatcher();

    let sensorPlugins = [];
    let initialPluginID;

    onMount(() => {
        initialPluginID = settings.sensorProviderPluginID;
        GetSensorPlugins().then(plugins => {
            sensorPlugins = plugins;
        });
    });

    function handleSave() {
        if (settings.sensorProviderPluginID !== initialPluginID) {
            alert("Sensor provider changed. Please restart the application for changes to take effect.");
        }
        dispatch('save');
    }

    function validateDelta() {
        if (settings.criticalTempRecoveryDelta < 3) {
            settings.criticalTempRecoveryDelta = 3;
        }
        if (settings.criticalTempRecoveryDelta > 15) {
            settings.criticalTempRecoveryDelta = 15;
        }
    }
</script>

<div class="modal-backdrop">
    <div class="modal">
        <h2>{$t.settings_title}</h2>

        <div class="form-group">
            <label for="language">{$t.lang_label}</label>
            <select id="language" bind:value={settings.language}>
                <option value="en">English</option>
                <option value="ua">Українська</option>
                <option value="de">Deutsch</option>
                <option value="pl">Polski</option>
                <option value="ja">日本語</option>
            </select>
        </div>

        <div class="form-group">
            <label for="autostart">{$t.autostart_label}</label>
            <input type="checkbox" id="autostart" bind:checked={settings.autoStart} />
        </div>

        <hr>

        <div class="form-group">
            <label for="sensor-provider">{$t.cpu_sensor_source}</label>
            <select id="sensor-provider" bind:value={settings.sensorProviderPluginID}>
                <option value="">WMI (System)</option>
                {#each sensorPlugins as plugin}
                    <option value={plugin.id}>{plugin.name}</option>
                {/each}
            </select>
        </div>

        <hr>

        <div class="form-group">
            <label for="critical-temp">{$t.critical_temp_label}</label>
            <input type="number" id="critical-temp" bind:value={settings.criticalTemp} min="70" max="100" />
        </div>

        <div class="form-group">
            <label for="safety-action">{$t.safety_action_label}</label>
            <select id="safety-action" bind:value={settings.safetyAction}>
                <option value="bios_control">{$t.action_bios}</option>
                <option value="force_full_speed">{$t.action_max}</option>
            </select>
        </div>

        <div class="form-group">
            <label>
                <input type="checkbox" bind:checked={settings.enableCriticalTempRecovery} />
                {$t.settings_enable_recovery}
            </label>
        </div>

        <div class="form-group" class:disabled={!settings.enableCriticalTempRecovery}>
            <label for="recovery-delta">{$t.settings_recovery_delta}</label>
            <input
                type="number"
                id="recovery-delta"
                bind:value={settings.criticalTempRecoveryDelta}
                min="3"
                max="15"
                disabled={!settings.enableCriticalTempRecovery}
                on:input={validateDelta}
            />
            <small>({$t.settings_recovery_delta_hint})</small>
        </div>

        <div class="modal-actions">
            <button on:click={handleSave}>{$t.save_btn}</button>
            <button on:click={() => dispatch('close')} class="cancel-btn">{$t.cancel_btn}</button>
        </div>
    </div>
</div>

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
    .form-group.disabled {
        opacity: 0.5;
        pointer-events: none;
    }
</style>
