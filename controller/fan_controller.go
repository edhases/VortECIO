package controller

import (
	"VortECIO-Go/hardware"
	"VortECIO-Go/models"
	"VortECIO-Go/sensors"
	"context"
	"fmt"
	"log"
	"math"
	"sort"
	"sync"
	"time"
)

// FanMode defines the operating mode for a fan.
type FanMode string

const (
	ModeAuto     FanMode = "Auto"
	ModeManual   FanMode = "Manual"
	ModeReadOnly FanMode = "Read-only"
	ModeDisabled FanMode = "Disabled"
)

// SettingsSnapshot holds a copy of the main app settings relevant to the controller.
type SettingsSnapshot struct {
	CriticalTemp int
	SafetyAction string
}

// FanState represents the current runtime state of a single fan.
type FanState struct {
	Mode                FanMode
	ManualSpeed         int // User-set percentage (0-100) for Manual mode
	TargetSpeedPercent  int // Last calculated/set speed percentage
	ReadSpeedPercent    int // Speed percentage read back from the EC
	biosControlReleased bool
}

// PublicState is a simplified, thread-safe representation of the controller's state for the UI.
type PublicState struct {
	SystemTemp float64
	GpuTemp    float64 // Нове поле
	Fans       []PublicFanState
	ModelName  string
}

type PublicFanState struct {
	Name               string
	Mode               FanMode
	ManualSpeed        int
	TargetSpeedPercent int
	ReadSpeedPercent   int
}

// FanController manages the core fan control logic in a separate goroutine.
type FanController struct {
	ecDriver *hardware.EcDriver
	config   *models.Config
	settings SettingsSnapshot

	fanStates  []FanState
	stateMutex sync.RWMutex

	lastTemp    float64
	lastGpuTemp float64 // Нове поле для кешування

	ctx    context.Context
	cancel context.CancelFunc
	wg     sync.WaitGroup
}

// NewFanController creates a new, uninitialized fan controller.
func NewFanController(driver *hardware.EcDriver) *FanController {
	return &FanController{
		ecDriver: driver,
		settings: SettingsSnapshot{ // Default safety settings
			CriticalTemp: 80,
			SafetyAction: "bios_control",
		},
	}
}

// UpdateSettings safely updates the controller's settings from the main app.
func (fc *FanController) UpdateSettings(newSettings *models.Settings) {
	fc.stateMutex.Lock()
	defer fc.stateMutex.Unlock()
	fc.settings.CriticalTemp = newSettings.CriticalTemp
	fc.settings.SafetyAction = newSettings.SafetyAction
	log.Printf("Fan controller settings updated: CritTemp=%d, SafetyAction=%s", fc.settings.CriticalTemp, fc.settings.SafetyAction)
}

// LoadConfig applies a new configuration and initializes the fan states.
func (fc *FanController) LoadConfig(config *models.Config) {
	fc.stateMutex.Lock()
	defer fc.stateMutex.Unlock()

	fc.Stop() // Stop any previous control loop

	fc.config = config
	fc.fanStates = make([]FanState, len(config.FanConfigurations))
	for i := range fc.fanStates {
		fc.fanStates[i] = FanState{
			Mode:        ModeAuto, // Default to Auto mode
			ManualSpeed: 50,
		}
	}
}

// Start launches the main control loop in a background goroutine.
func (fc *FanController) Start() {
	fc.stateMutex.Lock()
	defer fc.stateMutex.Unlock()

	if fc.config == nil || fc.cancel != nil {
		return // Not configured or already running
	}

	fc.ctx, fc.cancel = context.WithCancel(context.Background())
	fc.wg.Add(1)
	go fc.controlLoop()
	log.Println("Fan Controller started.")
}

// Stop gracefully terminates the control loop.
func (fc *FanController) Stop() {
	if fc.cancel != nil {
		fc.cancel()
		fc.wg.Wait()
		fc.cancel = nil
		log.Println("Fan Controller stopped.")
	}
}

