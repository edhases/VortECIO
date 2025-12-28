package utils

import (
	"VortECIO-Go/models"
	"encoding/xml"
	"fmt"
	"io"
	"os"
)

// LoadConfigFromXML loads and parses a specified NBFC-compatible XML configuration file.
// It takes a file path as input and returns a pointer to a Config struct or an error.
func LoadConfigFromXML(filePath string) (*models.Config, error) {
	// Open the XML file for reading.
	xmlFile, err := os.Open(filePath)
	if err != nil {
		return nil, fmt.Errorf("error opening config file '%s': %w", filePath, err)
	}
	defer xmlFile.Close()

	// Read the entire file content using the opened file handle.
	byteValue, err := io.ReadAll(xmlFile)
	if err != nil {
		return nil, fmt.Errorf("error reading config file '%s': %w", filePath, err)
	}

	var config models.Config
	// Unmarshal the XML data into the Config struct.
	if err := xml.Unmarshal(byteValue, &config); err != nil {
		return nil, fmt.Errorf("error parsing XML from '%s': %w", filePath, err)
	}

	return &config, nil
}
