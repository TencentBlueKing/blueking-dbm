package tools

import (
	"fmt"
	"path"
	"path/filepath"

	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
)

// ExternalTool 外部工具类型
type ExternalTool string

const (
	// ToolMysqlbinlog mysqlbinlog
	ToolMysqlbinlog ExternalTool = "mysqlbinlog"
	// ToolMload mload
	ToolMload ExternalTool = "mload"
	// ToolMysqlclient mysql
	ToolMysqlclient ExternalTool = "mysql"
	// ToolXLoad xload
	ToolXLoad ExternalTool = "xload"
	// ToolQPress qpress
	ToolQPress ExternalTool = "qpress"
	// ToolPv TODO
	ToolPv ExternalTool = "pv"
	// ToolMysqlbinlogRollback mysqlbinlog_rollback
	ToolMysqlbinlogRollback ExternalTool = "mysqlbinlog_rollback"
	// ToolMysqlbinlogRollback80 mysqlbinlog_rollback80
	ToolMysqlbinlogRollback80 ExternalTool = "mysqlbinlog_rollback80"
	// ToolMysqlTableChecksum mysql-table-checksum
	ToolMysqlTableChecksum ExternalTool = "mysql-table-checksum"
	// ToolPtTableChecksum pt-table-checksum
	ToolPtTableChecksum ExternalTool = "pt-table-checksum"
	// ToolPtTableSync pt-table-sync
	ToolPtTableSync ExternalTool = "pt-table-sync"
	// ToolDbbackupGo dbbackup
	ToolDbbackupGo ExternalTool = "dbbackup"
	// ToolRotatebinlog binlog 清理
	ToolRotatebinlog ExternalTool = "rotatebinlog"
	// ToolMySQLCrond crond
	ToolMySQLCrond ExternalTool = "mysql-crond"
	// ToolMySQLMonitor mysql monitor
	ToolMySQLMonitor ExternalTool = "mysql-monitor"
)

// defaultPath defaults path
var defaultPath = map[ExternalTool]string{
	ToolMload:                 "/home/mysql/dbbackup/MLOAD/MLOAD.pl",
	ToolXLoad:                 "/home/mysql/dbbackup/xtrabackup/xload.pl",
	ToolQPress:                "/home/mysql/dbbackup-go/bin/xtrabackup/qpress",
	ToolPv:                    "/home/mysql/dbbackup-go/bin/pv",
	ToolMysqlclient:           "/usr/local/mysql/bin/mysql",
	ToolMysqlbinlog:           "/usr/local/mysql/bin/mysqlbinlog",
	ToolMysqlbinlogRollback:   filepath.Join(cst.DBAToolkitPath, string(ToolMysqlbinlogRollback)),
	ToolMysqlbinlogRollback80: filepath.Join(cst.DBAToolkitPath, "mysqlbinlog_rollback_80"),
	ToolMysqlTableChecksum:    path.Join(cst.ChecksumInstallPath, string(ToolMysqlTableChecksum)),
	ToolPtTableChecksum:       path.Join(cst.ChecksumInstallPath, string(ToolPtTableChecksum)),
	ToolPtTableSync:           path.Join(cst.ChecksumInstallPath, string(ToolPtTableSync)),
	ToolDbbackupGo:            path.Join(cst.DbbackupGoInstallPath, string(ToolDbbackupGo)),
	ToolMySQLCrond:            path.Join(cst.MySQLCrondInstallPath, string(ToolMySQLCrond)),
	ToolMySQLMonitor:          path.Join(cst.MySQLMonitorInstallPath, string(ToolMySQLMonitor)),
}

// ToolPath 基本结构
type ToolPath struct {
	Tools map[ExternalTool]string `json:"tools"`
}

// ToolSet 外部工具
type ToolSet struct {
	// 外部指定工具路径
	Tools map[ExternalTool]string `json:"tools"`
	maps  map[ExternalTool]string
}

// NewToolSetWithDefault 加载全部默认工具
func NewToolSetWithDefault() (*ToolSet, error) {
	res := &ToolSet{maps: defaultPath}
	err := res.validate()
	if err != nil {
		return nil, err
	}
	return res, nil
}

// NewToolsSetWithDefaultNoValidate 无验证
func NewToolsSetWithDefaultNoValidate() *ToolSet {
	return &ToolSet{maps: defaultPath}
}

// NewToolSetWithPick 按需加载
func NewToolSetWithPick(tools ...ExternalTool) (*ToolSet, error) {
	maps := make(map[ExternalTool]string)
	for _, tool := range tools {
		if p, ok := defaultPath[tool]; ok {
			maps[tool] = p
		} else {
			err := fmt.Errorf("%s not registered", tool)
			return nil, err
		}
	}
	res := &ToolSet{maps: maps}
	if err := res.validate(); err != nil {
		return nil, err
	}
	return res, nil
}

// NewToolSetWithPickNoValidate 无验证
func NewToolSetWithPickNoValidate(tools ...ExternalTool) *ToolSet {
	maps := make(map[ExternalTool]string)
	for _, tool := range tools {
		if p, ok := defaultPath[tool]; ok {
			maps[tool] = p
		} else {
			maps[tool] = ""
		}
	}
	return &ToolSet{maps: maps}
}

// Merge merge tools to left ToolSet
func (s *ToolSet) Merge(tools *ToolSet) error {
	s.maps = s.Tools
	if s.maps == nil {
		s.maps = make(map[ExternalTool]string)
	}
	if err := s.validate(); err != nil {
		return err
	}
	for toolName, toolPath := range tools.maps {
		if _, ok := s.maps[toolName]; !ok {
			s.maps[toolName] = toolPath
		}
	}
	return nil
}

// Set modify a tool path
// 没有校验 toolName 和 toolPath
func (s *ToolSet) Set(toolName ExternalTool, toolPath string) error {
	if s.maps == nil {
		s.maps = make(map[ExternalTool]string)
	}
	s.maps[toolName] = toolPath
	return nil
}
