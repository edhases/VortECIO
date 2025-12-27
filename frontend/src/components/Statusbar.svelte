<script>
    export let modelName = "Unknown";
    export let systemTemp = "0.0";
    export let gpuTemp = 0; // Новий проп
</script>

<div class="statusbar">
    <div class="left">
        <span class="model">Model: {modelName}</span>
    </div>
    <div class="right">
        {#if gpuTemp > 0}
            <span class="temp gpu">GPU: {gpuTemp.toFixed(1)}°C</span>
            <span class="divider">|</span>
        {/if}
        <span class="temp cpu">CPU: {systemTemp}°C</span>
    </div>
</div>

<style>
    .statusbar {
        background-color: #2c3e50;
        padding: 8px 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #1a252f;
        font-size: 0.9em;
    }
    .temp {
        font-weight: bold;
    }
    .cpu { color: #e74c3c; } /* Червоний для CPU */
    .gpu { color: #2ecc71; } /* Зелений для GPU */
    .divider { margin: 0 8px; color: #7f8c8d; }
</style>
