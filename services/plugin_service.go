//go:build windows

package services

import (
	"encoding/json"
	"io/ioutil"
	"log"
	"os"
	"path/filepath"
)

// PluginManifest describes the metadata of a plugin.
type PluginManifest struct {
	ID          string `json:"id"`
	Name        string `json:"name"`
	Version     string `json:"version"`
	Type        string `json:"type"`
	Executable  string `json:"executable"`
	Description string `json:"description"`
}

// Plugin represents a discovered and registered plugin.
type Plugin struct {
	Manifest PluginManifest
	BasePath string
}

// PluginService manages the discovery and registration of plugins.
type PluginService struct {
	plugins         map[string]*Plugin
	sensorProviders map[string]*Plugin
}

// NewPluginService creates a new service and discovers plugins.
func NewPluginService(pluginDir string) *PluginService {
	service := &PluginService{
		plugins:         make(map[string]*Plugin),
		sensorProviders: make(map[string]*Plugin),
	}
	service.discoverPlugins(pluginDir)
	return service
}

// GetSensorProviders returns all registered plugins that can provide sensor data.
func (s *PluginService) GetSensorProviders() []*Plugin {
	providers := make([]*Plugin, 0, len(s.sensorProviders))
	for _, p := range s.sensorProviders {
		providers = append(providers, p)
	}
	return providers
}

// GetPluginByID returns a specific plugin by its ID.
func (s *PluginService) GetPluginByID(id string) (*Plugin, bool) {
	p, ok := s.plugins[id]
	return p, ok
}

// discoverPlugins scans the plugin directory for valid plugins.
func (s *PluginService) discoverPlugins(pluginDir string) {
	log.Println("Discovering plugins in:", pluginDir)
	files, err := ioutil.ReadDir(pluginDir)
	if err != nil {
		log.Printf("Warning: Could not read plugin directory %s: %v", pluginDir, err)
		return
	}

	for _, f := range files {
		if !f.IsDir() {
			continue
		}
		pluginPath := filepath.Join(pluginDir, f.Name())
		manifestPath := filepath.Join(pluginPath, "plugin.json")

		if _, err := os.Stat(manifestPath); os.IsNotExist(err) {
			log.Printf("Plugin directory %s is missing a manifest.", pluginPath)
			continue
		}

		manifestData, err := ioutil.ReadFile(manifestPath)
		if err != nil {
			log.Printf("Warning: Could not read manifest for plugin %s: %v", f.Name(), err)
			continue
		}

		var manifest PluginManifest
		if err := json.Unmarshal(manifestData, &manifest); err != nil {
			log.Printf("Warning: Could not parse manifest for plugin %s: %v", f.Name(), err)
			continue
		}

		plugin := &Plugin{
			Manifest: manifest,
			BasePath: pluginPath,
		}

		s.plugins[manifest.ID] = plugin
		log.Printf("Discovered plugin: %s (v%s)", manifest.Name, manifest.Version)

		// Register by type
		if manifest.Type == "sensor_provider" {
			s.sensorProviders[manifest.ID] = plugin
			log.Printf("-> Registered '%s' as a sensor provider.", manifest.Name)
		}
	}
}
