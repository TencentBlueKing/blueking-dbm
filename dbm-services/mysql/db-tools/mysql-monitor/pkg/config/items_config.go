package config

import "golang.org/x/exp/slices"

// MonitorItem 监控项
type MonitorItem struct {
	Name        string   `yaml:"name" validate:"required"`
	Enable      *bool    `yaml:"enable" validate:"required"`
	Schedule    *string  `yaml:"schedule"`
	MachineType []string `yaml:"machine_type"`
	Role        []string `yaml:"role"`
}


// IsEnable 监控项启用
func (c *MonitorItem) IsEnable() bool {
	return c.Enable != nil && *c.Enable
}

// IsMatchMachineType 机器类型匹配
func (c *MonitorItem) IsMatchMachineType() bool {
	return slices.Index(c.MachineType, MonitorConfig.MachineType) >= 0
}

// IsMatchRole 实例角色匹配
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
