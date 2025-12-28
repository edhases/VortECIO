package models

// UserProfile represents a user-defined fan curve for a specific fan
// on a specific notebook model. It only stores the thresholds, as other
// hardware-specific values (registers, min/max speed) are read from the base XML.
type UserProfile struct {
	TemperatureThresholds []TemperatureThreshold `json:"temperatureThresholds"`
}

// UserProfiles is a map where the key is the notebook model name (from XML)
// and the value is another map, where the key is the fan index (as a string)
// and the value is the user-defined profile for that fan.
// E.g., { "HP Pavilion 15": { "0": UserProfile{...}, "1": UserProfile{...} } }
type UserProfiles map[string]map[string]UserProfile
