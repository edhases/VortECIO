<script>
    import { onMount } from "svelte";
    import Statusbar from "./components/Statusbar.svelte";
    import FanCard from "./components/FanCard.svelte";
    import SettingsModal from "./components/SettingsModal.svelte";
    import { t, initI18n, setLocale } from './i18n/store.js';
    import { LoadConfig, GetState, GetSettings, SaveAppSettings } from "../wailsjs/go/main/App";

    let state = {
        SystemTemp: 0.0,
        GpuTemp: 0.0,
        Fans: [],
        ModelName: "No Config Loaded"
    };
    let settings = {};
    let errorMsg = "";
    let showSettingsModal = false;

    // --- Core App Logic ---
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

    // --- Settings Modal Logic ---
    function openSettings() {
        showSettingsModal = true;
    }

    function handleSaveSettings() {
        SaveAppSettings(settings)
            .then(() => {
                setLocale(settings.language); // Update language in UI
                showSettingsModal = false;
            })
            .catch(err => {
                console.error("Failed to save settings:", err);
                errorMsg = err;
            });
    }

    // --- Lifecycle ---
    onMount(() => {
        // Initialize localization
        initI18n();

        // Load initial settings from backend
        GetSettings().then(loadedSettings => {
            settings = loadedSettings;
        });

        // Initial state load
        GetState().then(newState => {
            if(newState.ModelName) {
                state = newState;
            }
        });

        // Polling for state updates
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
        }, 1000);

        return () => clearInterval(interval);
    });

</script>

<main>
    {#if showSettingsModal}
        <SettingsModal
            bind:settings={settings}
            on:save={handleSaveSettings}
            on:close={() => showSettingsModal = false}
        />
    {/if}

    <div class="top-bar">
        <h1>{$t.app_title}</h1>
        <div>
            <button on:click={handleLoadConfig}>{$t.load_config}</button>
            <button on:click={openSettings}>{$t.settings_btn}</button>
        </div>
    </div>
    <Statusbar
        modelName={state.ModelName}
        systemTemp={state.SystemTemp.toFixed(1)}
        gpuTemp={state.GpuTemp}
    />

    <div class="content">
        {#if errorMsg}
            <div class="error">{errorMsg}</div>
        {/if}

        {#if state.Fans && state.Fans.length > 0}
            {#each state.Fans as fan, i}
                <FanCard {fan} fanIndex={i} />
            {/each}
        {:else}
            <div class="no-config">
                <p>{$t.no_config}</p>
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

    .top-bar div {
        display: flex;
        gap: 10px;
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
