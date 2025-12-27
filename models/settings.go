package models

// Settings struct for storing application settings.
type Settings struct {
	LastConfigPath string `json:"last_config_path"`
	Language       string `json:"language"`
	AutoStart      bool   `json:"auto_start"`
	CriticalTemp   int    `json:"critical_temp"`
	SafetyAction   string `json:"safety_action"` // "bios_control" or "force_full_speed"
}
