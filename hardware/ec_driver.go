//go:build windows

package hardware

import (
	"fmt"
	"os"
	"sync"
	"syscall"
	"time"
)

const (
	ecDataPort    = 0x62
	ecCommandPort = 0x66
	statusIbf     = 1 // Input Buffer Full bit
	statusObf     = 0 // Output Buffer Full bit
	dllName       = "inpoutx64.dll"
)

// EcDriver handles low-level communication with the Embedded Controller (EC)
// via the inpoutx64.dll driver. It ensures thread-safe access to EC ports.
type EcDriver struct {
	dll   *syscall.LazyDLL
	out32 *syscall.LazyProc
	inp32 *syscall.LazyProc
	mutex sync.Mutex
}

// NewEcDriver attempts to load inpoutx64.dll and initializes the driver.
// It returns an error if the DLL cannot be loaded or procedures are not found.
func NewEcDriver() (*EcDriver, error) {
	// First, check if the DLL file exists in the current directory.
	if _, err := os.Stat(dllName); os.IsNotExist(err) {
		return nil, fmt.Errorf("critical driver file not found: %s. Please ensure it is in the same directory as the application", dllName)
	}

	dll := syscall.NewLazyDLL(dllName)
	if err := dll.Load(); err != nil {
		return nil, fmt.Errorf("critical: failed to load %s: %w. This may be due to antivirus software or missing permissions", dllName, err)
	}

	out32 := dll.NewProc("Out32")
	inp32 := dll.NewProc("Inp32")

	// A basic check to see if the procedures were found.
	if out32.Find() != nil || inp32.Find() != nil {
		return nil, fmt.Errorf("critical: could not find Inp32/Out32 procedures in %s", dllName)
	}

	return &EcDriver{
		dll:   dll,
		out32: out32,
		inp32: inp32,
	}, nil
}

// Read queries a value from a specific register in the EC.
func (d *EcDriver) Read(register int) (byte, error) {
	d.mutex.Lock()
	defer d.mutex.Unlock()

	if err := d.waitIBF(); err != nil {
		return 0, fmt.Errorf("EC read failed during pre-command wait: %w", err)
	}

	// Send read command (0x80) to the EC
	d.out32.Call(uintptr(ecCommandPort), uintptr(0x80))

	if err := d.waitIBF(); err != nil {
		return 0, fmt.Errorf("EC read failed during address wait: %w", err)
	}

	// Write the register address we want to read from
	d.out32.Call(uintptr(ecDataPort), uintptr(register))

	if err := d.waitOBF(); err != nil {
		return 0, fmt.Errorf("EC read failed waiting for data: %w", err)
	}

	// Read the actual data from the data port
	result, _, _ := d.inp32.Call(uintptr(ecDataPort))
	return byte(result), nil
}

// Write sends a value to a specific register in the EC.
func (d *EcDriver) Write(register int, value byte) error {
	d.mutex.Lock()
	defer d.mutex.Unlock()

	if err := d.waitIBF(); err != nil {
		return fmt.Errorf("EC write failed during pre-command wait: %w", err)
	}

	// Send write command (0x81) to the EC
	d.out32.Call(uintptr(ecCommandPort), uintptr(0x81))

	if err := d.waitIBF(); err != nil {
		return fmt.Errorf("EC write failed during address wait: %w", err)
	}

	// Write the register address we want to write to
	d.out32.Call(uintptr(ecDataPort), uintptr(register))

	if err := d.waitIBF(); err != nil {
		return fmt.Errorf("EC write failed during value wait: %w", err)
	}

	// Write the actual data to the data port
	d.out32.Call(uintptr(ecDataPort), uintptr(value))

	return nil
}

// waitIBF waits for the Input Buffer Full bit to clear (become 0).
// This indicates the EC is ready to accept a command or data.
func (d *EcDriver) waitIBF() error {
	for i := 0; i < 100; i++ {
		status, _, _ := d.inp32.Call(uintptr(ecCommandPort))
		if (status & (1 << statusIbf)) == 0 {
			return nil
		}
		time.Sleep(1 * time.Millisecond)
	}
	return fmt.Errorf("timeout waiting for EC input buffer to clear")
}

// waitOBF waits for the Output Buffer Full bit to set (become 1).
// This indicates the EC has data ready for us to read.
func (d *EcDriver) waitOBF() error {
	for i := 0; i < 100; i++ {
		status, _, _ := d.inp32.Call(uintptr(ecCommandPort))
		if (status & (1 << statusObf)) != 0 {
			return nil
		}
		time.Sleep(1 * time.Millisecond)
	}
	return fmt.Errorf("timeout waiting for EC output buffer to fill")
}
