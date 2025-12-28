//go:build windows

package utils

import (
	"os"
	"path/filepath"
)

// GetBaseDir returns the directory of the executable.
func GetBaseDir() (string, error) {
	exePath, err := os.Executable()
	if err != nil {
		return "", err
	}
	return filepath.Dir(exePath), nil
}
