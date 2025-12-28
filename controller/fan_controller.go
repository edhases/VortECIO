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
	CriticalTemp               int
	SafetyAction               string
	EnableCriticalTempRecovery bool
	CriticalTempRecoveryDelta  int
}

// FanState represents the current runtime state of a single fan.
type FanState struct {
	Mode                FanMode
	ManualSpeed         int // User-set percentage (0-100) for Manual mode
	TargetSpeedPercent  int // The speed calculated by the fan curve
	CurrentSpeed        int // The smoothed speed being written to the EC
	ReadSpeedPercent    int // Speed percentage read back from the EC
	CurrentRPM          int // Actual RPM read from the sensor
	LastValidRPM        int // Used for spike filter
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
	Name                  string                        `json:"name"`
	Mode                  FanMode                       `json:"mode"`
	ManualSpeed           int                           `json:"manualSpeed"`
	TargetSpeedPercent    int                           `json:"targetSpeedPercent"`
	ReadSpeedPercent      int                           `json:"readSpeedPercent"`
	CurrentRPM            int                           `json:"currentRpm"`
	TemperatureThresholds []models.TemperatureThreshold `json:"temperatureThresholds"`
}

// SensorSource defines the origin of temperature data.
type SensorSource string

const (
	SensorSourceSidecar SensorSource = "Sidecar"
	SensorSourceWMI     SensorSource = "WMI"
)

// AppController defines the interface for the main application controller.
type AppController interface {
	UpdateTrayTooltip(tooltip string)
}

// FanController manages the core fan control logic in a separate goroutine.
type FanController struct {
	ecDriver                 hardware.ECDriver // Use the interface
	config                   *models.Config
	settings                 SettingsSnapshot
	sensorSource             SensorSource
	onTempUpdate             func(tooltip string) // Callback to update UI elements like tray tooltip
	fanStates                []FanState
	inCriticalState          bool // Flag to track if we are in a critical temp state
	stateMutex               sync.RWMutex
	lastTemp                 float64
	lastGpuTemp              float64
	lastSuccessfulTempUpdate time.Time
	ctx                      context.Context
	cancel                   context.CancelFunc
	wg                       sync.WaitGroup
}

