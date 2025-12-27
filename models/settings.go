package models

// Settings struct for storing application settings.
type Settings struct {
	LastConfigPath string `json:"lastConfigPath"`
	Language       string `json:"language"`
	AutoStart      bool   `json:"autoStart"`
	CriticalTemp   int    `json:"criticalTemp"`
	SafetyAction   string `json:"safetyAction"` // "bios_control" or "force_full_speed"
}
