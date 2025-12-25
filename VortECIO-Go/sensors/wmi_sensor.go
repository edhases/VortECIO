package sensors

import (
	"fmt"
	"math"

	"github.com/yusufpapurcu/wmi"
)

// ThermalZoneTemperature represents the structure of the data returned by the
// MSAcpi_ThermalZoneTemperature WMI class.
type ThermalZoneTemperature struct {
	CurrentTemperature uint32
}

// GetMaxSystemTemperature queries WMI for all available thermal zones, finds the
// highest temperature, and returns it in degrees Celsius.
func GetMaxSystemTemperature() (float64, error) {
	var dst []ThermalZoneTemperature
	// The query to get temperature values.
	query := "SELECT CurrentTemperature FROM MSAcpi_ThermalZoneTemperature"

	// FIX: Explicitly specify the namespace "root\wmi"
	// Without this, it defaults to root\cimv2 where this class doesn't exist.
	err := wmi.QueryNamespace(query, &dst, "root\\wmi")
	if err != nil {
		return 0, fmt.Errorf("WMI query failed: %w. Ensure you are running as Administrator", err)
	}

	if len(dst) == 0 {
		return 0, fmt.Errorf("no thermal zones found via WMI")
	}

	maxTempDeciKelvin := uint32(0)
	for _, zone := range dst {
		// Sometimes WMI returns invalid 0 or super high values, basic filtering can be added here if needed
		if zone.CurrentTemperature > maxTempDeciKelvin {
			maxTempDeciKelvin = zone.CurrentTemperature
		}
	}

	// WMI returns temperature in deci-Kelvin (tenths of a Kelvin).
	// Formula: (DeciKelvin / 10) - 273.15
	// Simplified approximation: (dK - 2732) / 10
	celsius := (float64(maxTempDeciKelvin) - 2732.0) / 10.0

	// Round to one decimal place for cleaner display
	celsius = math.Round(celsius*10) / 10

	// Safety check: if calculation results in nonsense (e.g. < 0), return 0 error
	if celsius < 0 {
		return 0, nil
	}

	return celsius, nil
}