// NewFanController creates a new, uninitialized fan controller.
func NewFanController(ctx context.Context, driver hardware.ECDriver, onTempUpdate func(tooltip string)) *FanController {
	return &FanController{
		ctx:          ctx,
		ecDriver:     driver,
		onTempUpdate: onTempUpdate,
		sensorSource: SensorSourceWMI, // Default to WMI
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
	fc.settings.EnableCriticalTempRecovery = newSettings.EnableCriticalTempRecovery
	fc.settings.CriticalTempRecoveryDelta = newSettings.CriticalTempRecoveryDelta
	log.Printf("Fan controller settings updated: CritTemp=%d, SafetyAction=%s, RecoveryEnabled=%t, RecoveryDelta=%d",
		fc.settings.CriticalTemp, fc.settings.SafetyAction, fc.settings.EnableCriticalTempRecovery, fc.settings.CriticalTempRecoveryDelta)
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

	// Update tray tooltip with current temperatures
	tooltip := fmt.Sprintf("CPU: %.1f°C", fc.lastTemp)
	if fc.lastGpuTemp > 0 {
		tooltip += fmt.Sprintf(" | GPU: %.1f°C", fc.lastGpuTemp)
	}
	if fc.onTempUpdate != nil {
		fc.onTempUpdate(tooltip)
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

// GetConfig safely returns the current configuration.
func (fc *FanController) GetConfig() *models.Config {
	fc.stateMutex.RLock()
	defer fc.stateMutex.RUnlock()
	return fc.config
}

// SetSensorSource safely switches the temperature data source.
func (fc *FanController) SetSensorSource(source SensorSource) {
	fc.stateMutex.Lock()
	defer fc.stateMutex.Unlock()
	if fc.sensorSource != source {
		log.Printf("Switching sensor source from %s to %s", fc.sensorSource, source)
		fc.sensorSource = source
		// Reset last update time to allow WMI to fetch immediately
		fc.lastSuccessfulTempUpdate = time.Time{}
	}
}

// UpdateTemperatures is called by the MonitorService to push new temperature data.
func (fc *FanController) UpdateTemperatures(cpuTemp, gpuTemp float32) {
	fc.stateMutex.Lock()
	defer fc.stateMutex.Unlock()

	// This method should only be active if the source is the sidecar
	if fc.sensorSource == SensorSourceSidecar {
		fc.lastTemp = float64(cpuTemp)
		fc.lastGpuTemp = float64(gpuTemp)
		fc.lastSuccessfulTempUpdate = time.Now()
	}
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
			Name:                  fc.config.FanConfigurations[i].FanDisplayName,
			Mode:                  fan.Mode,
			ManualSpeed:           fan.ManualSpeed,
			TargetSpeedPercent:    fan.TargetSpeedPercent,
			ReadSpeedPercent:      fan.ReadSpeedPercent,
			CurrentRPM:            fan.CurrentRPM,
			TemperatureThresholds: fc.config.FanConfigurations[i].TemperatureThresholds,
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
	// Step 1: Handle temperature reading based on the current source.
	// WMI is polled, Sidecar data is pushed.
	if fc.sensorSource == SensorSourceWMI {
		temps, err := sensors.GetSystemTemperatures()
		if err != nil {
			log.Printf("Warning: Failed to read temperature from WMI: %v", err)
		} else {
			fc.stateMutex.Lock()
			fc.lastTemp = temps.MaxCpuTemp
			fc.lastGpuTemp = temps.GpuTemp
			fc.lastSuccessfulTempUpdate = time.Now()
			fc.stateMutex.Unlock()
		}
	}

	// Update tray tooltip with current temperatures
	tooltip := fmt.Sprintf("CPU: %.1f°C", fc.lastTemp)
	if fc.lastGpuTemp > 0 {
		tooltip += fmt.Sprintf(" | GPU: %.1f°C", fc.lastGpuTemp)
	}
	if fc.onTempUpdate != nil {
		fc.onTempUpdate(tooltip)
	}

	// Step 2: Lock the mutex for the rest of the tick.
	fc.stateMutex.Lock()
	defer fc.stateMutex.Unlock()

	// Watchdog: Check for stale data regardless of source.
	if !fc.lastSuccessfulTempUpdate.IsZero() && time.Since(fc.lastSuccessfulTempUpdate) > 20*time.Second {
		log.Printf("CRITICAL: Temperature data is stale for >20s. Forcing fans to 100%%.")
		for i := range fc.fanStates {
			fc.fanStates[i].Mode = ModeManual
			fc.fanStates[i].ManualSpeed = 100
		}
		// Skip the rest of the tick to avoid acting on stale data
		return
	}

	effectiveTemp := math.Max(fc.lastTemp, fc.lastGpuTemp)

	// Critical Temperature Safety Logic
	recoveryThreshold := float64(fc.settings.CriticalTemp - fc.settings.CriticalTempRecoveryDelta)

	if fc.inCriticalState {
		// If in critical state, check if we should recover
		if fc.settings.EnableCriticalTempRecovery && effectiveTemp < recoveryThreshold {
			log.Printf("INFO: Temperature %.1f°C is below recovery threshold of %.1f°C. Restoring Auto mode.", effectiveTemp, recoveryThreshold)
			for i := range fc.fanStates {
				fc.fanStates[i].Mode = ModeAuto
			}
			fc.inCriticalState = false
		}
	} else {
		// If not in critical state, check if we should enter it
		if effectiveTemp > float64(fc.settings.CriticalTemp) {
			log.Printf("CRITICAL: Temp %.1f°C exceeds %d°C. Action: %s", effectiveTemp, fc.settings.CriticalTemp, fc.settings.SafetyAction)
			fc.inCriticalState = true
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

// calculateSpeedForTemp determines fan speed with proper hysteresis.
func calculateSpeedForTemp(temp float64, lastSpeed int, thresholds []models.TemperatureThreshold) int {
	// Determine the current speed level based on the last known speed.
	// This helps us find the correct DownThreshold to use.
	currentLevelIndex := -1
	for i, t := range thresholds {
		if float64(lastSpeed) == t.FanSpeed {
			currentLevelIndex = i
			break
		}
	}

	// If temperature is rising
	// Find the highest threshold that the temperature has crossed from below.
	newSpeed := 0.0
	for _, t := range thresholds {
		if temp >= float64(t.UpThreshold) {
			newSpeed = t.FanSpeed
		}
	}

	// If the new speed (from rising temp) is higher than the last speed, we apply it.
	if newSpeed > float64(lastSpeed) {
		return int(newSpeed)
	}

	// If temperature is falling or stable, and we have a current speed level
	if currentLevelIndex != -1 {
		// Check if the temperature has dropped below the DownThreshold for the *current* level.
		currentThreshold := thresholds[currentLevelIndex]
		if temp < float64(currentThreshold.DownThreshold) {
			// If it has, we can safely drop to the speed of the *next lower* level.
			if currentLevelIndex > 0 {
				return int(thresholds[currentLevelIndex-1].FanSpeed)
			}
			return 0 // We were at the lowest level, so now we turn off.
		}
	}

	// If none of the above conditions are met, maintain the last speed.
	// This covers the hysteresis zone (between DownThreshold and UpThreshold).
	return lastSpeed
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
