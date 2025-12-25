<script>
    import { onMount } from "svelte";
    import Statusbar from "./components/Statusbar.svelte";
    import FanCard from "./components/FanCard.svelte";
    import { LoadConfig, GetState } from "../wailsjs/go/main/App";

    let state = {
        SystemTemp: 0.0,
        Fans: [],
        ModelName: "No Config Loaded"
    };
    let errorMsg = "";

    function handleLoadConfig() {
        errorMsg = "";
        LoadConfig()
            .then(newState => {
                if(newState.ModelName) {
                    state = newState;
                }
            })
            .catch(err => {
                console.error(err);
                errorMsg = err;
            });
    }

    // Poll for state updates
    onMount(() => {
        // Initial state load
        GetState().then(newState => {
            if(newState.ModelName) {
                state = newState;
            }
        });

        const interval = setInterval(() => {
            GetState()
                .then(newState => {
                    if(newState.ModelName) {
                       state = newState;
                    }
                })
                .catch(err => {
                    console.error("Failed to get state:", err);
                    clearInterval(interval); // Stop polling on error
                });
        }, 1000); // Poll every second

        return () => clearInterval(interval);
    });

</script>

<main>
    <div class="top-bar">
        <h1>VortECIO-Go</h1>
        <button on:click={handleLoadConfig}>Load Config</button>
    </div>
    <Statusbar modelName={state.ModelName} systemTemp={state.SystemTemp.toFixed(1)} />

    <div class="content">
        {#if errorMsg}
            <div class="error">{errorMsg}</div>
        {/if}

        {#if state.Fans && state.Fans.length > 0}
            {#each state.Fans as fan, i}
                <FanCard fan={fan} fanIndex={i} bind:fan.Mode bind:fan.ManualSpeed />
            {/each}
        {:else}
            <div class="no-config">
                <p>Please load an NBFC configuration file to begin.</p>
            </div>
        {/if}
    </div>
</main>

<style>
    :global(body) {
        background-color: #1b2636;
        color: #ecf0f1;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol";
        margin: 0;
    }

    main {
        display: flex;
        flex-direction: column;
        height: 100vh;
    }

    .top-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 16px;
        background-color: #34495e;
    }

    h1 {
        margin: 0;
        font-size: 1.2em;
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
    button:hover {
        background-color: #7abfff;
    }

    .content {
        padding: 16px;
        overflow-y: auto;
        flex-grow: 1;
    }

    .no-config {
        text-align: center;
        margin-top: 50px;
        color: #95a5a6;
    }

    .error {
        color: #e74c3c;
        background-color: #f2dede4d;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
</style>
