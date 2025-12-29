//go:build windows

package utils

import (
	"os"
	"path/filepath"
)

// GetBaseDir determines the base directory of the application.
// For development (`wails dev`), it's the working directory.
// For a built executable, it's the directory of the executable.
func GetBaseDir() (string, error) {
	// Get current working directory for dev mode
	wd, err := os.Getwd()
	if err == nil {
		// Check if 'plugins' directory exists, a good indicator of running in dev mode from the project root.
		if _, err := os.Stat(filepath.Join(wd, "plugins")); err == nil {
			return wd, nil
		}
	}

	// Fallback for production: get the directory of the executable.
	exePath, err := os.Executable()
	if err != nil {
		return "", err
	}
	return filepath.Dir(exePath), nil
}
