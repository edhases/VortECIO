//go:build !windows

package main

import (
	"VortECIO-Go/controller"
	"VortECIO-Go/models"
	"context"
	"fmt"
	"log"
)

// App is a dummy struct for non-Windows systems.
type App struct {
	ctx context.Context
}

// NewApp creates a new App application struct.
func NewApp() *App {
	return &App{}
}

func (a *App) startup(ctx context.Context) {
	a.ctx = ctx
	log.Println("Dummy App started on non-Windows platform.")
}

func (a *App) LoadConfig() (controller.PublicState, error) {
	return controller.PublicState{}, fmt.Errorf("not implemented on this platform")
}

func (a *App) GetState() controller.PublicState {
	// Return a mock state so the UI can render something.
	return controller.PublicState{
		ModelName: "Dummy Model (Non-Windows)",
		SystemTemp: 42.0,
		Fans: []controller.PublicFanState{
			{Name: "CPU Fan", Mode: "Auto", ManualSpeed: 50, ReadSpeedPercent: 35, TargetSpeedPercent: 35},
			{Name: "GPU Fan", Mode: "Manual", ManualSpeed: 75, ReadSpeedPercent: 70, TargetSpeedPercent: 75},
		},
	}
}

func (a *App) SetFanMode(fanIndex int, mode string) error {
	log.Printf("Dummy SetFanMode called: index=%d, mode=%s", fanIndex, mode)
	return nil
}

func (a *App) SetManualSpeed(fanIndex int, speed int) error {
	log.Printf("Dummy SetManualSpeed called: index=%d, speed=%d", fanIndex, speed)
	return nil
}

func (a *App) GetSettings() models.Settings {
	return models.Settings{
		Language:     "en",
		AutoStart:    false,
		CriticalTemp: 80,
		SafetyAction: "bios_control",
	}
}

func (a *App) SaveAppSettings(newSettings models.Settings) error {
	log.Printf("Dummy SaveAppSettings called: %+v", newSettings)
	return nil
}
