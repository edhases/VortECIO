//go:build windows

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
	// The query to get temperature values. Note the namespace `root\wmi`.
	query := "SELECT CurrentTemperature FROM MSAcpi_ThermalZoneTemperature"

	err := wmi.QueryNamespace(query, &dst, "root\\wmi")
	if err != nil {
		return 0, fmt.Errorf("WMI query failed: %w. This may happen on systems without WMI support or if run without admin privileges", err)
	}

	if len(dst) == 0 {
		return 0, fmt.Errorf("no thermal zones found via WMI")
	}

	maxTempDeciKelvin := uint32(0)
	for _, zone := range dst {
		if zone.CurrentTemperature > maxTempDeciKelvin {
			maxTempDeciKelvin = zone.CurrentTemperature
		}
	}

	// WMI returns temperature in deci-Kelvin (tenths of a Kelvin).
	// Formula to convert to Celsius: Celsius = (dK - 2732) / 10.0
	celsius := (float64(maxTempDeciKelvin) - 2732.0) / 10.0

	// Round to one decimal place for cleaner display
	celsius = math.Round(celsius*10) / 10

	return celsius, nil
}
