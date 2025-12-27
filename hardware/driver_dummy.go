//go:build !windows

package hardware

import "fmt"

// EcDriver is a dummy struct for non-Windows systems.
type EcDriver struct{}

// NewEcDriver returns an error on non-Windows systems.
func NewEcDriver() (*EcDriver, error) {
	return nil, fmt.Errorf("EC driver is only available on Windows")
}

// Read is a dummy method for non-Windows systems.
func (d *EcDriver) Read(register int) (byte, error) {
	return 0, fmt.Errorf("EC driver is not available on this platform")
}

// Write is a dummy method for non-Windows systems.
func (d *EcDriver) Write(register int, value byte) error {
	return fmt.Errorf("EC driver is not available on this platform")
}
