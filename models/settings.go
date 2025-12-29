package models

// Settings defines the structure for the application's configuration file (settings.json).
// It holds user preferences and the state of the application.
type Settings struct {
	Language                    string `json:"language"`
	AutoStart                   bool   `json:"autoStart"`
	LastConfigPath              string `json:"lastConfigPath"`
	CriticalTemp                int    `json:"criticalTemp"`
	SafetyAction                string `json:"safetyAction"`
	SensorProviderPluginID      string `json:"sensorProviderPluginID"`
	EnableCriticalTempRecovery  bool   `json:"enableCriticalTempRecovery"`
	CriticalTempRecoveryDelta   int    `json:"criticalTempRecoveryDelta"`
}
