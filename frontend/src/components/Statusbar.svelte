<script>
    export let modelName = "No Config Loaded";
    export let systemTemp = "N/A";
</script>

<div class="statusbar">
    <div class="model-name">{modelName}</div>
    <div class="temperature">
        System Temp: <span>{systemTemp}°C</span>
    </div>
</div>

<style>
    .statusbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 16px;
        background-color: #2a3a4a;
        color: #e0e0e0;
        border-bottom: 1px solid #445566;
        font-size: 14px;
    }

    .model-name {
        font-weight: bold;
    }

    .temperature span {
        font-weight: bold;
        color: #61afef; /* A light blue accent */
    }
</style>
