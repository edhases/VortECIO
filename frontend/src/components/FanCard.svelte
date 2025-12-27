<script>
    import { SetFanMode, SetManualSpeed } from "../../wailsjs/go/main/App";
    import { t } from '../i18n/store.js';

    export let fan = {};
    export let fanIndex = 0;

    let modes = ["Auto", "Manual", "Disabled"];

    function handleModeChange(event) {
        const newMode = event.target.value;
        SetFanMode(fanIndex, newMode)
            .catch(err => console.error(err));
    }

    function handleSpeedChange(event) {
        const newSpeed = parseInt(event.target.value, 10);
        SetManualSpeed(fanIndex, newSpeed)
            .catch(err => console.error(err));
    }

    // A map to get translated mode names
    const modeTranslations = {
        "Auto": $t.mode_auto,
        "Manual": $t.mode_manual,
        "Disabled": $t.mode_disabled,
    };
</script>

<div class="fan-card">
    <div class="fan-header">
        <span class="fan-name">{fan.Name || 'Unnamed Fan'}</span>
    </div>
    <div class="fan-controls">
        <div class="control-group">
            <label for="mode-select-{fanIndex}">{$t.mode_label}:</label>
            <select id="mode-select-{fanIndex}" value={fan.Mode} on:change={handleModeChange}>
                {#each modes as mode}
                    <option value={mode}>{modeTranslations[mode] || mode}</option>
                {/each}
            </select>
        </div>

        <div class="control-group slider-group">
            <label for="speed-slider-{fanIndex}">{$t.speed_label}:</label>
            <input
                type="range"
                id="speed-slider-{fanIndex}"
                min="0"
                max="100"
                value={fan.ManualSpeed}
                on:input={handleSpeedChange}
                disabled={fan.Mode !== 'Manual'}
            />
            <span class="speed-label">
                {fan.ReadSpeedPercent < 0 ? 'N/A' : fan.ReadSpeedPercent + '%'}
                {#if fan.currentRpm > 0}
                    <span class="rpm-label">{fan.currentRpm} RPM</span>
                {/if}
            </span>
        </div>
    </div>
</div>

<style>
    .fan-card {
        background-color: #2c3e50;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 16px;
        border: 1px solid #445566;
    }

    .fan-header {
        margin-bottom: 12px;
    }

    .fan-name {
        font-weight: bold;
        font-size: 1.1em;
        color: #e0e0e0;
    }

    .fan-controls {
        display: flex;
        flex-direction: column;
        gap: 12px;
    }

    .control-group {
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .slider-group {
        flex-grow: 1;
    }

    label {
        font-size: 14px;
        color: #bdc3c7;
    }

    select {
        background-color: #34495e;
        color: #ecf0f1;
        border: 1px solid #4a627a;
        border-radius: 4px;
        padding: 4px 8px;
    }

    input[type="range"] {
        flex-grow: 1;
        -webkit-appearance: none;
        appearance: none;
        width: 100%;
        height: 8px;
        background: #4a627a;
        border-radius: 5px;
        outline: none;
        opacity: 0.7;
        transition: opacity .2s;
    }
    input[type="range"]:hover {
        opacity: 1;
    }
    input[type="range"]::-webkit-slider-thumb {
        -webkit-appearance: none;
        appearance: none;
        width: 18px;
        height: 18px;
        background: #61afef;
        cursor: pointer;
        border-radius: 50%;
    }
    input[type="range"]:disabled::-webkit-slider-thumb {
        background: #7f8c8d;
    }

    .speed-label {
        min-width: 40px;
        text-align: right;
        font-weight: bold;
    }
</style>
