//go:build !windows

package sensors

import "fmt"

// GetMaxSystemTemperature is a dummy implementation for non-Windows systems.
func GetMaxSystemTemperature() (float64, error) {
	return 0, fmt.Errorf("temperature sensing is only available on Windows")
}