// SetFanMode updates the operating mode for a specific fan.
func (fc *FanController) SetFanMode(fanIndex int, mode FanMode) error {
	fc.stateMutex.Lock()
	defer fc.stateMutex.Unlock()
	if fanIndex < 0 || fanIndex >= len(fc.fanStates) {
		return fmt.Errorf("invalid fan index: %d", fanIndex)
	}
	fc.fanStates[fanIndex].Mode = mode
	// When switching to a mode that gives BIOS control, mark it as needing a reset write.
	if mode == ModeDisabled || mode == ModeReadOnly {
		fc.fanStates[fanIndex].biosControlReleased = false
	}
	return nil
}

// SetManualSpeed sets the target speed for a fan in Manual mode.
func (fc *FanController) SetManualSpeed(fanIndex int, speed int) error {
	fc.stateMutex.Lock()
	defer fc.stateMutex.Unlock()
	if fanIndex < 0 || fanIndex >= len(fc.fanStates) {
		return fmt.Errorf("invalid fan index: %d", fanIndex)
	}
	if speed < 0 {
		speed = 0
	}
	if speed > 100 {
		speed = 100
	}
	fc.fanStates[fanIndex].ManualSpeed = speed
	return nil
}

// GetPublicState returns a thread-safe snapshot of the current state for UI rendering.
func (fc *FanController) GetPublicState() PublicState {
	fc.stateMutex.RLock()
	defer fc.stateMutex.RUnlock()

	if fc.config == nil {
		return PublicState{}
	}

	state := PublicState{
		SystemTemp: fc.lastTemp,
		GpuTemp:    fc.lastGpuTemp, // Передаємо на фронт
		ModelName:  fc.config.ModelName,
		Fans:       make([]PublicFanState, len(fc.fanStates)),
	}

	for i, fan := range fc.fanStates {
		state.Fans[i] = PublicFanState{
			Name:               fc.config.FanConfigurations[i].FanDisplayName,
			Mode:               fan.Mode,
			ManualSpeed:        fan.ManualSpeed,
			TargetSpeedPercent: fan.TargetSpeedPercent,
			ReadSpeedPercent:   fan.ReadSpeedPercent,
		}
	}
	return state
}


// controlLoop is the heart of the fan controller.
func (fc *FanController) controlLoop() {
	defer fc.wg.Done()

	// Use config's poll interval, with a fallback
	interval := time.Duration(1000) * time.Millisecond
	if fc.config != nil && fc.config.EcPollInterval > 0 {
		interval = time.Duration(fc.config.EcPollInterval) * time.Millisecond
	}
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-fc.ctx.Done():
			fc.releaseAllFansToBios()
			return
		case <-ticker.C:
			fc.tick()
		}
	}
}

