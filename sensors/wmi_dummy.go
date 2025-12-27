//go:build !windows

package sensors

import "fmt"

// SystemTemps містить знайдені температури (dummy version)
type SystemTemps struct {
	MaxCpuTemp float64
	GpuTemp    float64
}

// GetSystemTemperatures is a dummy implementation for non-Windows systems.
func GetSystemTemperatures() (SystemTemps, error) {
	// Return zero values and a platform error.
	return SystemTemps{}, fmt.Errorf("temperature sensing is only available on Windows")
}
