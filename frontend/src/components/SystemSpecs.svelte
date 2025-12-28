<script>
    export let systemInfo = {};
</script>

<div class="specs-grid">
    <!-- CPU Card -->
    <div class="card">
        <h2>CPU</h2>
        {#if systemInfo.cpu}
            <p><strong>Name:</strong> {systemInfo.cpu.name || 'N/A'}</p>
            <p><strong>Temperature:</strong> {systemInfo.cpu.packageTemp?.toFixed(1) || 'N/A'} °C</p>
            <p><strong>Load:</strong> {systemInfo.cpu.totalLoad?.toFixed(1) || 'N/A'} %</p>
            <p><strong>Power:</strong> {systemInfo.cpu.packagePower?.toFixed(1) || 'N/A'} W</p>
        {:else}
            <p>Loading CPU data...</p>
        {/if}
    </div>

    <!-- GPU Card -->
    <div class="card">
        <h2>GPU</h2>
        {#if systemInfo.gpu}
            <p><strong>Name:</strong> {systemInfo.gpu.name || 'N/A'}</p>
            <p><strong>Temperature:</strong> {systemInfo.gpu.temp?.toFixed(1) || 'N/A'} °C</p>
            <p><strong>Load:</strong> {systemInfo.gpu.load?.toFixed(1) || 'N/A'} %</p>
            <p><strong>Memory Used:</strong> {systemInfo.gpu.memoryUsed?.toFixed(2) || 'N/A'} GB</p>
            <p><strong>Memory Total:</strong> {systemInfo.gpu.memoryTotal?.toFixed(2) || 'N/A'} GB</p>
        {:else}
            <p>Loading GPU data...</p>
        {/if}
    </div>

    <!-- RAM Card -->
    <div class="card">
        <h2>RAM</h2>
        {#if systemInfo.ram}
            <p><strong>Used:</strong> {systemInfo.ram.used?.toFixed(2) || 'N/A'} GB</p>
            <p><strong>Available:</strong> {systemInfo.ram.available?.toFixed(2) || 'N/A'} GB</p>
            <p><strong>Total:</strong> {systemInfo.ram.total?.toFixed(2) || 'N/A'} GB</p>
        {:else}
            <p>Loading RAM data...</p>
        {/if}
    </div>

    <!-- Battery Card -->
    {#if systemInfo.battery}
        <div class="card">
            <h2>Battery</h2>
            <p><strong>Charge Level:</strong> {systemInfo.battery.chargeLevel?.toFixed(1) || 'N/A'} %</p>
            <p><strong>Voltage:</strong> {systemInfo.battery.voltage?.toFixed(2) || 'N/A'} V</p>
            <p><strong>Wear Level:</strong> {systemInfo.battery.wearLevel?.toFixed(1) || 'N/A'} %</p>
        </div>
    {/if}
</div>

<style>
    .specs-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 16px;
    }
    .card {
        background-color: #2c3e50;
        padding: 16px;
        border-radius: 8px;
    }
    .card h2 {
        margin-top: 0;
        border-bottom: 2px solid #61afef;
        padding-bottom: 8px;
    }
    .card p {
        margin: 8px 0;
        display: flex;
        justify-content: space-between;
    }
    .card p strong {
        color: #95a5a6;
    }
</style>
