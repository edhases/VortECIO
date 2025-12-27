//go:build windows

package sensors

import (
	"fmt"
	"math"
	"strings"

	"github.com/yusufpapurcu/wmi"
)

// ThermalZoneInfo зберігає розширену інформацію про зону
type ThermalZoneInfo struct {
	InstanceName       string
	CurrentTemperature uint32
}

// SystemTemps містить знайдені температури
type SystemTemps struct {
	MaxCpuTemp float64
	GpuTemp    float64 // 0.0, якщо не знайдено
}

// GetSystemTemperatures отримує всі зони та намагається визначити CPU і GPU
func GetSystemTemperatures() (SystemTemps, error) {
	var dst []ThermalZoneInfo
	// Отримуємо також InstanceName, щоб розрізняти зони
	query := "SELECT CurrentTemperature, InstanceName FROM MSAcpi_ThermalZoneTemperature"

	err := wmi.QueryNamespace(query, &dst, `root\wmi`)
	if err != nil {
		return SystemTemps{}, fmt.Errorf("WMI query failed: %w", err)
	}

	if len(dst) == 0 {
		return SystemTemps{}, fmt.Errorf("no thermal zones found via WMI")
	}

	temps := SystemTemps{}
	maxTempDeciKelvin := uint32(0)

	for _, zone := range dst {
		// Шукаємо GPU за ключовими словами в назві
		name := strings.ToLower(zone.InstanceName)
		isGpu := strings.Contains(name, "gpu") || strings.Contains(name, "vga") || strings.Contains(name, "video") || strings.Contains(name, "3d")

		if isGpu {
			// Якщо знайшли схожу на GPU зону
			if zone.CurrentTemperature > 0 {
				temps.GpuTemp = deciKelvinToCelsius(zone.CurrentTemperature)
			}
		} else {
			// Всі інші вважаємо системними/CPU і шукаємо максимум
			if zone.CurrentTemperature > maxTempDeciKelvin {
				maxTempDeciKelvin = zone.CurrentTemperature
			}
		}
	}

	temps.MaxCpuTemp = deciKelvinToCelsius(maxTempDeciKelvin)
	return temps, nil
}

func deciKelvinToCelsius(dk uint32) float64 {
	celsius := (float64(dk) - 2732.0) / 10.0
	return math.Round(celsius*10) / 10
}
