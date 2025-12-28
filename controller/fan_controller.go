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
	Mode               FanMode
	ManualSpeed        int // User-set percentage (0-100) for Manual mode
	TargetSpeedPercent int // The speed calculated by the fan curve
	CurrentSpeed       int // The smoothed speed being written to the EC
	ReadSpeedPercent   int // Speed percentage read back from the EC
	CurrentRPM         int // Actual RPM read from the sensor
	LastValidRPM       int // Used for spike filter
	biosControlReleased bool
}

// PublicState is a simplified, thread-safe representation of the controller's state for the UI.
type PublicState struct {
	SystemTemp float64
	GpuTemp    float64
	Fans       []PublicFanState
	ModelName  string
}

type PublicFanState struct {
	Name               string  `json:"name"`
	Mode               FanMode `json:"mode"`
	ManualSpeed        int     `json:"manualSpeed"`
	TargetSpeedPercent int     `json:"targetSpeedPercent"`
	ReadSpeedPercent   int     `json:"readSpeedPercent"`
	CurrentRPM         int     `json:"currentRpm"`
}

// FanController manages the core fan control logic in a separate goroutine.
type FanController struct {
	ecDriver hardware.ECDriver // Use the interface
	config   *models.Config
	settings SettingsSnapshot

	fanStates  []FanState
	stateMutex sync.RWMutex

	lastTemp                 float64
	lastGpuTemp              float64 // Нове поле для кешування
	lastSuccessfulTempUpdate time.Time

	ctx    context.Context
	cancel context.CancelFunc
	wg     sync.WaitGroup
}

