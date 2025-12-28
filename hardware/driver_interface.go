package hardware

// ECDriver defines the interface for interacting with the Embedded Controller.
// This allows for abstracting the hardware-specific implementation (like inpoutx64.dll)
// from the core application logic, making it easier to test and maintain.
type ECDriver interface {
	// Read queries a single byte from a specific register in the EC.
	Read(register int) (byte, error)

	// Write sends a single byte to a specific register in the EC.
	Write(register int, value byte) error

	// ReadWord queries a 16-bit value from two consecutive EC registers.
	// This is typically used for reading values that exceed 255, such as fan RPM.
	ReadWord(register int) (int, error)

	// Close releases any resources held by the driver (e.g., loaded DLLs).
	// This method is not currently used by the EcDriver but is included for
	// interface completeness and future compatibility.
	Close()
}
