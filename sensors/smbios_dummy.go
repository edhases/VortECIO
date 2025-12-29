//go:build !windows

package sensors

import "fmt"

// GetSystemModel is a dummy implementation for non-Windows systems.
func GetSystemModel() (string, error) {
	return "Dummy Model", fmt.Errorf("SMBIOS reading is only available on Windows")
}