// tick performs a single control cycle.
func (fc *FanController) tick() {
	// КРОК 1: Читаємо сенсори БЕЗ блокування м'ютекса!
	// Це займає час (WMI повільний), але тепер це не блокує UI.
	temps, err := sensors.GetSystemTemperatures()

	// КРОК 2: Блокуємо м'ютекс тільки для оновлення стану
	fc.stateMutex.Lock()
	defer fc.stateMutex.Unlock()

	if err != nil {
		log.Printf("Warning: Failed to read temperature: %v", err)
		// Продовжуємо зі старими значеннями
	} else {
		fc.lastTemp = temps.MaxCpuTemp
		fc.lastGpuTemp = temps.GpuTemp
	}

	// Використовуємо максимальну температуру для захисту (безпечніше)
	effectiveTemp := fc.lastTemp
	if fc.lastGpuTemp > effectiveTemp {
		effectiveTemp = fc.lastGpuTemp
	}

	// Safety logic based on settings
	if effectiveTemp > float64(fc.settings.CriticalTemp) {
		log.Printf("CRITICAL: Temperature %.1f°C exceeds threshold of %d°C. Action: %s", effectiveTemp, fc.settings.CriticalTemp, fc.settings.SafetyAction)
		switch fc.settings.SafetyAction {
		case "bios_control":
			fc.releaseAllFansToBios()
			for i := range fc.fanStates {
				fc.fanStates[i].Mode = ModeDisabled
			}
			return // Stop further processing this tick
		case "force_full_speed":
			for i := range fc.fanStates {
				fc.fanStates[i].Mode = ModeManual
				fc.fanStates[i].ManualSpeed = 100
			}
			// Continue to the main loop to apply 100% speed
		}
	}

	if fc.config == nil {
		return
	}

	for i, fanConfig := range fc.config.FanConfigurations {
		state := &fc.fanStates[i]
		var targetSpeedPercent int

		// Read current speed BEFORE deciding what to write
		rawValue, err := fc.ecDriver.Read(fanConfig.ReadRegister)
		if err != nil {
			log.Printf("Error reading fan %d speed: %v", i, err)
			state.ReadSpeedPercent = -1 // Indicate error
		} else {
			// Assuming the read value scales linearly from 0-255 to 0-100%
			state.ReadSpeedPercent = int(math.Round(float64(rawValue) / 255.0 * 100.0))
		}

		switch state.Mode {
		case ModeAuto:
			targetSpeedPercent = calculateSpeedForTemp(effectiveTemp, fanConfig.TemperatureThresholds)
			state.biosControlReleased = false
		case ModeManual:
			targetSpeedPercent = state.ManualSpeed
			state.biosControlReleased = false
		case ModeReadOnly:
			// Only read, do not write.
			continue
		case ModeDisabled:
			// Release control to BIOS if not already done.
			if !state.biosControlReleased {
				if fanConfig.ResetRequired {
					log.Printf("Fan %d (%s): Releasing control to BIOS (writing %d)", i, fanConfig.FanDisplayName, fanConfig.FanSpeedResetValue)
					fc.ecDriver.Write(fanConfig.WriteRegister, byte(fanConfig.FanSpeedResetValue))
				}
				state.biosControlReleased = true
			}
			continue
		}

		state.TargetSpeedPercent = targetSpeedPercent
		ecValue := scaleSpeedToECValue(targetSpeedPercent, fanConfig.MinSpeedValue, fanConfig.MaxSpeedValue)

		err = fc.ecDriver.Write(fanConfig.WriteRegister, ecValue)
		if err != nil {
			log.Printf("Error writing to EC for fan %d: %v", i, err)
		}
	}
}

// releaseAllFansToBios is a utility function for shutdown or panic mode.
func (fc *FanController) releaseAllFansToBios() {
	log.Println("Attempting to release all fans to BIOS control...")
	if fc.config == nil {
		return
	}
	for i, fanConfig := range fc.config.FanConfigurations {
		if fanConfig.ResetRequired {
			log.Printf("Fan %d (%s): Releasing control", i, fanConfig.FanDisplayName)
			fc.ecDriver.Write(fanConfig.WriteRegister, byte(fanConfig.FanSpeedResetValue))
		}
	}
}

// calculateSpeedForTemp determines the appropriate fan speed for a given temperature.
func calculateSpeedForTemp(temp float64, thresholds []models.TemperatureThreshold) int {
	sort.Slice(thresholds, func(i, j int) bool {
		return thresholds[i].UpThreshold < thresholds[j].UpThreshold
	})

	speed := 0.0
	for _, t := range thresholds {
		if temp >= float64(t.UpThreshold) {
			speed = t.FanSpeed
		} else {
			break
		}
	}
	return int(speed)
}

// scaleSpeedToECValue converts a 0-100 percentage to the raw EC value.
func scaleSpeedToECValue(percent, minVal, maxVal int) byte {
	if percent <= 0 {
		return byte(minVal)
	}
	if percent >= 100 {
		return byte(maxVal)
	}
	val := minVal + ((maxVal - minVal) * percent / 100)
	return byte(val)
}
