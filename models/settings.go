package models

// Settings holds the user-configurable application settings.
// These are stored in settings.json.
type Settings struct {
	Language                  string `json:"language"`
	AutoStart                 bool   `json:"autoStart"`
	LastConfigPath            string `json:"lastConfigPath"`
	CriticalTemp              int    `json:"criticalTemp"`
	SafetyAction              string `json:"safetyAction"`
	EnableCriticalTempRecovery bool   `json:"enableCriticalTempRecovery"`
	CriticalTempRecoveryDelta int    `json:"criticalTempRecoveryDelta"`
}
