//go:build windows

package main

import (
	"VortECIO-Go/controller"
	"VortECIO-Go/hardware"
	"VortECIO-Go/models"
	"VortECIO-Go/utils" // Import the new utils package
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"

	"github.com/wailsapp/wails/v2/pkg/runtime"
	"golang.org/x/sys/windows/registry"
)

// App struct holds the application's state and dependencies.
type App struct {
	ctx           context.Context
	ecDriver      *hardware.EcDriver
	fanController *controller.FanController
	settings      models.Settings
	settingsPath  string
}

// NewApp creates a new App application struct.
func NewApp() *App {
	return &App{}
}

// startup is called when the app starts.
func (a *App) startup(ctx context.Context) {
	a.ctx = ctx

	// Determine settings path
	exePath, err := os.Executable()
	if err != nil {
		log.Printf("Warning: could not determine executable path: %v", err)
	}
	a.settingsPath = filepath.Join(filepath.Dir(exePath), "settings.json")

	// Load settings or create default
	if err := a.loadSettings(); err != nil {
		log.Printf("Could not load settings, creating default: %v", err)
		a.settings = models.Settings{
			Language:     "en",
			AutoStart:    false,
			CriticalTemp: 80,
			SafetyAction: "bios_control",
		}
		// Try to save the new default settings
		if err := a.saveSettingsToFile(); err != nil {
			log.Printf("Warning: failed to save default settings: %v", err)
		}
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
	a.fanController = controller.NewFanController(a.ecDriver)
	a.fanController.UpdateSettings(&a.settings) // Pass initial settings to controller

	// Try to auto-load last config
	if a.settings.LastConfigPath != "" {
		log.Printf("Found last config path: %s", a.settings.LastConfigPath)
		if _, err := os.Stat(a.settings.LastConfigPath); err == nil {
			a.loadConfigFile(a.settings.LastConfigPath)
		} else {
			log.Printf("Warning: last config file not found at %s", a.settings.LastConfigPath)
		}
	}
}

// shutdown is called when the app is closing.
func (a *App) shutdown(ctx context.Context) {
	log.Println("Shutting down...")
	a.fanController.Stop()
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

	return a.loadConfigFile(selection)
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

	if err := a.SetAutoStart(a.settings.AutoStart); err != nil {
		log.Printf("Error setting auto-start: %v", err)
		// Return the error to the frontend so the user knows something went wrong.
		return fmt.Errorf("failed to update auto-start setting: %w", err)
	}

	return a.saveSettingsToFile()
}

// --- Helper methods ---

func (a *App) loadConfigFile(path string) (controller.PublicState, error) {
	config, err := utils.LoadConfigFromXML(path)
	if err != nil {
		return controller.PublicState{}, err // Pass the error up
	}

	a.fanController.LoadConfig(config)
	a.fanController.Start()

	// Save the path for next launch
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

// SetAutoStart adds or removes the application from the Windows startup registry.
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
		// Set the value to the path of the executable, enclosed in quotes.
		return key.SetStringValue(appName, fmt.Sprintf(`"%s"`, exePath))
	}

	// If not enabled, delete the key.
	// It's safe to call DeleteValue even if the value doesn't exist.
	return key.DeleteValue(appName)
}
