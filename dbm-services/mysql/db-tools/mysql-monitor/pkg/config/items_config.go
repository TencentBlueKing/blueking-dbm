package config

import "slices"

// MonitorItem 监控项
type MonitorItem struct {
	Name        string   `json:"name" yaml:"name" validate:"required"`
	Enable      *bool    `json:"enable" yaml:"enable" validate:"required"`
	Schedule    *string  `json:"schedule" yaml:"schedule"`
	MachineType []string `json:"machine_type" yaml:"machine_type"`
	Role        []string `json:"role" yaml:"role"`
	// Options custom options for this item
	Options map[string]interface{} `json:"options" yaml:"options"`
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

// HasOptions 是否存在自定义选项
func (c *MonitorItem) HasOptions() bool {
	if c.Options == nil || len(c.Options) == 0 {
		return false
	}
	return true
}
