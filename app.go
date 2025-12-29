//go:build windows

package main

import (
	"VortECIO-Go/controller"
	"VortECIO-Go/hardware"
	"VortECIO-Go/models"
	"VortECIO-Go/sensors"
	"VortECIO-Go/services"
	"VortECIO-Go/utils"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"

	"github.com/getlantern/systray"
	"github.com/wailsapp/wails/v2/pkg/runtime"
	"golang.org/x/sys/windows/registry"
)

// App struct holds the application's state and dependencies.
type App struct {
	ctx              context.Context
	ecDriver         hardware.ECDriver
	fanController    *controller.FanController
	monitorService   *services.MonitorService
	pluginService    *services.PluginService
	settings         models.Settings
	settingsPath     string
	userProfiles     models.UserProfiles
	userProfilesPath string
}

// NewApp creates a new App application struct.
func NewApp() *App {
	return &App{}
}

// GetSensorPlugins returns a list of available sensor provider plugins.
func (a *App) GetSensorPlugins() []services.PluginManifest {
	plugins := a.pluginService.GetSensorProviders()
	manifests := make([]services.PluginManifest, len(plugins))
	for i, p := range plugins {
		manifests[i] = p.Manifest
	}
	return manifests
}

// startup is called when the app starts.
func (a *App) startup(ctx context.Context) {
	a.ctx = ctx
	go a.runSysTray()

	// Determine paths
	baseDir, err := utils.GetBaseDir()
	if err != nil {
		log.Fatalf("Fatal: Could not determine base directory: %v", err)
	}
	a.settingsPath = filepath.Join(baseDir, "settings.json")
	a.userProfilesPath = filepath.Join(baseDir, "user_profiles.json")
	pluginDir := filepath.Join(baseDir, "plugins")

	// Discover plugins first
	a.pluginService = services.NewPluginService(pluginDir)

	// Load settings or create default
	if err := a.loadSettings(); err != nil {
		log.Printf("Could not load settings, creating default: %v", err)
		a.settings = models.Settings{
			Language:               "en",
			AutoStart:              false,
			CriticalTemp:           80,
			SafetyAction:           "bios_control",
			SensorProviderPluginID: "", // Default to WMI
		}
		// Try to save the new default settings
		if err := a.saveSettingsToFile(); err != nil {
			log.Printf("Warning: failed to save default settings: %v", err)
		}
	}

	// Load user profiles
	if err := a.loadUserProfiles(); err != nil {
		log.Printf("Could not load user profiles, starting with empty set: %v", err)
		a.userProfiles = make(models.UserProfiles)
	}

	// Initialize the EC driver
	driver, err := hardware.NewEcDriver()
	if err != nil {
		runtime.MessageDialog(a.ctx, runtime.MessageDialogOptions{
			Type:    runtime.ErrorDialog,
			Title:   "Critical Driver Error",
			Message: fmt.Sprintf("The fan control driver (inpoutx64.dll) could not be loaded.\n\n%v", err),
		})
		os.Exit(1)
	}
	a.ecDriver = driver
	a.fanController = controller.NewFanController(a.ctx, a.ecDriver, a.UpdateTrayTooltip)
	a.fanController.UpdateSettings(&a.settings) // Pass initial settings to controller

	// Initialize and start monitor service based on settings
	if a.settings.SensorProviderPluginID != "" {
		if plugin, ok := a.pluginService.GetPluginByID(a.settings.SensorProviderPluginID); ok {
			sidecarPath := filepath.Join(plugin.BasePath, plugin.Manifest.Executable)

			a.monitorService = services.NewMonitorService(sidecarPath)
			a.monitorService.OnData = func(info services.SystemInfo) {
				a.fanController.UpdateTemperatures(info.CPU.PackageTemp, info.GPU.Temp)
				runtime.EventsEmit(a.ctx, "systemInfo", info)
			}
			a.monitorService.OnError = func(err error) {
				log.Printf("Monitor service plugin '%s' error: %v. Activating fallback.", plugin.Manifest.Name, err)
				a.fanController.SetSensorSource(controller.SensorSourceWMI)
			}

			a.fanController.SetSensorSource(controller.SensorSourceSidecar)
			a.monitorService.Start()
		} else {
			log.Printf("Warning: Selected sensor plugin '%s' not found. Defaulting to WMI.", a.settings.SensorProviderPluginID)
			a.fanController.SetSensorSource(controller.SensorSourceWMI)
		}
	} else {
		log.Println("No sensor plugin selected. Defaulting to WMI.")
		a.fanController.SetSensorSource(controller.SensorSourceWMI)
	}

	// Try to auto-load last config
	if a.settings.LastConfigPath != "" {
		log.Printf("Found last config path: %s", a.settings.LastConfigPath)
		if _, err := os.Stat(a.settings.LastConfigPath); err == nil {
			a.loadConfigFile(a.settings.LastConfigPath, true) // isAutoLoad = true
		} else {
			log.Printf("Warning: last config file not found at %s", a.settings.LastConfigPath)
		}
	}
}

