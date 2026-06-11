/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package config

import (
	"errors"
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"

	"gopkg.in/yaml.v3"
)

// APIConfig represents API configuration
type APIConfig struct {
	Endpoint  string        `yaml:"endpoint"`
	BkCloudID int           `yaml:"bk_cloud_id"`
	Timeout   time.Duration `yaml:"timeout"`
	Token     string        `yaml:"token"`
}

// Config represents the configuration of the black-white list manager.
type Config struct {
	API APIConfig `yaml:"api"`
}

// GlobalConfig represents the global configuration instance
var GlobalConfig *Config

// SetGlobalConfig sets the global configuration
func SetGlobalConfig(config *Config) {
	GlobalConfig = config
}

// LoadConfig loads configuration from YAML file with environment variable and command line override support
func LoadConfig(configFile string, cmdFlags map[string]interface{}) (*Config, error) {
	config := &Config{}

	// Load from YAML file if it exists
	if _, err := os.Stat(configFile); err == nil {
		data, err := os.ReadFile(configFile)
		if err != nil {
			return nil, fmt.Errorf(errReadConfigFormat, err)
		}

		err = yaml.Unmarshal(data, config)
		if err != nil {
			return nil, fmt.Errorf(errParseConfigFormat, err)
		}
	}

	// Apply environment variable overrides
	applyEnvOverrides(config)

	// Apply command line flag overrides (highest priority)
	applyCmdFlagOverrides(config, cmdFlags)

	// Validate required fields
	if err := validateConfig(config); err != nil {
		return nil, err
	}

	return config, nil
}

// applyEnvOverrides applies environment variable overrides to config
func applyEnvOverrides(config *Config) {
	// API Endpoint
	if envEndpoint := os.Getenv(EnvAPIEndpoint); envEndpoint != "" {
		config.API.Endpoint = envEndpoint
	}

	// API bk_cloud_id
	if envBkCloudID := os.Getenv(EnvAPIBkCloudID); envBkCloudID != "" {
		if bkCloudID, err := strconv.Atoi(envBkCloudID); err == nil {
			config.API.BkCloudID = bkCloudID
		}
	}

	// API Timeout
	if envTimeout := os.Getenv(EnvAPITimeout); envTimeout != "" {
		if timeout, err := time.ParseDuration(envTimeout); err == nil {
			config.API.Timeout = timeout
		}
	}

	// API Token
	if envToken := os.Getenv(EnvAPIToken); envToken != "" {
		config.API.Token = envToken
	}
}

// applyCmdFlagOverrides applies command line flag overrides to config
func applyCmdFlagOverrides(config *Config, cmdFlags map[string]interface{}) {
	for key, value := range cmdFlags {
		switch key {
		case CmdFlagAPIEndpoint:
			if endpoint, ok := value.(string); ok && endpoint != "" {
				config.API.Endpoint = endpoint
			}

		case CmdFlagAPIBkCloudID:
			if bkCloudID, ok := value.(int); ok && bkCloudID >= 0 {
				config.API.BkCloudID = bkCloudID
			}

		case CmdFlagAPITimeout:
			if timeoutStr, ok := value.(string); ok && timeoutStr != "" {
				if timeout, err := time.ParseDuration(timeoutStr); err == nil {
					config.API.Timeout = timeout
				}
			}

		case CmdFlagAPIToken:
			if token, ok := value.(string); ok && token != "" {
				config.API.Token = token
			}
		}
	}
}

// validateConfig validates the configuration
func validateConfig(config *Config) error {
	if config.API.Endpoint == "" {
		return errors.New(errAPIEndpointRequired)
	}

	if config.API.BkCloudID < 0 {
		return errors.New(errAPIBkCloudIDInvalid)
	}

	if config.API.Timeout <= 0 {
		config.API.Timeout = defaultAPITimeout
	}

	if config.API.Token == "" {
		return errors.New(errAPITokenRequired)
	}

	return nil
}

// GetAPIURL returns the full API URL
func (c *Config) GetAPIURL() string {
	return c.API.Endpoint
}

// GetDefaultConfig returns a default configuration
func GetDefaultConfig() *Config {
	return &Config{
		API: APIConfig{
			Endpoint:  defaultAPIEndpoint,
			BkCloudID: defaultAPIBkCloudID,
			Timeout:   defaultAPITimeout,
			Token:     defaultAPIToken,
		},
	}
}

// CreateDefaultConfigFile creates a default configuration file
func CreateDefaultConfigFile(filePath string) error {
	defaultConfig := GetDefaultConfig()

	data, err := yaml.Marshal(defaultConfig)
	if err != nil {
		return fmt.Errorf(errMarshalConfigFormat, err)
	}

	// Ensure directory exists
	dir := filePath[:strings.LastIndex(filePath, pathSeparator)]
	if err := os.MkdirAll(dir, dirPerm); err != nil {
		return fmt.Errorf(errCreateConfigDirFormat, err)
	}

	if err := os.WriteFile(filePath, data, filePerm); err != nil {
		return fmt.Errorf(errWriteConfigFileFormat, err)
	}

	return nil
}
