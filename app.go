package main

import (
	"VortECIO-Go/controller"
	"VortECIO-Go/hardware"
	"VortECIO-Go/models"
	"context"
	"encoding/json"
	"encoding/xml"
	"fmt"
	"log"
	"os"
	"path/filepath"

	"github.com/wailsapp/wails/v2/pkg/runtime"
)

// App struct holds the application's state and dependencies.
type App struct {
	ctx           context.Context
	ecDriver      *hardware.EcDriver
	fanController *controller.FanController
	settingsPath  string
}

// Settings struct for storing application settings like the last config path.
type Settings struct {
	LastConfigPath string `json:"last_config_path"`
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

	// Try to auto-load last config
	if err := a.loadLastConfig(); err != nil {
		log.Printf("Could not auto-load last config: %v", err)
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

// --- Helper methods ---

func (a *App) loadConfigFile(path string) (controller.PublicState, error) {
	xmlFile, err := os.ReadFile(path)
	if err != nil {
		return controller.PublicState{}, fmt.Errorf("failed to read config file: %w", err)
	}

	var config models.Config
	if err := xml.Unmarshal(xmlFile, &config); err != nil {
		return controller.PublicState{}, fmt.Errorf("failed to parse XML config: %w", err)
	}

	a.fanController.LoadConfig(&config)
	a.fanController.Start()

	// Save the path for next launch
	if err := a.saveSettings(Settings{LastConfigPath: path}); err != nil {
		log.Printf("Warning: failed to save settings: %v", err)
	}

	log.Printf("Successfully loaded config: %s", path)
	return a.fanController.GetPublicState(), nil
}

func (a *App) loadLastConfig() error {
	settings, err := a.loadSettings()
	if err != nil {
		return err // Could not read settings file
	}

	if settings.LastConfigPath != "" {
		log.Printf("Found last config path: %s", settings.LastConfigPath)
		// Check if file exists before trying to load
		if _, err := os.Stat(settings.LastConfigPath); err == nil {
			_, err := a.loadConfigFile(settings.LastConfigPath)
			return err
		}
		return fmt.Errorf("last config file not found at %s", settings.LastConfigPath)
	}

	return nil // No last config path saved
}


func (a *App) loadSettings() (Settings, error) {
	var settings Settings
	data, err := os.ReadFile(a.settingsPath)
	if err != nil {
		return settings, err
	}
	err = json.Unmarshal(data, &settings)
	return settings, err
}

func (a *App) saveSettings(settings Settings) error {
	data, err := json.MarshalIndent(settings, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(a.settingsPath, data, 0644)
}