// shutdown is called when the app is closing.
func (a *App) shutdown(ctx context.Context) {
	log.Println("Shutting down...")
	if a.monitorService != nil {
		a.monitorService.Stop()
	}
	if a.fanController != nil {
		a.fanController.Stop()
	}
}

// LoadConfig opens a file dialog for the user to select an NBFC config file.
func (a *App) LoadConfig() (controller.PublicState, error) {
	selection, err := runtime.OpenFileDialog(a.ctx, runtime.OpenDialogOptions{
		Title: "Select NBFC Configuration File",
		Filters: []runtime.FileFilter{
			{DisplayName: "XML Files (*.xml)", Pattern: "*.xml"},
		},
	})
	if err != nil {
		return controller.PublicState{}, err
	}
	if selection == "" {
		return controller.PublicState{}, nil // User cancelled
	}

	return a.loadConfigFile(selection, false) // isAutoLoad = false
}

// GetState returns the current state of the fan controller to the frontend.
func (a *App) GetState() controller.PublicState {
	return a.fanController.GetPublicState()
}

// SetFanMode sets the mode for a specific fan.
func (a *App) SetFanMode(fanIndex int, mode string) error {
	return a.fanController.SetFanMode(fanIndex, controller.FanMode(mode))
}

// SetManualSpeed sets the manual speed for a specific fan.
func (a *App) SetManualSpeed(fanIndex int, speed int) error {
	return a.fanController.SetManualSpeed(fanIndex, speed)
}

// GetSettings returns the current application settings to the frontend.
func (a *App) GetSettings() models.Settings {
	return a.settings
}

// SaveAppSettings saves the provided settings from the frontend.
func (a *App) SaveAppSettings(newSettings models.Settings) error {
	a.settings = newSettings
	a.fanController.UpdateSettings(&a.settings) // Update controller logic

	if err := a.SetAutoStart(newSettings.AutoStart); err != nil {
		log.Printf("Error setting auto-start: %v", err)
		// Return the error to the frontend so the user knows something went wrong.
		return fmt.Errorf("failed to update auto-start setting: %w", err)
	}

	return a.saveSettingsToFile()
}

// SaveFanCurve saves a user-defined fan curve for the currently loaded model.
func (a *App) SaveFanCurve(fanIndex int, thresholds []models.TemperatureThreshold) error {
	config := a.fanController.GetConfig()
	if config == nil || config.ModelName == "" {
		return fmt.Errorf("no config loaded, cannot save fan curve")
	}

	modelName := config.ModelName
	fanIndexStr := fmt.Sprintf("%d", fanIndex)

	if _, ok := a.userProfiles[modelName]; !ok {
		a.userProfiles[modelName] = make(map[string]models.UserProfile)
	}

	a.userProfiles[modelName][fanIndexStr] = models.UserProfile{
		TemperatureThresholds: thresholds,
	}

	// Reload the entire config with the new override applied
	if a.settings.LastConfigPath != "" {
		_, err := a.loadConfigFile(a.settings.LastConfigPath, true)
		if err != nil {
			return fmt.Errorf("failed to reload config with new curve: %w", err)
		}
	}

	return a.saveUserProfilesToFile()
}

// ResetFanCurve removes a user-defined fan curve for the currently loaded model.
func (a *App) ResetFanCurve(fanIndex int) error {
	config := a.fanController.GetConfig()
	if config == nil || config.ModelName == "" {
		return fmt.Errorf("no config loaded, cannot reset fan curve")
	}

	modelName := config.ModelName
	fanIndexStr := fmt.Sprintf("%d", fanIndex)

	if modelProfiles, ok := a.userProfiles[modelName]; ok {
		delete(modelProfiles, fanIndexStr)
		if len(modelProfiles) == 0 {
			delete(a.userProfiles, modelName)
		}
	}

	// Reload the entire config to revert to XML defaults
	if a.settings.LastConfigPath != "" {
		_, err := a.loadConfigFile(a.settings.LastConfigPath, true)
		if err != nil {
			return fmt.Errorf("failed to reload config after reset: %w", err)
		}
	}

	return a.saveUserProfilesToFile()
}

// --- Helper methods ---

func (a *App) loadUserProfiles() error {
	if _, err := os.Stat(a.userProfilesPath); os.IsNotExist(err) {
		a.userProfiles = make(models.UserProfiles)
		return nil
	}
	data, err := os.ReadFile(a.userProfilesPath)
	if err != nil {
		return err
	}
	return json.Unmarshal(data, &a.userProfiles)
}