// NewFanController creates a new, uninitialized fan controller.
func NewFanController(driver hardware.ECDriver) *FanController {
	return &FanController{
		ecDriver: driver,
		settings: SettingsSnapshot{ // Default safety settings
			CriticalTemp: 80,
			SafetyAction: "bios_control",
		},
		lastSuccessfulTempUpdate: time.Now(), // Initialize to prevent immediate trigger
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

	// Pre-sort temperature thresholds for performance
	for i := range config.FanConfigurations {
		sort.Slice(config.FanConfigurations[i].TemperatureThresholds, func(j, k int) bool {
			return config.FanConfigurations[i].TemperatureThresholds[j].UpThreshold < config.FanConfigurations[i].TemperatureThresholds[k].UpThreshold
		})
	}

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
		GpuTemp:    fc.lastGpuTemp,
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
			CurrentRPM:         fan.CurrentRPM,
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
	// Step 1: Read sensors without locking the mutex to avoid blocking the UI.
	temps, err := sensors.GetSystemTemperatures()

	// Step 2: Lock the mutex only for the duration of state updates.
	fc.stateMutex.Lock()
	defer fc.stateMutex.Unlock()

	if err != nil {
		log.Printf("Warning: Failed to read temperature: %v", err)
		// Watchdog: If temp data is stale, force high fan speed for safety.
		if !fc.lastSuccessfulTempUpdate.IsZero() && time.Since(fc.lastSuccessfulTempUpdate) > 20*time.Second {
			log.Printf("CRITICAL: Temperature data is stale for >20s. Forcing fans to 100%%.")
			for i := range fc.fanStates {
				fc.fanStates[i].Mode = ModeManual
				fc.fanStates[i].ManualSpeed = 100
			}
		}
	} else {
		fc.lastTemp = temps.MaxCpuTemp
		fc.lastGpuTemp = temps.GpuTemp
		fc.lastSuccessfulTempUpdate = time.Now()
	}

	effectiveTemp := math.Max(fc.lastTemp, fc.lastGpuTemp)

	// Safety logic for critical temperature
	if effectiveTemp > float64(fc.settings.CriticalTemp) {
		log.Printf("CRITICAL: Temp %.1f°C exceeds %d°C. Action: %s", effectiveTemp, fc.settings.CriticalTemp, fc.settings.SafetyAction)
		if fc.settings.SafetyAction == "bios_control" {
			fc.releaseAllFansToBios()
			for i := range fc.fanStates {
				fc.fanStates[i].Mode = ModeDisabled
			}
			return // Stop processing this tick
		} else { // "force_full_speed"
			for i := range fc.fanStates {
				fc.fanStates[i].Mode = ModeManual
				fc.fanStates[i].ManualSpeed = 100
			}
		}
	}

	if fc.config == nil {
		return
	}

	// --- Pass 1: Read RPM and current speed for all fans ---
	for i, fanConfig := range fc.config.FanConfigurations {
		state := &fc.fanStates[i]
		if fanConfig.RpmRegister > 0 {
			rawRpm, err := fc.ecDriver.ReadWord(fanConfig.RpmRegister)
			if err == nil && isValidRPM(rawRpm) {
				diff := int(math.Abs(float64(rawRpm - state.LastValidRPM)))
				if state.LastValidRPM == 0 || diff < 3000 {
					state.CurrentRPM = rawRpm
					state.LastValidRPM = rawRpm
				}
			}
		}
		rawValue, err := fc.ecDriver.Read(fanConfig.ReadRegister)
		if err == nil {
			state.ReadSpeedPercent = int(math.Round(float64(rawValue) / 255.0 * 100.0))
		} else {
			state.ReadSpeedPercent = -1
		}
	}

	// --- Pass 2: Calculate target speed and write to EC ---
	for i, fanConfig := range fc.config.FanConfigurations {
		state := &fc.fanStates[i]

		switch state.Mode {
		case ModeAuto:
			state.TargetSpeedPercent = calculateSpeedForTemp(effectiveTemp, state.TargetSpeedPercent, fanConfig.TemperatureThresholds)
			state.biosControlReleased = false
		case ModeManual:
			state.TargetSpeedPercent = state.ManualSpeed
			state.biosControlReleased = false
		case ModeReadOnly, ModeDisabled:
			if !state.biosControlReleased && fanConfig.ResetRequired {
				if err := fc.ecDriver.Write(fanConfig.WriteRegister, byte(fanConfig.FanSpeedResetValue)); err != nil {
					log.Printf("Error releasing fan %d to BIOS control: %v", i, err)
				}
				state.biosControlReleased = true
			}
			continue
		}

		// Smoothing logic
		const smoothingStep = 10
		if state.CurrentSpeed < state.TargetSpeedPercent {
			state.CurrentSpeed = min(state.CurrentSpeed+smoothingStep, state.TargetSpeedPercent)
		} else if state.CurrentSpeed > state.TargetSpeedPercent {
			state.CurrentSpeed = max(state.CurrentSpeed-smoothingStep, state.TargetSpeedPercent)
		}

		ecValue := scaleSpeedToECValue(state.CurrentSpeed, fanConfig.MinSpeedValue, fanConfig.MaxSpeedValue)
		// Only write if the value is different to avoid unnecessary EC communication
		if state.CurrentSpeed != state.ReadSpeedPercent {
			if err := fc.ecDriver.Write(fanConfig.WriteRegister, ecValue); err != nil {
				log.Printf("Error writing to EC for fan %d: %v", i, err)
			}
		}
	}
}

// isValidRPM checks if an RPM value is within a plausible range.
func isValidRPM(val int) bool {
	return val != 0xFFFF && val >= 0 && val < 15000
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
			if err := fc.ecDriver.Write(fanConfig.WriteRegister, byte(fanConfig.FanSpeedResetValue)); err != nil {
				log.Printf("Error releasing fan %d to BIOS control during shutdown: %v", i, err)
			}
		}
	}
}

// calculateSpeedForTemp determines fan speed with hysteresis.
func calculateSpeedForTemp(temp float64, currentSpeed int, thresholds []models.TemperatureThreshold) int {
	// Find the highest threshold we are currently at or above
	for i := len(thresholds) - 1; i >= 0; i-- {
		t := thresholds[i]
		if temp >= float64(t.UpThreshold) {
			return int(t.FanSpeed)
		}
	}

	// If below all UpThresholds, find where we are relative to DownThresholds
	for i, t := range thresholds {
		if temp < float64(t.DownThreshold) {
			if i > 0 {
				return int(thresholds[i-1].FanSpeed)
			}
			return 0 // Below the lowest threshold
		}
	}
	return currentSpeed // Maintain speed if in hysteresis zone
}

// scaleSpeedToECValue converts a 0-100 percentage to the raw EC value.
func scaleSpeedToECValue(percent, minVal, maxVal int) byte {
	if percent <= 0 {
		return byte(minVal)
	}
	if percent >= 100 {
		return byte(maxVal)
	}
	val := minVal + int(math.Round(float64(maxVal-minVal)*float64(percent)/100.0))
	return byte(val)
}
