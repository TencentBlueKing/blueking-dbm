package config

import "golang.org/x/exp/slices"

// MonitorItem TODO
type MonitorItem struct {
	Name        string   `yaml:"name" validate:"required"`
	Enable      *bool    `yaml:"enable" validate:"required"`
	Schedule    *string  `yaml:"schedule"`
	MachineType []string `yaml:"machine_type"`
	Role        []string `yaml:"role"`
}

// IsEnable TODO
func (c *MonitorItem) IsEnable() bool {
	return c.Enable != nil && *c.Enable
}

// IsMatchMachineType TODO
func (c *MonitorItem) IsMatchMachineType() bool {
	return slices.Index(c.MachineType, MonitorConfig.MachineType) >= 0
}

// IsMatchRole TODO
func (c *MonitorItem) IsMatchRole() bool {
	if MonitorConfig.Role == nil {
		return true
	}

	if c.Role == nil || len(c.Role) < 1 {
		return true
	}

	if *MonitorConfig.Role == "repeater" {
		return true
	}

	return slices.Index(c.Role, *MonitorConfig.Role) >= 0
}