func (a *App) saveUserProfilesToFile() error {
	data, err := json.MarshalIndent(a.userProfiles, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(a.userProfilesPath, data, 0644)
}

func (a *App) loadConfigFile(path string, isAutoLoad bool) (controller.PublicState, error) {
	config, err := utils.LoadConfigFromXML(path)
	if err != nil {
		return controller.PublicState{}, fmt.Errorf("failed to parse XML config: %w", err)
	}

	// Safety Check: Compare SMBIOS model with the model in the config
	systemModel, err := sensors.GetSystemModel()
	if err != nil {
		log.Printf("Warning: Could not get system model via SMBIOS: %v", err)
	} else {
		// Be lenient in the comparison
		configModelClean := strings.ReplaceAll(strings.ToLower(config.ModelName), " ", "")
		systemModelClean := strings.ReplaceAll(strings.ToLower(systemModel), " ", "")

		if !strings.Contains(systemModelClean, configModelClean) {
			warningMsg := fmt.Sprintf("Model Mismatch Warning!\n\nSystem Model: %s\nConfig Model: %s\n\nUsing a config for a different model can be dangerous. Do you want to proceed?", systemModel, config.ModelName)
			dialogOpts := runtime.MessageDialogOptions{
				Type:    runtime.QuestionDialog,
				Title:   "Model Mismatch",
				Message: warningMsg,
			}
			// Don't show the interactive dialog on startup, just log it.
			if isAutoLoad {
				log.Println(strings.ReplaceAll(warningMsg, "\n\n", " | "))
			} else {
				result, err := runtime.MessageDialog(a.ctx, dialogOpts)
				if err != nil || result != "Yes" {
					return controller.PublicState{}, fmt.Errorf("config load cancelled by user due to model mismatch")
				}
			}
		}
	}

	// Apply user profile override if it exists
	if modelProfiles, ok := a.userProfiles[config.ModelName]; ok {
		log.Printf("Found user profile for model '%s'. Applying overrides.", config.ModelName)
		for i, fanConfig := range config.FanConfigurations {
			fanIndexStr := fmt.Sprintf("%d", i)
			if userFanProfile, ok := modelProfiles[fanIndexStr]; ok {
				fanConfig.TemperatureThresholds = userFanProfile.TemperatureThresholds
				config.FanConfigurations[i] = fanConfig
				log.Printf("-> Applied custom curve to Fan %d", i)
			}
		}
	}

	a.fanController.LoadConfig(config)
	a.fanController.Start()

	a.settings.LastConfigPath = path
	if err := a.saveSettingsToFile(); err != nil {
		log.Printf("Warning: failed to save settings: %v", err)
	}

	log.Printf("Successfully loaded config: %s", path)
	return a.fanController.GetPublicState(), nil
}

func (a *App) loadSettings() error {
	data, err := os.ReadFile(a.settingsPath)
	if err != nil {
		return err
	}
	return json.Unmarshal(data, &a.settings)
}

func (a *App) saveSettingsToFile() error {
	data, err := json.MarshalIndent(a.settings, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(a.settingsPath, data, 0644)
}

func (a *App) SetAutoStart(enabled bool) error {
	const appName = "VortECIO-Go"
	key, err := registry.OpenKey(registry.CURRENT_USER, `Software\Microsoft\Windows\CurrentVersion\Run`, registry.SET_VALUE|registry.QUERY_VALUE)
	if err != nil {
		return fmt.Errorf("failed to open registry key: %w", err)
	}
	defer key.Close()

	if enabled {
		exePath, err := os.Executable()
		if err != nil {
			return fmt.Errorf("failed to get executable path: %w", err)
		}
		return key.SetStringValue(appName, `"`+exePath+`"`)
	}

	err = key.DeleteValue(appName)
	if err != nil && err != registry.ErrNotExist {
		return err // Only return error if it's not a "not found" error
	}
	return nil
}

// runSysTray initializes and runs the system tray icon and menu.
func (a *App) runSysTray() {
	systray.Run(a.onSysTrayReady, a.onSysTrayExit)
}

// onSysTrayReady is called when the systray is ready.
func (a *App) onSysTrayReady() {
	iconBytes, err := os.ReadFile("frontend/src/assets/images/logo-universal.png")
	if err != nil {
		log.Printf("Warning: could not load tray icon: %v", err)
	} else {
		systray.SetIcon(iconBytes)
	}

	systray.SetTitle("VortECIO-Go")
	systray.SetTooltip("VortECIO-Go is running")

	mShow := systray.AddMenuItem("Show", "Show the main window")
	mQuit := systray.AddMenuItem("Quit", "Quit the application")

	go func() {
		for {
			select {
			case <-mShow.ClickedCh:
				runtime.Show(a.ctx)
			case <-mQuit.ClickedCh:
				runtime.Quit(a.ctx)
				return
			}
		}
	}()
}

// onSysTrayExit is called when the systray is exiting.
func (a *App) onSysTrayExit() {}

// UpdateTrayTooltip is the new, correct implementation for updating the tooltip.
func (a *App) UpdateTrayTooltip(tooltip string) {
	systray.SetTooltip(tooltip)
}
