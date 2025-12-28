<script>
    import { onMount, createEventDispatcher } from 'svelte';
    import { Line } from 'svelte-chartjs';
    import { SaveFanCurve, ResetFanCurve } from '../../../wailsjs/go/main/App';
    import {
        Chart as ChartJS,
        Title,
        Tooltip,
        Legend,
        LineElement,
        LinearScale,
        PointElement,
        CategoryScale,
    } from 'chart.js';
    import 'chartjs-plugin-dragdata';

    export let thresholds = [];
    export let fanIndex = 0;

    const dispatch = createEventDispatcher();

    let localThresholds = JSON.parse(JSON.stringify(thresholds)); // Deep copy
    let chartData;
    let chartOptions;

    function handleSave() {
        SaveFanCurve(fanIndex, localThresholds)
            .then(() => dispatch('save'))
            .catch(err => console.error(err));
    }

    function handleReset() {
        ResetFanCurve(fanIndex)
            .then(() => dispatch('reset'))
            .catch(err => console.error(err));
    }

    // Register Chart.js components
    onMount(() => {
        ChartJS.register(
            Title,
            Tooltip,
            Legend,
            LineElement,
            LinearScale,
            PointElement,
            CategoryScale
        );
        updateChartData();
    });

    function updateChartData() {
        chartData = {
            datasets: [
                {
                    label: 'Fan Speed',
                    data: localThresholds.map(t => ({ x: t.UpThreshold, y: t.FanSpeed })),
                    borderColor: '#61afef',
                    backgroundColor: '#61afef',
                    fill: false,
                    tension: 0.1,
                    draggable: true
                },
            ],
        };

        chartOptions = {
            responsive: true,
            plugins: {
                legend: { display: false },
                dragdata: {
                    round: 1,
                    dragX: true, // Enable horizontal dragging
                    showTooltip: true,
                    onDragEnd: (e, datasetIndex, index, value) => {
                        // value is an object {x, y} when dragX is true
                        const newTemp = Math.round(value.x);
                        const newSpeed = Math.round(value.y);

                        // Basic validation to prevent inverting the curve
                        if (index > 0 && newTemp <= localThresholds[index - 1].UpThreshold) {
                            // Reset position if dragged before the previous point
                            updateChartData();
                            return;
                        }
                        if (index < localThresholds.length - 1 && newTemp >= localThresholds[index + 1].UpThreshold) {
                            // Reset position if dragged after the next point
                            updateChartData();
                            return;
                        }

                        localThresholds[index].UpThreshold = newTemp;
                        // A simple heuristic for DownThreshold
                        localThresholds[index].DownThreshold = newTemp - 5;
                        localThresholds[index].FanSpeed = newSpeed;

                        localThresholds = [...localThresholds];
                        updateChartData();
                    },
                },
            },
            scales: {
                y: {
                    min: 0,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Speed (%)',
                    },
                },
                x: {
                     title: {
                        display: true,
                        text: 'Temperature (°C)',
                    },
                }
            },
        };
    }

</script>

<div class="curve-editor-container">
    {#if chartData}
        <Line data={chartData} options={chartOptions} />
    {/if}
    <div class="controls">
        <button on:click={handleSave}>Save Curve</button>
        <button on:click={handleReset} class="reset-btn">Reset to Default</button>
    </div>
</div>

<style>
    .curve-editor-container {
        padding: 1rem;
        background-color: #2c3e50;
        border-radius: 8px;
        margin-top: 1rem;
    }
    .controls {
        display: flex;
        justify-content: flex-end;
        gap: 10px;
        margin-top: 1rem;
    }
    button {
        background-color: #61afef;
        color: #1b2636;
        border: none;
        padding: 8px 12px;
        border-radius: 4px;
        cursor: pointer;
        font-weight: bold;
    }
    .reset-btn {
        background-color: #e06c75;
    }
</style>
