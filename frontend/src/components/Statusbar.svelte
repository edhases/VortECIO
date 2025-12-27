<script>
    export let modelName = "Loading...";
    export let systemTemp = "N/A";
    export let systemTempLabel = "System Temp";
</script>

<div class="statusbar">
    <span class="model-name">{modelName}</span>
    <div class="temp-display">
        <span>{systemTempLabel}: </span>
        <span class="temp-value">{systemTemp}°C</span>
    </div>
</div>

<style>
    .statusbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 16px;
        background-color: #2c3e50;
        border-bottom: 1px solid #445566;
    }

    .model-name {
        font-weight: bold;
        color: #bdc3c7;
    }

    .temp-display {
        font-size: 14px;
        color: #ecf0f1;
    }

    .temp-value {
        font-weight: bold;
        color: #61afef;
    }
</style>
