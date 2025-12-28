package models

import "encoding/xml"

// Config represents the root of the NBFC XML configuration.
// It is the Go equivalent of the FanControlConfigV2 XML structure.
type Config struct {
	XMLName             xml.Name           `xml:"FanControlConfigV2"`
	ModelName           string             `xml:"NotebookModel"`
	Author              string             `xml:"Author"`
	EcPollInterval      int                `xml:"EcPollInterval"`
	ReadWriteWords      bool               `xml:"ReadWriteWords"`
	CriticalTemperature int                `xml:"CriticalTemperature"`
	FanConfigurations   []FanConfiguration `xml:"FanConfigurations>FanConfiguration"`
}

// FanConfiguration holds the settings for a single fan.
type FanConfiguration struct {
	ReadRegister          int                    `xml:"ReadRegister"`
	WriteRegister         int                    `xml:"WriteRegister"`
	RpmRegister           int                    `xml:"RpmRegister,omitempty"` // Optional: Register for reading fan RPM
	MinSpeedValue         int                    `xml:"MinSpeedValue"`
	MaxSpeedValue         int                    `xml:"MaxSpeedValue"`
	ResetRequired         bool                   `xml:"ResetRequired"`
	FanSpeedResetValue    int                    `xml:"FanSpeedResetValue"`
	FanDisplayName        string                 `xml:"FanDisplayName"`
	TemperatureThresholds []TemperatureThreshold `xml:"TemperatureThresholds>TemperatureThreshold"`
}

// TemperatureThreshold defines a single point in the fan curve,
// linking temperature ranges to a specific fan speed percentage.
type TemperatureThreshold struct {
	UpThreshold   int     `xml:"UpThreshold"`
	DownThreshold int     `xml:"DownThreshold"`
	FanSpeed      float64 `xml:"FanSpeed"`
}
