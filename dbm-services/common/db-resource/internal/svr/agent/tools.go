/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package agent

import (
	"context"
	"crypto/sha256"
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"sort"
	"strings"
	"sync"
	"time"

	"gorm.io/gorm"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/bk"
)

// ResourceTools 资源查询工具集
type ResourceTools struct {
	db *gorm.DB
}

// 资源类型推测相关常量
const (
	// 支持的资源类型
	ResourceTypeMySQL        = "mysql"
	ResourceTypeTenDBCluster = "tendbcluster"

	// 性能优化相关常量
	DefaultQueryTimeout   = 30 * time.Second // 默认查询超时时间
	MaxConcurrentQueries  = 10               // 最大并发查询数
	QueryResultCacheSize  = 1000             // 查询结果缓存大小
	QueryResultCacheTTL   = 5 * time.Minute  // 查询结果缓存TTL
	MaxSubZoneResults     = 50               // 最大园区结果数
	MaxDeviceClassResults = 30               // 最大机型规格结果数
	QueryBatchSize        = 1000             // 查询批次大小
)

// 资源类型映射关系（遗留兜底）。mysql 与 tendbcluster 已合并为库内同一池，不再在此处配置互换。
var resourceTypeMapping = map[string]string{}

// 支持推测的资源类型集合 - 可配置
var supportedResourceTypes = map[string]bool{
	ResourceTypeMySQL:        true,
	ResourceTypeTenDBCluster: true,
}

// ResourceTypeMappingConfig 资源类型映射配置
type ResourceTypeMappingConfig struct {
	Mappings           map[string][]string          `json:"mappings"`            // 一对多映射关系
	CompatibilityRules map[string]CompatibilityRule `json:"compatibility_rules"` // 兼容性规则
	MigrationCosts     map[string]map[string]string `json:"migration_costs"`     // 迁移成本矩阵
	Priorities         map[string]int               `json:"priorities"`          // 优先级配置
	Enabled            bool                         `json:"enabled"`             // 是否启用扩展映射
}

// CompatibilityRule 兼容性规则
type CompatibilityRule struct {
	Level       string   `json:"level"`       // 兼容性级别：high/medium/low/none
	Conditions  []string `json:"conditions"`  // 兼容性条件
	Limitations []string `json:"limitations"` // 限制说明
}

// ResourceTypeRegistry 资源类型注册表（可扩展）
type ResourceTypeRegistry struct {
	mu              sync.RWMutex
	mappingConfig   *ResourceTypeMappingConfig
	customMappings  map[string][]string
	validationRules map[string]ValidationRule
	transformRules  map[string]TransformRule
}

// ValidationRule 验证规则
type ValidationRule struct {
	RequiredFields []string                          `json:"required_fields"`
	Validators     map[string]func(interface{}) bool `json:"-"` // 自定义验证函数
}

// TransformRule 转换规则
type TransformRule struct {
	FieldMappings map[string]string                        `json:"field_mappings"` // 字段映射
	Transformers  map[string]func(interface{}) interface{} `json:"-"`              // 自定义转换函数
}

// 全局资源类型注册表
var globalResourceTypeRegistry = &ResourceTypeRegistry{
	mappingConfig:   getDefaultMappingConfig(),
	customMappings:  make(map[string][]string),
	validationRules: make(map[string]ValidationRule),
	transformRules:  make(map[string]TransformRule),
}

// NewResourceTools 创建资源工具集
func NewResourceTools(db *gorm.DB) *ResourceTools {
	return &ResourceTools{db: db}
}

// getBkCloudID 从参数中提取 bk_cloud_id，支持 JSON 解析后的 float64 和 int
func getBkCloudID(args map[string]interface{}) int {
	v := args["bk_cloud_id"]
	if v == nil {
		return 0
	}
	switch val := v.(type) {
	case int:
		return val
	case int64:
		return int(val)
	case float64:
		return int(val)
	default:
		return 0
	}
}

// getIntentionBizID 从参数中提取 intention_biz_id，对齐真实匹配链 SearchContext.IntentionBkBizId。
// 支持 JSON 解析后的 float64/int/int64。
// 备注：单据流程中 IntentionBkBizId 来自 RequestInputParam.ForbizId（json: for_biz_id）。
// 兼容上游也可能直接传 for_biz_id 的情况。
func getIntentionBizID(args map[string]interface{}) int {
	keys := []string{"intention_biz_id", "for_biz_id"}
	for _, k := range keys {
		v, ok := args[k]
		if !ok || v == nil {
			continue
		}
		switch val := v.(type) {
		case int:
			return val
		case int64:
			return int(val)
		case float64:
			return int(val)
		}
	}
	return 0
}

// getOsType 从参数中提取 os_type，缺省返回 model.LinuxOs，对齐 SearchContext.MatchOsType 默认 Linux 行为。
func getOsType(args map[string]interface{}) string {
	if s, ok := args["os_type"].(string); ok && s != "" {
		return s
	}
	return model.LinuxOs
}

// getStringSlice 从参数里提取 []string（用于 os_names/labels 等）。
func getStringSlice(args map[string]interface{}, key string) []string {
	raw, ok := args[key].([]interface{})
	if !ok {
		return nil
	}
	out := make([]string, 0, len(raw))
	for _, x := range raw {
		if s, ok := x.(string); ok && s != "" {
			out = append(out, s)
		}
	}
	return out
}

// getBool 提取 bool（用于 exclude_os_name 等）。
func getBool(args map[string]interface{}, key string) bool {
	if v, ok := args[key].(bool); ok {
		return v
	}
	return false
}

// applyBizAndOsFilters 对齐 apply.SearchContext 真实选机链的业务/操作系统过滤，避免 AI 工具高估候选库存。
//   - dedicated_biz：未指定 IntentionBkBizId 时只能匹配公共池（dedicated_biz=0）；指定时若同时带 labels 则只能匹配该业务专属
//     （dedicated_biz=biz），否则匹配公共池或该业务专属（dedicated_biz IN (0, biz)）。
//   - os_type：未传时默认 Linux。
//   - os_names：传入则按 in/not in 过滤（与 ObjectDetail.ExcludeOsName 行为对齐）。
//
// 与 apply.MatchIntentionBkBiz/MatchOsType/MatchOsName 行为完全一致，方便分析工具的 SQL 与真实匹配链对齐。
func applyBizAndOsFilters(db *gorm.DB, args map[string]interface{}) *gorm.DB {
	bizID := getIntentionBizID(args)
	labels := getStringSlice(args, "labels")
	if bizID <= 0 {
		db = db.Where("dedicated_biz = ?", 0)
	} else if len(labels) > 0 {
		db = db.Where("dedicated_biz = ?", bizID)
	} else {
		db = db.Where("dedicated_biz IN (?)", []int{0, bizID})
	}

	db = db.Where("os_type = ?", getOsType(args))

	osNames := getStringSlice(args, "os_names")
	if len(osNames) > 0 {
		if getBool(args, "exclude_os_name") {
			db = db.Where("os_name NOT IN (?)", osNames)
		} else {
			db = db.Where("os_name IN (?)", osNames)
		}
	}
	return db
}

// bizAndOsParamDefs 返回与 apply.MatchIntentionBkBiz/MatchOsType/MatchOsName 对齐的 schema 参数定义。
// 任何对候选库存做评估的工具都应包含这组参数，使分析结果与真实匹配链一致。
func bizAndOsParamDefs() map[string]interface{} {
	return map[string]interface{}{
		"intention_biz_id": map[string]interface{}{
			"type": "integer",
			"description": "申请单据归属业务ID（来自 RequestInputParam.for_biz_id）。" +
				"未指定时只能匹配 dedicated_biz=0 的公共池；指定时匹配 dedicated_biz IN (0, biz)，若同时带 labels 则仅匹配该业务专属池。",
		},
		"for_biz_id": map[string]interface{}{
			"type":        "integer",
			"description": "等价于 intention_biz_id 的别名，兼容直接传单据原始字段的场景。",
		},
		"os_type": map[string]interface{}{
			"type":        "string",
			"description": "操作系统类型（Linux/Windows）。未传则默认 Linux，与真实匹配链 MatchOsType 行为一致。",
		},
		"os_names": map[string]interface{}{
			"type":        "array",
			"items":       map[string]interface{}{"type": "string"},
			"description": "os_name 限制列表，配合 exclude_os_name 决定 in/not in。",
		},
		"exclude_os_name": map[string]interface{}{
			"type":        "boolean",
			"description": "是否将 os_names 视为黑名单（true=NOT IN，false=IN）。",
		},
	}
}

// getSQLFromQuery 从 GORM 查询中获取 SQL 语句（用于调试）
func (t *ResourceTools) getSQLFromQuery(query *gorm.DB) string {
	// 使用 DryRun 模式获取 SQL
	dryRunQuery := query.Session(&gorm.Session{DryRun: true})
	var count int64
	stmt := dryRunQuery.Count(&count).Statement
	if stmt.SQL.String() == "" {
		stmt.Build("SELECT COUNT(*)")
	}
	sql := stmt.SQL.String()
	// 替换参数占位符为实际值（简化版，仅用于调试）
	if len(stmt.Vars) > 0 {
		for _, v := range stmt.Vars {
			var valStr string
			switch v := v.(type) {
			case string:
				valStr = fmt.Sprintf("'%s'", v)
			case []string:
				valStr = fmt.Sprintf("('%s')", strings.Join(v, "','"))
			default:
				valStr = fmt.Sprintf("%v", v)
			}
			sql = strings.Replace(sql, "?", valStr, 1)
		}
	}
	return sql
}

// ========== 园区显示格式化辅助函数 ==========

// formatSubZoneDisplay converts sub_zone_id to a more readable format
// Output format: "城市-园区名(ID)" e.g., "深圳-光明(268)"
// If city or subZone is empty, falls back to available info or just ID
func formatSubZoneDisplay(city, subZone, subZoneID string) string {
	if subZoneID == "" {
		return "UNKNOWN"
	}
	if city != "" && subZone != "" {
		return fmt.Sprintf("%s-%s(%s)", city, subZone, subZoneID)
	}
	if subZone != "" {
		return fmt.Sprintf("%s(%s)", subZone, subZoneID)
	}
	if city != "" {
		return fmt.Sprintf("%s(%s)", city, subZoneID)
	}
	// Fallback: try to get name from SubzoneIdMap
	if name, ok := model.SubzoneIdMap[subZoneID]; ok {
		return fmt.Sprintf("%s(%s)", name, subZoneID)
	}
	return subZoneID
}

// ========== 公共参数定义辅助函数 ==========

// DiskSpec represents a disk specification for multi-disk condition queries.
// storage_device structure example:
//
//	{
//	  "/data": {"size": 100, "disk_id": "disk-xxx", "disk_type": "CLOUD_SSD", "file_type": "ext4"},
//	  "/data1": {"size": 200, "disk_id": "disk-yyy", "disk_type": "HDD", "file_type": "xfs"}
//	}
type DiskSpec struct {
	MountPoint string `json:"mount_point"` // Mount point (e.g., "/data", "/data1")
	DiskType   string `json:"disk_type"`   // Disk type (SSD/HDD/CLOUD_SSD/CLOUD_PREMIUM etc.)
	MinSize    int    `json:"min_size"`    // Minimum disk size in GB
	MaxSize    int    `json:"max_size"`    // Maximum disk size in GB (0 means only check min_size)
}

// diskParamDefs returns common disk-related parameter definitions for tool schemas (single disk, backward compatible).
func diskParamDefs() map[string]interface{} {
	return map[string]interface{}{
		"disk_mount_point": map[string]interface{}{
			"type":        "string",
			"description": "磁盘挂载点(如'/data')，用于查询storage_device中对应挂载点的磁盘信息（单磁盘查询）",
		},
		"disk_type": map[string]interface{}{
			"type":        "string",
			"description": "磁盘类型(SSD/HDD/CLOUD_SSD/CLOUD_PREMIUM等)",
		},
		"disk_min_size": map[string]interface{}{
			"type":        "integer",
			"description": "磁盘最小大小(GB)",
		},
		"disk_max_size": map[string]interface{}{
			"type":        "integer",
			"description": "磁盘最大大小(GB)，若>0则使用范围匹配[min,max]",
		},
	}
}

// diskSpecParamDefs returns multi-disk specification parameter definitions for tool schemas.
// This supports querying multiple disks simultaneously (e.g., /data, /data1, /data2).
func diskSpecParamDefs() map[string]interface{} {
	return map[string]interface{}{
		"disk_specs": map[string]interface{}{
			"type": "array",
			"items": map[string]interface{}{
				"type": "object",
				"properties": map[string]interface{}{
					"mount_point": map[string]interface{}{
						"type":        "string",
						"description": "挂载点(如'/data', '/data1')",
					},
					"disk_type": map[string]interface{}{
						"type":        "string",
						"description": "磁盘类型(SSD/HDD/CLOUD_SSD/CLOUD_PREMIUM等)",
					},
					"min_size": map[string]interface{}{
						"type":        "integer",
						"description": "最小磁盘大小(GB)",
					},
					"max_size": map[string]interface{}{
						"type":        "integer",
						"description": "最大磁盘大小(GB)，若>0则使用范围匹配[min,max]",
					},
				},
				"required": []string{"mount_point"},
			},
			"description": "多磁盘规格数组，支持同时指定多个挂载点的磁盘条件（如同时检查/data需要100GB SSD，/data1需要200GB HDD）",
		},
	}
}

// parseDiskSpecs parses disk specifications from tool arguments.
// It supports both new format (disk_specs array) and old format (single disk parameters).
// If both formats are provided, the new format (disk_specs) takes precedence.
func parseDiskSpecs(args map[string]interface{}) []DiskSpec {
	var specs []DiskSpec

	// Try new format first (disk_specs array)
	if diskSpecsRaw, ok := args["disk_specs"]; ok && diskSpecsRaw != nil {
		switch v := diskSpecsRaw.(type) {
		case []interface{}:
			for _, item := range v {
				if itemMap, ok := item.(map[string]interface{}); ok {
					spec := DiskSpec{}
					if mp, ok := itemMap["mount_point"].(string); ok {
						spec.MountPoint = mp
					}
					if dt, ok := itemMap["disk_type"].(string); ok {
						spec.DiskType = dt
					}
					if minSize, ok := itemMap["min_size"].(float64); ok {
						spec.MinSize = int(minSize)
					}
					if maxSize, ok := itemMap["max_size"].(float64); ok {
						spec.MaxSize = int(maxSize)
					}
					if spec.MountPoint != "" {
						specs = append(specs, spec)
					}
				}
			}
		case []DiskSpec:
			specs = v
		}
		if len(specs) > 0 {
			return specs
		}
	}

	// Fall back to old format (single disk parameters)
	spec := DiskSpec{}
	if mp, ok := args["disk_mount_point"].(string); ok && mp != "" {
		spec.MountPoint = mp
	} else if mp, ok := args["mount_point"].(string); ok && mp != "" {
		// Also support mount_point for backward compatibility
		spec.MountPoint = mp
	}
	if dt, ok := args["disk_type"].(string); ok {
		spec.DiskType = dt
	}
	if minSize, ok := args["disk_min_size"].(float64); ok {
		spec.MinSize = int(minSize)
	} else if minSize, ok := args["min_size"].(float64); ok {
		spec.MinSize = int(minSize)
	}
	if maxSize, ok := args["disk_max_size"].(float64); ok {
		spec.MaxSize = int(maxSize)
	} else if maxSize, ok := args["max_size"].(float64); ok {
		spec.MaxSize = int(maxSize)
	}

	if spec.MountPoint != "" {
		specs = append(specs, spec)
	}
	return specs
}

// DiskMatchResult represents the result of matching a single disk spec.
type DiskMatchResult struct {
	MountPoint    string `json:"mount_point"`
	Exists        bool   `json:"exists"`         // Whether the mount point exists in any resource
	TypeMatched   bool   `json:"type_matched"`   // Whether the disk type matches
	SizeMatched   bool   `json:"size_matched"`   // Whether the disk size satisfies the requirement
	MatchedCount  int    `json:"matched_count"`  // Number of resources that match this disk spec
	RequiredType  string `json:"required_type"`  // The required disk type
	RequiredSize  int    `json:"required_size"`  // The required minimum disk size
	FailureReason string `json:"failure_reason"` // Reason for failure (if any)
}

// buildDiskConditions builds GORM query conditions for multiple disk specifications.
// It uses MySQL JSON functions (JSON_EXTRACT) to access nested data in the storage_device field.
// All disk conditions are combined using AND logic (all conditions must be satisfied).
//
// storage_device JSON structure example:
//
//	{
//	  "/data": {"size": 100, "disk_type": "CLOUD_SSD", ...},
//	  "/data1": {"size": 200, "disk_type": "HDD", ...}
//	}
func buildDiskConditions(query *gorm.DB, specs []DiskSpec) *gorm.DB {
	for _, spec := range specs {
		if spec.MountPoint == "" {
			continue
		}

		query = query.Where(
			fmt.Sprintf("JSON_EXTRACT(storage_device, '%s') IS NOT NULL", storageDeviceJSONPath(spec.MountPoint)),
		)
		if spec.DiskType != "" && spec.DiskType != "ALL" {
			query = query.Where(
				fmt.Sprintf("JSON_UNQUOTE(JSON_EXTRACT(storage_device, '%s')) = ?",
					storageDeviceJSONPath(spec.MountPoint, "disk_type")),
				spec.DiskType,
			)
		}
		if spec.MinSize > 0 {
			if spec.MaxSize > 0 {
				query = query.Where(
					fmt.Sprintf("CAST(JSON_EXTRACT(storage_device, '%s') AS SIGNED) BETWEEN ? AND ?",
						storageDeviceJSONPath(spec.MountPoint, "size")),
					spec.MinSize, spec.MaxSize,
				)
			} else {
				query = query.Where(
					fmt.Sprintf("CAST(JSON_EXTRACT(storage_device, '%s') AS SIGNED) >= ?",
						storageDeviceJSONPath(spec.MountPoint, "size")),
					spec.MinSize,
				)
			}
		} else if spec.MaxSize > 0 {
			query = query.Where(
				fmt.Sprintf("CAST(JSON_EXTRACT(storage_device, '%s') AS SIGNED) <= ?",
					storageDeviceJSONPath(spec.MountPoint, "size")),
				spec.MaxSize,
			)
		}
	}

	return query
}

// buildDiskConditionsSQL builds raw SQL conditions for multiple disk specifications.
// This is useful when you need to get the SQL string for debugging or direct execution.
func buildDiskConditionsSQL(specs []DiskSpec) (conditions []string, args []interface{}) {
	for _, spec := range specs {
		if spec.MountPoint == "" {
			continue
		}

		// Check if mount point exists
		conditions = append(conditions,
			fmt.Sprintf("JSON_EXTRACT(storage_device, '$.\"%s\"') IS NOT NULL", spec.MountPoint))
		// Check disk type if specified
		if spec.DiskType != "" && spec.DiskType != "ALL" {
			conditions = append(conditions,
				fmt.Sprintf("JSON_UNQUOTE(JSON_EXTRACT(storage_device, '$.\"%s\".disk_type')) = ?", spec.MountPoint))
			args = append(args, spec.DiskType)
		}

		// Check disk size
		if spec.MinSize > 0 {
			if spec.MaxSize > 0 {
				// Range match
				conditions = append(conditions,
					fmt.Sprintf("CAST(JSON_EXTRACT(storage_device, '$.\"%s\".size') AS SIGNED) BETWEEN ? AND ?",
						spec.MountPoint))
				args = append(args, spec.MinSize, spec.MaxSize)
			} else {
				// Only min size
				conditions = append(conditions,
					fmt.Sprintf("CAST(JSON_EXTRACT(storage_device, '$.\"%s\".size') AS SIGNED) >= ?", spec.MountPoint))
				args = append(args, spec.MinSize)
			}
		} else if spec.MaxSize > 0 {
			// Only max size
			conditions = append(conditions,
				fmt.Sprintf("CAST(JSON_EXTRACT(storage_device, '$.\"%s\".size') AS SIGNED) <= ?", spec.MountPoint))
			args = append(args, spec.MaxSize)
		}
	}

	return conditions, args
}

// analyzeDiskSpecMatches analyzes disk specifications against the database and returns detailed match results.
// It returns per-mount-point analysis including existence, type match, size match, and matched count.
func (t *ResourceTools) analyzeDiskSpecMatches(baseQuery *gorm.DB, specs []DiskSpec) []DiskMatchResult {
	results := make([]DiskMatchResult, 0, len(specs))

	for _, spec := range specs {
		result := DiskMatchResult{
			MountPoint:   spec.MountPoint,
			RequiredType: spec.DiskType,
			RequiredSize: spec.MinSize,
		}

		if spec.MountPoint == "" {
			result.FailureReason = "mount_point is empty"
			results = append(results, result)
			continue
		}

		// Check if mount point exists
		var existsCount int64
		existsQuery := baseQuery.Session(&gorm.Session{})
		existsQuery = existsQuery.Where(
			fmt.Sprintf("JSON_EXTRACT(storage_device, '$.\"%s\"') IS NOT NULL", spec.MountPoint),
		)
		existsQuery.Count(&existsCount)
		result.Exists = existsCount > 0

		if !result.Exists {
			result.FailureReason = fmt.Sprintf("mount point '%s' does not exist in any resource", spec.MountPoint)
			results = append(results, result)
			continue
		}

		// Check disk type match
		typeQuery := baseQuery.Session(&gorm.Session{})
		typeQuery = typeQuery.Where(
			fmt.Sprintf("JSON_EXTRACT(storage_device, '$.\"%s\"') IS NOT NULL", spec.MountPoint),
		)
		if spec.DiskType != "" && spec.DiskType != "ALL" {
			typeQuery = typeQuery.Where(
				fmt.Sprintf("JSON_UNQUOTE(JSON_EXTRACT(storage_device, '$.\"%s\".disk_type')) = ?", spec.MountPoint),
				spec.DiskType,
			)
		}
		var typeCount int64
		typeQuery.Count(&typeCount)
		result.TypeMatched = typeCount > 0

		if !result.TypeMatched && spec.DiskType != "" && spec.DiskType != "ALL" {
			result.FailureReason = fmt.Sprintf("no resource has disk type '%s' at mount point '%s'",
				spec.DiskType, spec.MountPoint)
			results = append(results, result)
			continue
		}

		// Check disk size match (full conditions)
		sizeQuery := buildDiskConditions(baseQuery.Session(&gorm.Session{}), []DiskSpec{spec})
		var sizeCount int64
		sizeQuery.Count(&sizeCount)
		result.SizeMatched = sizeCount > 0
		result.MatchedCount = int(sizeCount)

		if !result.SizeMatched {
			if spec.MaxSize > 0 {
				result.FailureReason = fmt.Sprintf("no resource has disk size in range [%d, %d]GB at mount point '%s'",
					spec.MinSize, spec.MaxSize, spec.MountPoint)
			} else if spec.MinSize > 0 {
				result.FailureReason = fmt.Sprintf("no resource has disk size >= %dGB at mount point '%s'",
					spec.MinSize, spec.MountPoint)
			}
		}

		results = append(results, result)
	}

	return results
}

// mergeParams merges multiple parameter maps into one.
func mergeParams(paramMaps ...map[string]interface{}) map[string]interface{} {
	result := make(map[string]interface{})
	for _, m := range paramMaps {
		for k, v := range m {
			result[k] = v
		}
	}
	return result
}

// ========== 工具定义 ==========

// GetToolDefinitions 获取所有工具定义
func (t *ResourceTools) GetToolDefinitions() []ToolDefinition {
	return []ToolDefinition{
		t.queryPoolStatsToolDef(),
		t.checkMatchConditionsToolDef(),
		t.analyzeDiskIssuesToolDef(),
		t.analyzeLabelIssuesToolDef(),
		t.analyzeRsTypeIssuesToolDef(),
		t.analyzeAffinityIssuesToolDef(),
		t.verifyPredictionToolDef(),
		t.executeCustomQueryToolDef(),
		t.inferResourceTypeToolDef(),
	}
}

func (t *ResourceTools) queryPoolStatsToolDef() ToolDefinition {
	baseParams := map[string]interface{}{
		"bk_cloud_id": map[string]interface{}{
			"type":        "integer",
			"description": "云区域ID",
		},
		"city": map[string]interface{}{
			"type":        "string",
			"description": "城市名称，可选",
		},
		"labels": map[string]interface{}{
			"type":        "array",
			"items":       map[string]interface{}{"type": "string"},
			"description": "标签列表",
		},
		"device_class": map[string]interface{}{
			"type":        "array",
			"items":       map[string]interface{}{"type": "string"},
			"description": "机型规格列表(如['S5.MEDIUM8'])，若指定则只匹配device_class",
		},
	}
	return NewFunctionTool(
		"query_pool_stats",
		"根据接口的参数查询到的资源池统计信息，包括各城市、园区的可用资源数量分布",
		map[string]interface{}{
			"type":       "object",
			"properties": mergeParams(baseParams, diskParamDefs()),
			"required":   []string{"bk_cloud_id"},
		},
	)
}

func (t *ResourceTools) checkMatchConditionsToolDef() ToolDefinition {
	baseParams := map[string]interface{}{
		"bk_cloud_id": map[string]interface{}{
			"type":        "integer",
			"description": "云区域ID",
		},
		"city": map[string]interface{}{
			"type":        "string",
			"description": "城市",
		},
		"sub_zone_ids": map[string]interface{}{
			"type":        "array",
			"items":       map[string]interface{}{"type": "string"},
			"description": "园区ID列表(硬性条件)",
		},
		"exclude_sub_zone_ids": map[string]interface{}{
			"type":        "array",
			"items":       map[string]interface{}{"type": "string"},
			"description": "排除的园区ID列表",
		},
		"exclude_rack_ids": map[string]interface{}{
			"type":        "array",
			"items":       map[string]interface{}{"type": "string"},
			"description": "排除的机架ID列表",
		},
		"cpu_min": map[string]interface{}{
			"type":        "integer",
			"description": "最小CPU核数",
		},
		"cpu_max": map[string]interface{}{
			"type":        "integer",
			"description": "最大CPU核数",
		},
		"mem_min": map[string]interface{}{
			"type":        "integer",
			"description": "最小内存(MB)",
		},
		"mem_max": map[string]interface{}{
			"type":        "integer",
			"description": "最大内存(MB)",
		},
		"labels": map[string]interface{}{
			"type":        "array",
			"items":       map[string]interface{}{"type": "string"},
			"description": "标签列表",
		},
		"resource_type": map[string]interface{}{
			"type":        "string",
			"description": "资源类型(mysql/redis等)",
		},
		"device_class": map[string]interface{}{
			"type":        "array",
			"items":       map[string]interface{}{"type": "string"},
			"description": "机型规格列表(如['S5.MEDIUM8'])，若指定则只匹配device_class",
		},
		"request_count": map[string]interface{}{
			"type":        "integer",
			"description": "申请数量",
		},
	}
	return NewFunctionTool(
		"check_match_conditions",
		"逐步检查各匹配条件对资源数量的影响，找出关键瓶颈。"+
			"【重要】基础条件与真实选机链对齐，已包含 dedicated_biz/os_type 过滤："+
			"调用时请从 RequestInputParam 中传入 intention_biz_id (或 for_biz_id)、os_type、os_names，"+
			"未传将默认按公共池 + Linux 处理。",
		map[string]interface{}{
			"type":       "object",
			"properties": mergeParams(baseParams, diskParamDefs(), bizAndOsParamDefs()),
			"required":   []string{"bk_cloud_id", "request_count"},
		},
	)
}

func (t *ResourceTools) analyzeDiskIssuesToolDef() ToolDefinition {
	baseParams := map[string]interface{}{
		"bk_cloud_id": map[string]interface{}{
			"type":        "integer",
			"description": "云区域ID",
		},
		"city": map[string]interface{}{
			"type":        "string",
			"description": "城市",
		},
		"device_class": map[string]interface{}{
			"type":        "array",
			"items":       map[string]interface{}{"type": "string"},
			"description": "机型规格列表(如['S5.MEDIUM8'])，若指定则只匹配device_class",
		},
		"cpu_min": map[string]interface{}{
			"type":        "integer",
			"description": "最小CPU核数（仅在未指定device_class时使用）",
		},
		"mem_min": map[string]interface{}{
			"type":        "integer",
			"description": "最小内存(MB)（仅在未指定device_class时使用）",
		},
	}
	// Merge with multi-disk spec parameters and legacy single disk parameters
	allParams := mergeParams(baseParams, diskSpecParamDefs(), diskParamDefs())
	// Also add mount_point/min_size/max_size for backward compatibility
	allParams["mount_point"] = map[string]interface{}{
		"type":        "string",
		"description": "挂载点(如'/data')（单磁盘查询，向后兼容）",
	}
	allParams["min_size"] = map[string]interface{}{
		"type":        "integer",
		"description": "最小磁盘大小(GB)（单磁盘查询，向后兼容）",
	}
	allParams["max_size"] = map[string]interface{}{
		"type":        "integer",
		"description": "最大磁盘大小(GB)（单磁盘查询，向后兼容）",
	}
	return NewFunctionTool(
		"analyze_disk_issues",
		`分析磁盘匹配问题，支持多块磁盘条件查询（如/data, /data1, /data2），检查挂载点、类型、大小是否满足。使用disk_specs数组参数指定多磁盘条件
		- 如果 storage_device字段均为空对象{},表示该资源是没有磁盘 
		`,
		map[string]interface{}{
			"type":       "object",
			"properties": allParams,
			"required":   []string{"bk_cloud_id"},
		},
	)
}

func (t *ResourceTools) analyzeLabelIssuesToolDef() ToolDefinition {
	baseParams := map[string]interface{}{
		"bk_cloud_id": map[string]interface{}{
			"type":        "integer",
			"description": "云区域ID",
		},
		"city": map[string]interface{}{
			"type":        "string",
			"description": "城市",
		},
		"device_class": map[string]interface{}{
			"type":        "array",
			"items":       map[string]interface{}{"type": "string"},
			"description": "机型规格列表(如['S5.MEDIUM8'])，若指定则只匹配device_class",
		},
		"cpu_min": map[string]interface{}{
			"type":        "integer",
			"description": "最小CPU核数（仅在未指定device_class时使用）",
		},
		"mem_min": map[string]interface{}{
			"type":        "integer",
			"description": "最小内存(MB)（仅在未指定device_class时使用）",
		},
		"requested_labels": map[string]interface{}{
			"type":        "array",
			"items":       map[string]interface{}{"type": "string"},
			"description": "申请时指定的标签",
		},
	}
	return NewFunctionTool(
		"analyze_label_issues",
		"分析标签匹配问题，检查无标签申请与有标签资源的冲突",
		map[string]interface{}{
			"type":       "object",
			"properties": mergeParams(baseParams, diskParamDefs(), diskSpecParamDefs()),
			"required":   []string{"bk_cloud_id"},
		},
	)
}

func (t *ResourceTools) analyzeRsTypeIssuesToolDef() ToolDefinition {
	baseParams := map[string]interface{}{
		"bk_cloud_id": map[string]interface{}{
			"type":        "integer",
			"description": "云区域ID",
		},
		"city": map[string]interface{}{
			"type":        "string",
			"description": "城市",
		},
		"device_class": map[string]interface{}{
			"type":        "array",
			"items":       map[string]interface{}{"type": "string"},
			"description": "机型规格列表(如['S5.MEDIUM8'])，若指定则只匹配device_class",
		},
		"cpu_min": map[string]interface{}{
			"type":        "integer",
			"description": "最小CPU核数（仅在未指定device_class时使用）",
		},
		"mem_min": map[string]interface{}{
			"type":        "integer",
			"description": "最小内存(MB)（仅在未指定device_class时使用）",
		},
		"requested_type": map[string]interface{}{
			"type":        "string",
			"description": "申请的资源类型",
		},
	}
	return NewFunctionTool(
		"analyze_rstype_issues",
		"分析资源类型匹配问题，检查PUBLIC与专用类型分布，检测类型名称不一致",
		map[string]interface{}{
			"type":       "object",
			"properties": mergeParams(baseParams, diskParamDefs(), diskSpecParamDefs()),
			"required":   []string{"bk_cloud_id"},
		},
	)
}

func (t *ResourceTools) analyzeAffinityIssuesToolDef() ToolDefinition {
	baseParams := map[string]interface{}{
		"bk_cloud_id": map[string]interface{}{
			"type":        "integer",
			"description": "云区域ID",
		},
		"city": map[string]interface{}{
			"type":        "string",
			"description": "城市",
		},
		"sub_zone_ids": map[string]interface{}{
			"type":        "array",
			"items":       map[string]interface{}{"type": "string"},
			"description": "园区ID列表(如['1109'])",
		},
		"affinity_type": map[string]interface{}{
			"type":        "string",
			"description": "亲和性类型: SAME_SUBZONE_CROSS_SWTICH/CROSS_RACK/CROS_SUBZONE/CROSS_SUBZONE_STRONG/CROSS_SUBZONE_WEAK",
		},
		"request_count": map[string]interface{}{
			"type":        "integer",
			"description": "申请数量",
		},
		"tolerance": map[string]interface{}{
			"type":        "number",
			"description": "容忍度(0-1)，用于CROS_SUBZONE等亲和性",
		},
		"cpu_min": map[string]interface{}{
			"type":        "integer",
			"description": "最小CPU核数",
		},
		"mem_min": map[string]interface{}{
			"type":        "integer",
			"description": "最小内存(MB)",
		},
		"device_class": map[string]interface{}{
			"type":        "array",
			"items":       map[string]interface{}{"type": "string"},
			"description": "机型规格列表(如['S5.MEDIUM8'])",
		},
		"resource_type": map[string]interface{}{
			"type":        "string",
			"description": "资源类型(mysql/redis等)",
		},
		"labels": map[string]interface{}{
			"type":        "array",
			"items":       map[string]interface{}{"type": "string"},
			"description": "标签列表",
		},
		"exclude_rack_ids": map[string]interface{}{
			"type":        "array",
			"items":       map[string]interface{}{"type": "string"},
			"description": "排除的机架ID列表",
		},
		"exclude_sub_zone_ids": map[string]interface{}{
			"type":        "array",
			"items":       map[string]interface{}{"type": "string"},
			"description": "排除的园区ID列表",
		},
	}
	return NewFunctionTool(
		"analyze_affinity_issues",
		"分析亲和性匹配问题，展示资源在机架/交换机上的分布情况。"+
			"SAME_SUBZONE_CROSS_SWTICH要求同城同园区跨机架跨交换机，需要机架和交换机数量都>=申请数量。"+
			"【重要】候选库存评估已对齐真实选机链，包含 dedicated_biz/os_type 过滤："+
			"调用时请从 RequestInputParam 中传入 intention_biz_id (或 for_biz_id)、os_type、os_names。",
		map[string]interface{}{
			"type":       "object",
			"properties": mergeParams(baseParams, diskParamDefs(), diskSpecParamDefs(), bizAndOsParamDefs()),
			"required":   []string{"bk_cloud_id", "affinity_type", "request_count"},
		},
	)
}

func (t *ResourceTools) executeCustomQueryToolDef() ToolDefinition {
	return NewFunctionTool(
		"execute_custom_query",
		`执行自定义 SQL 查询来验证推测或深入分析问题。只能执行 SELECT 查询，用于验证假设、检查数据分布、统计资源数量等。

tb_rp_detail 表字段说明：
- bk_cloud_id: 云区域ID (int)
- city: 城市 (string)
- sub_zone: 园区名称 (string)
- sub_zone_id: 园区ID (string)
- rack_id: 机架ID (string)
- net_device_id: 网络设备/交换机ID (string)
- device_class: 机型规格 (string)
- cpu_num: CPU核数 (int)，注意不是cpu
- dram_cap: 内存大小MB (int)
- storage_device: 磁盘设备JSON (json)
- rs_type: 资源类型 (string)，如 PUBLIC/redis/mysql 等
- status: 状态 (string)，如 Unused/Used。选机只看 Unused
- gse_agent_status_code: Agent状态码 (int)，1表示正常
- labels: 标签JSON (json)

禁止分析、禁止写入 WHERE 的字段（看见也忽略）：
- consume_time: 仅机器被选中落账后才更新；1970-01-01 08:00:01 表示从未被消费，不是锁定
- is_idle: 导入侧空闲检查标记，不是“当前是否空闲”
- is_init: 导入侧初始化标记，选机不读`,
		map[string]interface{}{
			"type": "object",
			"properties": map[string]interface{}{
				"sql": map[string]interface{}{
					"type":        "string",
					"description": `要执行的 SQL SELECT 查询语句。只能查询 tb_rp_detail 表，只能使用 SELECT 语句。注意：CPU 字段名是 cpu_num 而不是 cpu。查询磁盘必须用 MySQL JSON Path，挂载点含斜杠要加双引号：JSON_EXTRACT(storage_device, '$."/data".size')、JSON_UNQUOTE(JSON_EXTRACT(storage_device, '$."/data".disk_type'))。禁止写成 JSON_EXTRACT(storage_device, '/data/size')，那不是合法 JSON Path，永远返回 NULL。示例：SELECT COUNT(*) as count, sub_zone_id FROM tb_rp_detail WHERE bk_cloud_id = 0 AND status = 'Unused' GROUP BY sub_zone_id`,
				},
				"description": map[string]interface{}{
					"type":        "string",
					"description": "查询目的说明，用于记录为什么执行这个查询",
				},
			},
			"required": []string{"sql", "description"},
		},
	)
}

func (t *ResourceTools) verifyPredictionToolDef() ToolDefinition {
	baseParams := map[string]interface{}{
		"bk_cloud_id": map[string]interface{}{
			"type":        "integer",
			"description": "云区域ID",
		},
		"city": map[string]interface{}{
			"type":        "string",
			"description": "城市",
		},
		"device_class": map[string]interface{}{
			"type":        "array",
			"items":       map[string]interface{}{"type": "string"},
			"description": "机型规格列表(如['S5.MEDIUM8'])，若指定则只匹配device_class",
		},
		"cpu_min": map[string]interface{}{
			"type":        "integer",
			"description": "最小CPU核数（仅在未指定device_class时使用）",
		},
		"mem_min": map[string]interface{}{
			"type":        "integer",
			"description": "最小内存(MB)（仅在未指定device_class时使用）",
		},
		"resource_type": map[string]interface{}{
			"type":        "string",
			"description": "资源类型",
		},
		"labels": map[string]interface{}{
			"type":        "array",
			"items":       map[string]interface{}{"type": "string"},
			"description": "标签列表",
		},
		"suggestion_type": map[string]interface{}{
			"type":        "string",
			"description": "建议类型: add_resources/adjust_spec/add_labels/change_rstype/adjust_disk",
		},
		"request_count": map[string]interface{}{
			"type":        "integer",
			"description": "申请数量，用于判断验证是否通过",
		},
	}
	return NewFunctionTool(
		"verify_prediction",
		"验证建议的可行性，查询按建议调整条件后的实际资源数量。支持验证多种建议类型的效果，并返回详细的验证结果",
		map[string]interface{}{
			"type":       "object",
			"properties": mergeParams(baseParams, diskParamDefs(), diskSpecParamDefs()),
			"required":   []string{"bk_cloud_id"},
		},
	)
}

// ========== 工具执行 ==========

// ExecuteTool 执行工具
func (t *ResourceTools) ExecuteTool(name string, argsJSON string) (interface{}, error) {
	var args map[string]interface{}
	if err := json.Unmarshal([]byte(argsJSON), &args); err != nil {
		return nil, fmt.Errorf("failed to parse tool arguments: %v", err)
	}

	switch name {
	case "query_pool_stats":
		return t.QueryPoolStats(args)
	case "check_match_conditions":
		return t.CheckMatchConditions(args)
	case "analyze_disk_issues":
		return t.AnalyzeDiskIssues(args)
	case "analyze_label_issues":
		return t.AnalyzeLabelIssues(args)
	case "analyze_rstype_issues":
		return t.AnalyzeRsTypeIssues(args)
	case "analyze_affinity_issues":
		return t.AnalyzeAffinityIssues(args)
	case "verify_prediction":
		return t.VerifyPrediction(args)
	case "execute_custom_query":
		return t.ExecuteCustomQuery(args)
	case "infer_resource_type":
		return t.inferResourceType(args)
	default:
		return nil, fmt.Errorf("unknown tool: %s", name)
	}
}

// ========== 资源池统计 ==========

// PoolStats 资源池统计结果
type PoolStats struct {
	TotalAvailable int            `json:"total_available"`
	ByCity         map[string]int `json:"by_city"`
	BySubZone      map[string]int `json:"by_subzone"`
	ByRsType       map[string]int `json:"by_rs_type"`
	BySpec         map[string]int `json:"by_spec"`
	SQL            string         `json:"sql,omitempty"` // 用于调试的 SQL 语句
}

// QueryPoolStats 查询资源池统计
func (t *ResourceTools) QueryPoolStats(args map[string]interface{}) (*PoolStats, error) {
	bkCloudID := getBkCloudID(args)
	city, _ := args["city"].(string)
	diskMountPoint, _ := args["disk_mount_point"].(string)
	diskType, _ := args["disk_type"].(string)
	diskMinSize, _ := args["disk_min_size"].(float64)
	diskMaxSize, _ := args["disk_max_size"].(float64)
	resourceType, _ := args["resource_type"].(string)
	resourceType = model.NormalizeResourceType(resourceType)
	result := &PoolStats{
		ByCity:    make(map[string]int),
		BySubZone: make(map[string]int),
		ByRsType:  make(map[string]int),
		BySpec:    make(map[string]int),
	}

	// 基础查询
	baseQuery := t.db.Table(model.TbRpDetailName()).
		Where("bk_cloud_id = ? AND status = ? AND gse_agent_status_code = ?",
			bkCloudID, model.Unused, bk.GseAlive)

	if city != "" {
		baseQuery = baseQuery.Where("city = ?", city)
	}
	deviceClass, _ := args["device_class"].([]interface{})
	var deviceClassStrs []string
	for _, d := range deviceClass {
		deviceClassStrs = append(deviceClassStrs, d.(string))
	}
	if len(deviceClassStrs) > 0 {
		baseQuery = baseQuery.Where("device_class IN (?)", deviceClassStrs)
	}
	labels, _ := args["labels"].([]interface{})
	if len(labels) > 0 {
		labelStrs := make([]string, 0, len(labels))
		for _, l := range labels {
			labelStrs = append(labelStrs, l.(string))
		}
		baseQuery = baseQuery.Where(model.JSONQuery("labels").JointOrContains(labelStrs))
	}
	if resourceType != "" {
		baseQuery = baseQuery.Where("rs_type IN (?)", []string{model.RESOURCE_TYPE_PUBLIC, resourceType})
	} else {
		baseQuery = baseQuery.Where("rs_type = ?", model.RESOURCE_TYPE_PUBLIC)
	}
	// 磁盘过滤
	if diskMountPoint != "" {
		if diskMaxSize > 0 && diskMinSize > 0 {
			// 使用范围匹配 [min, max]
			baseQuery = baseQuery.Where(model.JSONQuery("storage_device").NumRange(int(diskMinSize), int(diskMaxSize), diskMountPoint, "size"))
		} else if diskMinSize > 0 {
			// 只使用最小值 >= min
			baseQuery = baseQuery.Where(model.JSONQuery("storage_device").Gte(int(diskMinSize), diskMountPoint, "size"))
		}
		if diskType != "" {
			baseQuery = baseQuery.Where(model.JSONQuery("storage_device").Equals(diskType, diskMountPoint, "disk_type"))
		}
	}
	// 获取 SQL（用于调试）
	result.SQL = t.getSQLFromQuery(baseQuery.Model(&model.TbRpDetail{}))

	// 总数
	var total int64
	if err := baseQuery.Count(&total).Error; err != nil {
		return nil, err
	}
	result.TotalAvailable = int(total)

	// 按城市统计
	var cityStats []struct {
		City  string
		Count int
	}
	t.db.Table(model.TbRpDetailName()).
		Select("city, count(*) as count").
		Where("bk_cloud_id = ? AND status = ? AND gse_agent_status_code = ?",
			bkCloudID, model.Unused, bk.GseAlive).
		Group("city").
		Scan(&cityStats)
	for _, s := range cityStats {
		result.ByCity[s.City] = s.Count
	}

	// 按园区统计
	var subZoneStats []struct {
		SubZone string
		Count   int
	}
	query := t.db.Table(model.TbRpDetailName()).
		Select("sub_zone, count(*) as count").
		Where("bk_cloud_id = ? AND status = ? AND gse_agent_status_code = ?",
			bkCloudID, model.Unused, bk.GseAlive)
	if city != "" {
		query = query.Where("city = ?", city)
	}
	query.Group("sub_zone").Scan(&subZoneStats)
	for _, s := range subZoneStats {
		result.BySubZone[s.SubZone] = s.Count
	}

	// 按资源类型统计
	var rsTypeStats []struct {
		RsType string
		Count  int
	}
	query = t.db.Table(model.TbRpDetailName()).
		Select("rs_type, count(*) as count").
		Where("bk_cloud_id = ? AND status = ? AND gse_agent_status_code = ?",
			bkCloudID, model.Unused, bk.GseAlive)
	if city != "" {
		query = query.Where("city = ?", city)
	}
	query.Group("rs_type").Scan(&rsTypeStats)
	for _, s := range rsTypeStats {
		result.ByRsType[s.RsType] = s.Count
	}

	return result, nil
}

// ========== 条件影响分析 ==========

// ConditionImpact 条件影响
type ConditionImpact struct {
	Condition     string  `json:"condition"`
	Description   string  `json:"description"`
	BeforeCount   int     `json:"before_count"`
	AfterCount    int     `json:"after_count"`
	Reduction     int     `json:"reduction"`
	ReductionRate float64 `json:"reduction_rate"`
	IsCritical    bool    `json:"is_critical"`
}

// MatchConditionsResult 匹配条件检查结果
type MatchConditionsResult struct {
	RequestCount      int               `json:"request_count"`
	BaseCount         int               `json:"base_count"`        // 基础条件（云区域+状态）的资源数
	TotalTableCount   int               `json:"total_table_count"` // 资源表总记录数（用于判断表是否为空）
	FinalCount        int               `json:"final_count"`
	Impacts           []ConditionImpact `json:"impacts"`
	CriticalCondition string            `json:"critical_condition"`
	Summary           string            `json:"summary"`
	RootCause         string            `json:"root_cause,omitempty"` // 根本原因说明
	SQL               string            `json:"sql,omitempty"`        // 最终查询的 SQL（用于调试）
}

// CheckMatchConditions 逐步检查匹配条件
func (t *ResourceTools) CheckMatchConditions(args map[string]interface{}) (*MatchConditionsResult, error) {
	bkCloudID := getBkCloudID(args)
	requestCount := int(args["request_count"].(float64))
	city, _ := args["city"].(string)
	cpuMin, _ := args["cpu_min"].(float64)
	cpuMax, _ := args["cpu_max"].(float64)
	memMin, _ := args["mem_min"].(float64)
	memMax, _ := args["mem_max"].(float64)
	diskMountPoint, _ := args["disk_mount_point"].(string)
	diskMinSize, _ := args["disk_min_size"].(float64)
	diskMaxSize, _ := args["disk_max_size"].(float64)
	diskType, _ := args["disk_type"].(string)
	resourceType, _ := args["resource_type"].(string)
	resourceType = model.NormalizeResourceType(resourceType)
	labels, _ := args["labels"].([]interface{})

	// 解析 device_class 参数
	var deviceClasses []string
	if classes, ok := args["device_class"].([]interface{}); ok {
		for _, c := range classes {
			if s, ok := c.(string); ok && s != "" {
				deviceClasses = append(deviceClasses, s)
			}
		}
	}

	// 解析 location_spec 相关参数
	var subZoneIds []string
	if ids, ok := args["sub_zone_ids"].([]interface{}); ok {
		for _, id := range ids {
			if s, ok := id.(string); ok && s != "" {
				subZoneIds = append(subZoneIds, s)
			}
		}
	}
	var excludeSubZoneIds []string
	if ids, ok := args["exclude_sub_zone_ids"].([]interface{}); ok {
		for _, id := range ids {
			if s, ok := id.(string); ok && s != "" {
				excludeSubZoneIds = append(excludeSubZoneIds, s)
			}
		}
	}
	var excludeRackIds []string
	if ids, ok := args["exclude_rack_ids"].([]interface{}); ok {
		for _, id := range ids {
			if s, ok := id.(string); ok && s != "" {
				excludeRackIds = append(excludeRackIds, s)
			}
		}
	}

	result := &MatchConditionsResult{
		RequestCount: requestCount,
		Impacts:      make([]ConditionImpact, 0),
	}

	// 0. 先检查资源表总记录数（用于判断表是否为空）
	var totalTableCount int64
	t.db.Table(model.TbRpDetailName()).Count(&totalTableCount)
	result.TotalTableCount = int(totalTableCount)

	// 1. 基础条件：云区域 + 状态 + 业务/操作系统（与 apply.SearchContext.pickBase 对齐，
	//    避免遗漏 dedicated_biz/os_type 导致候选数量被高估）
	baseQuery := t.db.Table(model.TbRpDetailName()).
		Where("bk_cloud_id = ? AND status = ? AND gse_agent_status_code = ?",
			bkCloudID, model.Unused, bk.GseAlive)
	baseQuery = applyBizAndOsFilters(baseQuery, args)

	var baseCount int64
	baseQuery.Count(&baseCount)
	result.BaseCount = int(baseCount)
	prevCount := int(baseCount)

	// 如果基础条件就是0，需要明确标识根本原因
	if result.BaseCount == 0 {
		if result.TotalTableCount == 0 {
			result.RootCause = "资源表为空，没有任何资源记录"
			result.Summary = "资源表完全为空，没有任何资源记录。需要先导入资源数据。"
			result.CriticalCondition = "empty_table"
		} else {
			result.RootCause = fmt.Sprintf("云区域 %d 下没有任何可用资源（status=unused）。资源表总共有 %d 条记录，但都不满足云区域和状态条件", bkCloudID, result.TotalTableCount)
			result.Summary = fmt.Sprintf("云区域 %d 下没有任何可用资源。资源表总共有 %d 条记录，但都不满足云区域和状态条件（bk_cloud_id=%d AND status=unused）", bkCloudID, result.TotalTableCount, bkCloudID)
			result.CriticalCondition = "no_available_in_cloud"
		}
		// 获取 SQL
		result.SQL = t.getSQLFromQuery(baseQuery)
		return result, nil
	}

	// 2. 逐步添加条件（按优先级排序：基础条件 -> 磁盘/标签等可选条件）
	conditions := []struct {
		name       string
		desc       string
		applyFn    func(db *gorm.DB) *gorm.DB
		skip       bool
		isCritical bool // 是否为关键条件（基础条件），如果关键条件过滤后就不够，应该直接返回
	}{
		{
			name: "city",
			desc: fmt.Sprintf("城市条件(城市=%s)", city),
			applyFn: func(db *gorm.DB) *gorm.DB {
				return db.Where("city = ?", city)
			},
			skip:       city == "",
			isCritical: true,
		},
		{
			name: "sub_zone_ids",
			desc: fmt.Sprintf("园区ID条件(sub_zone_ids=%v)", subZoneIds),
			applyFn: func(db *gorm.DB) *gorm.DB {
				return db.Where("sub_zone_id IN ?", subZoneIds)
			},
			skip:       len(subZoneIds) == 0,
			isCritical: true,
		},
		{
			name: "exclude_sub_zones",
			desc: fmt.Sprintf("排除园区条件(exclude=%v)", excludeSubZoneIds),
			applyFn: func(db *gorm.DB) *gorm.DB {
				return db.Where("sub_zone_id NOT IN ?", excludeSubZoneIds)
			},
			skip:       len(excludeSubZoneIds) == 0,
			isCritical: true,
		},
		{
			name: "exclude_racks",
			desc: fmt.Sprintf("排除机架条件(exclude=%v)", excludeRackIds),
			applyFn: func(db *gorm.DB) *gorm.DB {
				return db.Where("rack_id NOT IN ?", excludeRackIds)
			},
			skip:       len(excludeRackIds) == 0,
			isCritical: true,
		},
		{
			name: "rs_type",
			desc: fmt.Sprintf("资源类型(%s)", resourceType),
			applyFn: func(db *gorm.DB) *gorm.DB {
				if resourceType == "" {
					return db.Where("rs_type = ?", model.RESOURCE_TYPE_PUBLIC)
				}
				return db.Where("rs_type IN (?)", []string{model.RESOURCE_TYPE_PUBLIC, resourceType})
			},
			skip:       false,
			isCritical: true,
		},
		{
			name: "device_class",
			desc: fmt.Sprintf("机型规格条件(device_class=%v)", deviceClasses),
			applyFn: func(db *gorm.DB) *gorm.DB {
				return db.Where("device_class IN ?", deviceClasses)
			},
			skip:       len(deviceClasses) == 0,
			isCritical: true,
		},
		{
			name: "cpu",
			desc: fmt.Sprintf("CPU规格(%d~%d核)", int(cpuMin), int(cpuMax)),
			applyFn: func(db *gorm.DB) *gorm.DB {
				if cpuMin > 0 {
					db = db.Where("cpu_num >= ?", int(cpuMin))
				}
				if cpuMax > 0 {
					db = db.Where("cpu_num <= ?", int(cpuMax))
				}
				return db
			},
			skip:       len(deviceClasses) > 0 || (cpuMin == 0 && cpuMax == 0),
			isCritical: true,
		},
		{
			name: "memory",
			desc: fmt.Sprintf("内存规格(>=%dMB)", int(memMin)),
			applyFn: func(db *gorm.DB) *gorm.DB {
				if memMin > 0 {
					db = db.Where("dram_cap >= ?", int(memMin))
				}
				if memMax > 0 {
					db = db.Where("dram_cap <= ?", int(memMax))
				}
				return db
			},
			skip:       len(deviceClasses) > 0 || (memMin == 0 && memMax == 0),
			isCritical: true,
		},
		{
			name: "labels",
			desc: "标签条件",
			applyFn: func(db *gorm.DB) *gorm.DB {
				if len(labels) == 0 {
					return db.Where("JSON_TYPE(labels) = 'NULL' OR JSON_LENGTH(labels) < 1")
				}
				labelStrs := make([]string, 0, len(labels))
				for _, l := range labels {
					labelStrs = append(labelStrs, l.(string))
				}
				return db.Where(model.JSONQuery("labels").JointOrContains(labelStrs))
			},
			skip:       false,
			isCritical: false, // 标签是可选条件
		},
		{
			name: "disk",
			desc: func() string {
				if diskMaxSize > 0 {
					return fmt.Sprintf("磁盘条件(%s [%d-%d]GB, 类型=%s)", diskMountPoint, int(diskMinSize), int(diskMaxSize), diskType)
				}
				return fmt.Sprintf("磁盘条件(%s >= %dGB, 类型=%s)", diskMountPoint, int(diskMinSize), diskType)
			}(),
			applyFn: func(db *gorm.DB) *gorm.DB {
				if diskMountPoint != "" {
					if diskMaxSize > 0 && diskMinSize > 0 {
						// 使用范围匹配 [min, max]
						db = db.Where(model.JSONQuery("storage_device").NumRange(int(diskMinSize), int(diskMaxSize), diskMountPoint, "size"))
					} else if diskMinSize > 0 {
						// 只使用最小值 >= min
						db = db.Where(model.JSONQuery("storage_device").Gte(int(diskMinSize), diskMountPoint, "size"))
					}
					if diskType != "" {
						db = db.Where(model.JSONQuery("storage_device").Equals(diskType, diskMountPoint, "disk_type"))
					}
				}
				return db
			},
			skip:       diskMountPoint == "" && diskMinSize == 0,
			isCritical: false, // 磁盘是可选条件，如果基础条件就不够，不需要继续分析磁盘
		},
	}

	// 累积查询：基础条件需与 baseQuery 完全一致，包含 dedicated_biz/os_type 过滤
	cumulativeQuery := t.db.Table(model.TbRpDetailName()).
		Where("bk_cloud_id = ? AND status = ? AND gse_agent_status_code = ?",
			bkCloudID, model.Unused, bk.GseAlive)
	cumulativeQuery = applyBizAndOsFilters(cumulativeQuery, args)

	for _, cond := range conditions {
		if cond.skip {
			continue
		}

		cumulativeQuery = cond.applyFn(cumulativeQuery)

		var count int64
		cumulativeQuery.Count(&count)
		currentCount := int(count)

		reduction := prevCount - currentCount
		var reductionRate float64
		if prevCount > 0 {
			reductionRate = float64(reduction) / float64(prevCount)
		}

		impact := ConditionImpact{
			Condition:     cond.name,
			Description:   cond.desc,
			BeforeCount:   prevCount,
			AfterCount:    currentCount,
			Reduction:     reduction,
			ReductionRate: reductionRate,
			IsCritical:    currentCount < requestCount && prevCount >= requestCount,
		}

		result.Impacts = append(result.Impacts, impact)

		if impact.IsCritical && result.CriticalCondition == "" {
			result.CriticalCondition = cond.name
		}

		// 如果这是关键条件（基础条件），且过滤后资源数 < 申请数量，直接返回，不再分析后续可选条件
		if cond.isCritical && currentCount < requestCount {
			shortage := requestCount - currentCount
			shortageRate := float64(shortage) / float64(requestCount) * 100
			result.FinalCount = currentCount
			result.SQL = t.getSQLFromQuery(cumulativeQuery)
			result.RootCause = fmt.Sprintf("资源总数不足：需要 %d 台，但基础条件（城市、园区、设备规格、资源类型等）过滤后仅有 %d 台，缺少 %d 台（%.1f%%）。即使后续条件（磁盘、标签等）全部满足，也无法满足需求",
				requestCount, currentCount, shortage, shortageRate)
			result.Summary = fmt.Sprintf("资源总数不足：基础条件过滤后仅有 %d 台，不满足 %d 台的需求，缺少 %d 台",
				currentCount, requestCount, shortage)
			if result.CriticalCondition == "" {
				result.CriticalCondition = cond.name
			}
			return result, nil
		}

		prevCount = currentCount
	}

	result.FinalCount = prevCount

	// 获取最终查询的 SQL（用于调试）
	result.SQL = t.getSQLFromQuery(cumulativeQuery)

	// 如果最终数量明显小于申请数量，需要明确标识
	if result.FinalCount < requestCount {
		// 如果最终数量为0，检查是否是基础条件（城市、园区）导致的
		if result.FinalCount == 0 && result.RootCause == "" {
			// 检查是否是城市或园区条件导致的
			for _, impact := range result.Impacts {
				if impact.Condition == "city" && impact.AfterCount == 0 && impact.BeforeCount > 0 {
					result.RootCause = fmt.Sprintf("城市条件（%s）过滤后资源数为0。该城市下没有任何可用资源", city)
					result.Summary = fmt.Sprintf("城市条件（%s）是根本原因：添加该条件后资源从 %d 台降至 0 台", city, impact.BeforeCount)
					result.CriticalCondition = "city_no_resource"
					return result, nil
				}
				if impact.Condition == "sub_zone_ids" && impact.AfterCount == 0 && impact.BeforeCount > 0 {
					result.RootCause = fmt.Sprintf("园区ID条件（%v）过滤后资源数为0。指定的园区下没有任何可用资源", subZoneIds)
					result.Summary = fmt.Sprintf("园区ID条件（%v）是根本原因：添加该条件后资源从 %d 台降至 0 台", subZoneIds, impact.BeforeCount)
					result.CriticalCondition = "subzone_no_resource"
					return result, nil
				}
			}
			// 如果所有条件都检查完了还是0，说明是多个条件叠加导致的
			if result.BaseCount > 0 {
				result.RootCause = fmt.Sprintf("所有匹配条件叠加后资源数为0。基础条件（云区域+状态）有 %d 台资源，但添加所有条件后变为0", result.BaseCount)
			}
		} else if result.FinalCount > 0 && result.RootCause == "" {
			// 资源数量不足但大于0，明确说明差距
			shortage := requestCount - result.FinalCount
			shortageRate := float64(shortage) / float64(requestCount) * 100
			result.RootCause = fmt.Sprintf("资源数量不足：需要 %d 台，但仅有 %d 台符合所有条件，缺少 %d 台（%.1f%%）",
				requestCount, result.FinalCount, shortage, shortageRate)
			// 找出导致资源减少最多的条件
			maxReduction := 0
			maxReductionCondition := ""
			for _, impact := range result.Impacts {
				if impact.Reduction > maxReduction {
					maxReduction = impact.Reduction
					maxReductionCondition = impact.Condition
				}
			}
			if maxReductionCondition != "" {
				for _, impact := range result.Impacts {
					if impact.Condition == maxReductionCondition {
						result.RootCause += fmt.Sprintf("。其中【%s】条件影响最大，导致资源减少 %d 台（从 %d 降至 %d）",
							impact.Description, impact.Reduction, impact.BeforeCount, impact.AfterCount)
						break
					}
				}
			}
		}
	}

	// 生成摘要（如果还没有设置）
	if result.Summary == "" {
		if result.CriticalCondition != "" {
			for _, imp := range result.Impacts {
				if imp.Condition == result.CriticalCondition {
					result.Summary = fmt.Sprintf("关键瓶颈条件是【%s】，添加该条件后资源从 %d 台降至 %d 台（减少 %.1f%%），不满足 %d 台的需求",
						imp.Description, imp.BeforeCount, imp.AfterCount, imp.ReductionRate*100, requestCount)
					break
				}
			}
		} else if result.FinalCount < requestCount {
			result.Summary = fmt.Sprintf("所有条件叠加后资源仅 %d 台，不满足 %d 台的需求，需要综合调整多个条件",
				result.FinalCount, requestCount)
		} else {
			result.Summary = fmt.Sprintf("资源充足，符合条件的资源有 %d 台，满足 %d 台的需求",
				result.FinalCount, requestCount)
		}
	}

	return result, nil
}

// ========== 磁盘问题分析 ==========

// DiskAnalysisResult 磁盘分析结果
type DiskAnalysisResult struct {
	TotalMachines        int                        `json:"total_machines"`
	WithMountPoint       int                        `json:"with_mount_point"`
	WithCorrectType      int                        `json:"with_correct_type"`
	WithEnoughSize       int                        `json:"with_enough_size"`
	MaxAvailableSize     int                        `json:"max_available_size"`
	DiskTypeDistribution map[string]int             `json:"disk_type_distribution"`
	IssueType            string                     `json:"issue_type,omitempty"`
	IssueDetail          string                     `json:"issue_detail,omitempty"`
	Suggestion           string                     `json:"suggestion,omitempty"`
	SQL                  string                     `json:"sql,omitempty"` // 用于调试的 SQL 语句
	MultiDiskResults     []DiskMatchResult          `json:"multi_disk_results,omitempty"`
	AllDisksMatched      int                        `json:"all_disks_matched,omitempty"`
	PerDiskStats         map[string]*DiskStatistics `json:"per_disk_stats,omitempty"`
}

// DiskStatistics represents statistics for a single mount point
type DiskStatistics struct {
	MountPoint           string         `json:"mount_point"`
	WithMountPoint       int            `json:"with_mount_point"`
	WithCorrectType      int            `json:"with_correct_type"`
	WithEnoughSize       int            `json:"with_enough_size"`
	MaxAvailableSize     int            `json:"max_available_size"`
	DiskTypeDistribution map[string]int `json:"disk_type_distribution"`
}

// AnalyzeDiskIssues 分析磁盘问题，支持多块磁盘条件查询
func (t *ResourceTools) AnalyzeDiskIssues(args map[string]interface{}) (*DiskAnalysisResult, error) {
	bkCloudID := getBkCloudID(args)
	city, _ := args["city"].(string)
	cpuMin, _ := args["cpu_min"].(float64)
	memMin, _ := args["mem_min"].(float64)

	// 解析 device_class 参数
	var deviceClasses []string
	if classes, ok := args["device_class"].([]interface{}); ok {
		for _, c := range classes {
			if s, ok := c.(string); ok && s != "" {
				deviceClasses = append(deviceClasses, s)
			}
		}
	}

	// 解析磁盘规格（支持新格式和旧格式）
	diskSpecs := parseDiskSpecs(args)

	result := &DiskAnalysisResult{
		DiskTypeDistribution: make(map[string]int),
		PerDiskStats:         make(map[string]*DiskStatistics),
	}

	// 基础查询
	baseQuery := t.db.Table(model.TbRpDetailName()).
		Where("bk_cloud_id = ? AND status = ? AND gse_agent_status_code = ?",
			bkCloudID, model.Unused, bk.GseAlive)
	if city != "" {
		baseQuery = baseQuery.Where("city = ?", city)
	}
	// 应用规格条件（device_class 和 cpu/mem 互斥）
	if len(deviceClasses) > 0 {
		baseQuery = baseQuery.Where("device_class IN ?", deviceClasses)
	} else {
		// 如果没有 device_class，则使用 cpu/mem
		if cpuMin > 0 {
			baseQuery = baseQuery.Where("cpu_num >= ?", int(cpuMin))
		}
		if memMin > 0 {
			baseQuery = baseQuery.Where("dram_cap >= ?", int(memMin))
		}
	}

	// 获取 SQL（用于调试）
	result.SQL = t.getSQLFromQuery(baseQuery)

	// 总机器数
	var total int64
	baseQuery.Count(&total)
	result.TotalMachines = int(total)

	// 如果没有指定磁盘条件，直接返回基础统计
	if len(diskSpecs) == 0 {
		return result, nil
	}

	// 查询所有符合基础条件的机器
	var machines []model.TbRpDetail
	baseQuery.Find(&machines)

	// 对于多磁盘分析，逐个分析每个磁盘规格
	result.MultiDiskResults = t.analyzeDiskSpecMatches(baseQuery, diskSpecs)

	// 分析每个磁盘的详细统计
	for _, spec := range diskSpecs {
		stats := &DiskStatistics{
			MountPoint:           spec.MountPoint,
			DiskTypeDistribution: make(map[string]int),
		}

		for _, m := range machines {
			if err := m.UnmarshalDiskInfo(); err != nil {
				continue
			}

			if disk, ok := m.Storages[spec.MountPoint]; ok {
				stats.WithMountPoint++

				// 统计磁盘类型分布
				stats.DiskTypeDistribution[disk.DiskType]++

				// 检查类型
				if spec.DiskType == "" || spec.DiskType == "ALL" || strings.EqualFold(disk.DiskType, spec.DiskType) {
					stats.WithCorrectType++
				}

				// 检查大小（范围匹配）
				sizeMatch := false
				if spec.MaxSize > 0 {
					sizeMatch = disk.Size >= spec.MinSize && disk.Size <= spec.MaxSize
				} else {
					sizeMatch = disk.Size >= spec.MinSize
				}
				if sizeMatch {
					stats.WithEnoughSize++
				}

				// 记录最大可用大小
				if disk.Size > stats.MaxAvailableSize {
					stats.MaxAvailableSize = disk.Size
				}
			}
		}

		result.PerDiskStats[spec.MountPoint] = stats

		// 更新全局的磁盘类型分布（合并所有挂载点的分布）
		for dt, cnt := range stats.DiskTypeDistribution {
			result.DiskTypeDistribution[dt] += cnt
		}
	}

	// 统计所有磁盘条件都满足的机器数
	allMatchCount := 0
	for _, m := range machines {
		if err := m.UnmarshalDiskInfo(); err != nil {
			continue
		}
		allMatch := true
		for _, spec := range diskSpecs {
			disk, ok := m.Storages[spec.MountPoint]
			if !ok {
				allMatch = false
				break
			}
			// 检查类型
			if spec.DiskType != "" && spec.DiskType != "ALL" && !strings.EqualFold(disk.DiskType, spec.DiskType) {
				allMatch = false
				break
			}
			// 检查大小
			if spec.MaxSize > 0 {
				if disk.Size < spec.MinSize || disk.Size > spec.MaxSize {
					allMatch = false
					break
				}
			} else if spec.MinSize > 0 && disk.Size < spec.MinSize {
				allMatch = false
				break
			}
		}
		if allMatch {
			allMatchCount++
		}
	}
	result.AllDisksMatched = allMatchCount

	// 为了向后兼容，如果只有一个磁盘规格，填充旧的字段
	if len(diskSpecs) == 1 {
		spec := diskSpecs[0]
		if stats, ok := result.PerDiskStats[spec.MountPoint]; ok {
			result.WithMountPoint = stats.WithMountPoint
			result.WithCorrectType = stats.WithCorrectType
			result.WithEnoughSize = stats.WithEnoughSize
			result.MaxAvailableSize = stats.MaxAvailableSize
		}

		// 分析问题（单磁盘兼容模式）
		if stats := result.PerDiskStats[spec.MountPoint]; stats != nil {
			if stats.WithMountPoint == 0 {
				result.IssueType = "mount_point_not_found"
				result.IssueDetail = fmt.Sprintf("没有机器有 %s 挂载点", spec.MountPoint)
				result.Suggestion = "检查挂载点名称是否正确，或考虑使用其他挂载点"
			} else if spec.DiskType != "" && spec.DiskType != "ALL" && stats.WithCorrectType == 0 {
				result.IssueType = "disk_type_mismatch"
				result.IssueDetail = fmt.Sprintf("有 %d 台机器有 %s 挂载点，但都不是 %s 类型。类型分布: %v",
					stats.WithMountPoint, spec.MountPoint, spec.DiskType, stats.DiskTypeDistribution)
				// 找出最多的类型
				maxType := ""
				maxCount := 0
				for dt, c := range stats.DiskTypeDistribution {
					if c > maxCount {
						maxType = dt
						maxCount = c
					}
				}
				result.Suggestion = fmt.Sprintf("如果业务允许，可考虑使用 %s 类型磁盘，有 %d 台机器可用",
					maxType, maxCount)
			} else if spec.MinSize > 0 && stats.WithEnoughSize == 0 {
				result.IssueType = "disk_size_insufficient"
				result.IssueDetail = fmt.Sprintf("有 %d 台机器有 %s 挂载点，但最大容量仅 %dGB，不满足 %dGB 需求",
					stats.WithMountPoint, spec.MountPoint, stats.MaxAvailableSize, spec.MinSize)
				result.Suggestion = fmt.Sprintf("降低磁盘大小要求至 %dGB 以下，或申请新资源",
					stats.MaxAvailableSize)
			}
		}
	} else if len(diskSpecs) > 1 {
		// 多磁盘分析
		var issues []string
		for _, dr := range result.MultiDiskResults {
			if dr.FailureReason != "" {
				issues = append(issues, fmt.Sprintf("%s: %s", dr.MountPoint, dr.FailureReason))
			}
		}
		if len(issues) > 0 {
			result.IssueType = "multi_disk_issue"
			result.IssueDetail = fmt.Sprintf("多磁盘条件分析发现 %d 个问题: %s", len(issues), strings.Join(issues, "; "))
			result.Suggestion = fmt.Sprintf("共有 %d 台机器满足所有磁盘条件，建议检查各磁盘条件是否合理", allMatchCount)
		}
	}

	return result, nil
}

// ========== 标签问题分析 ==========

// LabelAnalysisResult 标签分析结果
type LabelAnalysisResult struct {
	TotalMachines     int            `json:"total_machines"`
	WithoutLabels     int            `json:"without_labels"`
	WithLabels        int            `json:"with_labels"`
	LabelDistribution map[string]int `json:"label_distribution"`
	MatchingLabels    int            `json:"matching_labels"`
	IssueType         string         `json:"issue_type,omitempty"`
	IssueDetail       string         `json:"issue_detail,omitempty"`
	AvailableLabels   []string       `json:"available_labels,omitempty"`
	Suggestion        string         `json:"suggestion,omitempty"`
	SQL               string         `json:"sql,omitempty"` // 用于调试的 SQL 语句
}

// AnalyzeLabelIssues 分析标签问题
func (t *ResourceTools) AnalyzeLabelIssues(args map[string]interface{}) (*LabelAnalysisResult, error) {
	bkCloudID := getBkCloudID(args)
	city, _ := args["city"].(string)
	requestedLabels, _ := args["requested_labels"].([]interface{})
	cpuMin, _ := args["cpu_min"].(float64)
	memMin, _ := args["mem_min"].(float64)
	diskMountPoint, _ := args["disk_mount_point"].(string)
	diskType, _ := args["disk_type"].(string)
	diskMinSize, _ := args["disk_min_size"].(float64)
	diskMaxSize, _ := args["disk_max_size"].(float64)

	// 解析 device_class 参数
	var deviceClasses []string
	if classes, ok := args["device_class"].([]interface{}); ok {
		for _, c := range classes {
			if s, ok := c.(string); ok && s != "" {
				deviceClasses = append(deviceClasses, s)
			}
		}
	}

	result := &LabelAnalysisResult{
		LabelDistribution: make(map[string]int),
	}

	// 基础查询
	baseQuery := t.db.Table(model.TbRpDetailName()).
		Where("bk_cloud_id = ? AND status = ? AND gse_agent_status_code = ?",
			bkCloudID, model.Unused, bk.GseAlive)
	if city != "" {
		baseQuery = baseQuery.Where("city = ?", city)
	}
	// 应用规格条件（device_class 和 cpu/mem 互斥）
	if len(deviceClasses) > 0 {
		baseQuery = baseQuery.Where("device_class IN ?", deviceClasses)
	} else {
		// 如果没有 device_class，则使用 cpu/mem
		if cpuMin > 0 {
			baseQuery = baseQuery.Where("cpu_num >= ?", int(cpuMin))
		}
		if memMin > 0 {
			baseQuery = baseQuery.Where("dram_cap >= ?", int(memMin))
		}
	}
	// 磁盘过滤
	if diskMountPoint != "" {
		if diskMaxSize > 0 && diskMinSize > 0 {
			// 使用范围匹配 [min, max]
			baseQuery = baseQuery.Where(model.JSONQuery("storage_device").NumRange(int(diskMinSize), int(diskMaxSize), diskMountPoint, "size"))
		} else if diskMinSize > 0 {
			// 只使用最小值 >= min
			baseQuery = baseQuery.Where(model.JSONQuery("storage_device").Gte(int(diskMinSize), diskMountPoint, "size"))
		}
		if diskType != "" {
			baseQuery = baseQuery.Where(model.JSONQuery("storage_device").Equals(diskType, diskMountPoint, "disk_type"))
		}
	}

	// 获取 SQL（用于调试）
	result.SQL = t.getSQLFromQuery(baseQuery)

	// 总数
	var total int64
	baseQuery.Count(&total)
	result.TotalMachines = int(total)

	// 无标签机器数（应用相同的规格条件）
	noLabelQuery := t.db.Table(model.TbRpDetailName()).
		Where("bk_cloud_id = ? AND status = ? AND gse_agent_status_code = ?",
			bkCloudID, model.Unused, bk.GseAlive)
	if city != "" {
		noLabelQuery = noLabelQuery.Where("city = ?", city)
	}
	// 应用规格条件（device_class 和 cpu/mem 互斥）
	if len(deviceClasses) > 0 {
		noLabelQuery = noLabelQuery.Where("device_class IN ?", deviceClasses)
	} else {
		if cpuMin > 0 {
			noLabelQuery = noLabelQuery.Where("cpu_num >= ?", int(cpuMin))
		}
		if memMin > 0 {
			noLabelQuery = noLabelQuery.Where("dram_cap >= ?", int(memMin))
		}
	}
	// 磁盘过滤
	if diskMountPoint != "" {
		if diskMaxSize > 0 && diskMinSize > 0 {
			noLabelQuery = noLabelQuery.Where(model.JSONQuery("storage_device").NumRange(int(diskMinSize), int(diskMaxSize), diskMountPoint, "size"))
		} else if diskMinSize > 0 {
			noLabelQuery = noLabelQuery.Where(model.JSONQuery("storage_device").Gte(int(diskMinSize), diskMountPoint, "size"))
		}
		if diskType != "" {
			noLabelQuery = noLabelQuery.Where(model.JSONQuery("storage_device").Equals(diskType, diskMountPoint, "disk_type"))
		}
	}
	var noLabelCount int64
	noLabelQuery.Where("JSON_TYPE(labels) = 'NULL' OR JSON_LENGTH(labels) < 1").Count(&noLabelCount)
	result.WithoutLabels = int(noLabelCount)
	result.WithLabels = result.TotalMachines - result.WithoutLabels

	// 统计标签分布（应用相同的规格条件）
	labelQuery := t.db.Table(model.TbRpDetailName()).
		Select("labels").
		Where("bk_cloud_id = ? AND status = ? AND gse_agent_status_code = ?",
			bkCloudID, model.Unused, bk.GseAlive)
	if city != "" {
		labelQuery = labelQuery.Where("city = ?", city)
	}
	// 应用规格条件（device_class 和 cpu/mem 互斥）
	if len(deviceClasses) > 0 {
		labelQuery = labelQuery.Where("device_class IN ?", deviceClasses)
	} else {
		if cpuMin > 0 {
			labelQuery = labelQuery.Where("cpu_num >= ?", int(cpuMin))
		}
		if memMin > 0 {
			labelQuery = labelQuery.Where("dram_cap >= ?", int(memMin))
		}
	}
	// 磁盘过滤
	if diskMountPoint != "" {
		if diskMaxSize > 0 && diskMinSize > 0 {
			labelQuery = labelQuery.Where(model.JSONQuery("storage_device").NumRange(int(diskMinSize), int(diskMaxSize), diskMountPoint, "size"))
		} else if diskMinSize > 0 {
			labelQuery = labelQuery.Where(model.JSONQuery("storage_device").Gte(int(diskMinSize), diskMountPoint, "size"))
		}
		if diskType != "" {
			labelQuery = labelQuery.Where(model.JSONQuery("storage_device").Equals(diskType, diskMountPoint, "disk_type"))
		}
	}
	var machines []model.TbRpDetail
	labelQuery.Where("JSON_LENGTH(labels) > 0").Find(&machines)

	for _, m := range machines {
		var labels []string
		if err := json.Unmarshal(m.Labels, &labels); err == nil {
			for _, label := range labels {
				result.LabelDistribution[label]++
			}
		}
	}

	// 提取常用标签
	for label := range result.LabelDistribution {
		result.AvailableLabels = append(result.AvailableLabels, label)
	}

	// 分析问题
	if len(requestedLabels) == 0 {
		// 无标签申请
		if result.WithoutLabels == 0 && result.WithLabels > 0 {
			result.IssueType = "no_unlabeled_resources"
			result.IssueDetail = fmt.Sprintf("申请时未指定标签，只能匹配无标签机器。当前无标签机器 0 台，但有 %d 台机器带有标签无法被匹配",
				result.WithLabels)
			result.Suggestion = fmt.Sprintf("资源池中有以下标签的机器可用: %v。请在申请参数中添加 labels 字段",
				result.AvailableLabels)
		} else if result.WithoutLabels < result.WithLabels {
			result.IssueType = "few_unlabeled_resources"
			result.IssueDetail = fmt.Sprintf("申请时未指定标签，只能匹配无标签机器。无标签机器仅 %d 台，而有 %d 台机器带标签无法匹配",
				result.WithoutLabels, result.WithLabels)
			result.Suggestion = fmt.Sprintf("如果可以使用带标签的机器，请指定标签: %v",
				result.AvailableLabels)
		}
	} else {
		// 有标签申请，检查匹配（应用相同的规格条件）
		labelStrs := make([]string, 0, len(requestedLabels))
		for _, l := range requestedLabels {
			labelStrs = append(labelStrs, l.(string))
		}

		matchQuery := t.db.Table(model.TbRpDetailName()).
			Where("bk_cloud_id = ? AND status = ? AND gse_agent_status_code = ?",
				bkCloudID, model.Unused, bk.GseAlive)
		if city != "" {
			matchQuery = matchQuery.Where("city = ?", city)
		}
		// 应用规格条件（device_class 和 cpu/mem 互斥）
		if len(deviceClasses) > 0 {
			matchQuery = matchQuery.Where("device_class IN ?", deviceClasses)
		} else {
			if cpuMin > 0 {
				matchQuery = matchQuery.Where("cpu_num >= ?", int(cpuMin))
			}
			if memMin > 0 {
				matchQuery = matchQuery.Where("dram_cap >= ?", int(memMin))
			}
		}
		var matchCount int64
		matchQuery.Where(model.JSONQuery("labels").JointOrContains(labelStrs)).Count(&matchCount)
		result.MatchingLabels = int(matchCount)

		if matchCount == 0 {
			result.IssueType = "label_not_matched"
			result.IssueDetail = fmt.Sprintf("申请的标签 %v 在资源池中没有匹配的机器",
				labelStrs)
			result.Suggestion = fmt.Sprintf("资源池中有以下标签: %v",
				result.AvailableLabels)
		}
	}

	return result, nil
}

// ========== 资源类型问题分析 ==========

// RsTypeAnalysisResult 资源类型分析结果
type RsTypeAnalysisResult struct {
	TotalMachines    int            `json:"total_machines"`
	TypeDistribution map[string]int `json:"type_distribution"`
	PublicCount      int            `json:"public_count"`
	MatchableCount   int            `json:"matchable_count"`
	SimilarTypes     []string       `json:"similar_types,omitempty"`
	IssueType        string         `json:"issue_type,omitempty"`
	IssueDetail      string         `json:"issue_detail,omitempty"`
	Suggestion       string         `json:"suggestion,omitempty"`
	SQL              string         `json:"sql,omitempty"` // 用于调试的 SQL 语句
}

// AnalyzeRsTypeIssues 分析资源类型问题
func (t *ResourceTools) AnalyzeRsTypeIssues(args map[string]interface{}) (*RsTypeAnalysisResult, error) {
	bkCloudID := getBkCloudID(args)
	city, _ := args["city"].(string)
	requestedType, _ := args["requested_type"].(string)
	if requestedType == "" {
		if rt, ok := args["resource_type"].(string); ok {
			requestedType = rt
		}
	}
	requestedType = model.NormalizeResourceType(requestedType)
	cpuMin, _ := args["cpu_min"].(float64)
	memMin, _ := args["mem_min"].(float64)
	diskMountPoint, _ := args["disk_mount_point"].(string)
	diskType, _ := args["disk_type"].(string)
	diskMinSize, _ := args["disk_min_size"].(float64)
	diskMaxSize, _ := args["disk_max_size"].(float64)

	// 解析 device_class 参数
	var deviceClasses []string
	if classes, ok := args["device_class"].([]interface{}); ok {
		for _, c := range classes {
			if s, ok := c.(string); ok && s != "" {
				deviceClasses = append(deviceClasses, s)
			}
		}
	}

	result := &RsTypeAnalysisResult{
		TypeDistribution: make(map[string]int),
	}

	// 基础查询
	baseQuery := t.db.Table(model.TbRpDetailName()).
		Where("bk_cloud_id = ? AND status = ? AND gse_agent_status_code = ?",
			bkCloudID, model.Unused, bk.GseAlive)
	if city != "" {
		baseQuery = baseQuery.Where("city = ?", city)
	}
	// 应用规格条件（device_class 和 cpu/mem 互斥）
	if len(deviceClasses) > 0 {
		baseQuery = baseQuery.Where("device_class IN ?", deviceClasses)
	} else {
		// 如果没有 device_class，则使用 cpu/mem
		if cpuMin > 0 {
			baseQuery = baseQuery.Where("cpu_num >= ?", int(cpuMin))
		}
		if memMin > 0 {
			baseQuery = baseQuery.Where("dram_cap >= ?", int(memMin))
		}
	}
	// 磁盘过滤
	if diskMountPoint != "" {
		if diskMaxSize > 0 && diskMinSize > 0 {
			// 使用范围匹配 [min, max]
			baseQuery = baseQuery.Where(model.JSONQuery("storage_device").NumRange(int(diskMinSize), int(diskMaxSize), diskMountPoint, "size"))
		} else if diskMinSize > 0 {
			// 只使用最小值 >= min
			baseQuery = baseQuery.Where(model.JSONQuery("storage_device").Gte(int(diskMinSize), diskMountPoint, "size"))
		}
		if diskType != "" {
			baseQuery = baseQuery.Where(model.JSONQuery("storage_device").Equals(diskType, diskMountPoint, "disk_type"))
		}
	}

	// 获取 SQL（用于调试）
	result.SQL = t.getSQLFromQuery(baseQuery)

	// 总数
	var total int64
	baseQuery.Count(&total)
	result.TotalMachines = int(total)

	// 按类型统计（应用相同的规格条件）
	var typeStats []struct {
		RsType string
		Count  int
	}
	query := t.db.Table(model.TbRpDetailName()).
		Select("rs_type, count(*) as count").
		Where("bk_cloud_id = ? AND status = ? AND gse_agent_status_code = ?",
			bkCloudID, model.Unused, bk.GseAlive)
	if city != "" {
		query = query.Where("city = ?", city)
	}
	// 应用规格条件（device_class 和 cpu/mem 互斥）
	if len(deviceClasses) > 0 {
		query = query.Where("device_class IN ?", deviceClasses)
	} else {
		if cpuMin > 0 {
			query = query.Where("cpu_num >= ?", int(cpuMin))
		}
		if memMin > 0 {
			query = query.Where("dram_cap >= ?", int(memMin))
		}
	}
	query.Group("rs_type").Scan(&typeStats)

	for _, s := range typeStats {
		result.TypeDistribution[s.RsType] = s.Count
		if s.RsType == model.RESOURCE_TYPE_PUBLIC {
			result.PublicCount = s.Count
		}
	}

	// 计算可匹配数量
	if requestedType == "" {
		result.MatchableCount = result.PublicCount
	} else {
		result.MatchableCount = result.PublicCount
		if count, ok := result.TypeDistribution[requestedType]; ok {
			result.MatchableCount += count
		}
	}

	// 检查类型名称一致性
	if requestedType != "" {
		targetLower := strings.ToLower(requestedType)
		for rsType := range result.TypeDistribution {
			if rsType == requestedType || rsType == model.RESOURCE_TYPE_PUBLIC {
				continue
			}
			// 检查大小写不一致
			if strings.ToLower(rsType) == targetLower {
				result.SimilarTypes = append(result.SimilarTypes, rsType)
			}
		}
	}

	// 分析问题
	if requestedType == "" && result.PublicCount == 0 && result.TotalMachines > 0 {
		result.IssueType = "no_public_resources"
		result.IssueDetail = fmt.Sprintf("申请未指定资源类型，只能匹配 PUBLIC 类型。当前 PUBLIC 机器 0 台，但有 %d 台机器被标记为其他专用类型",
			result.TotalMachines)
		result.Suggestion = fmt.Sprintf("资源池类型分布: %v。建议在申请参数中指定 resource_type",
			result.TypeDistribution)
	} else if requestedType == "" && result.PublicCount < result.TotalMachines/2 {
		otherCount := result.TotalMachines - result.PublicCount
		result.IssueType = "few_public_resources"
		result.IssueDetail = fmt.Sprintf("申请未指定资源类型，只能匹配 PUBLIC 类型。PUBLIC 机器仅 %d 台，另有 %d 台专用类型机器无法使用",
			result.PublicCount, otherCount)
		result.Suggestion = fmt.Sprintf("资源池类型分布: %v",
			result.TypeDistribution)
	} else if len(result.SimilarTypes) > 0 {
		similarCount := 0
		for _, st := range result.SimilarTypes {
			similarCount += result.TypeDistribution[st]
		}
		result.IssueType = "type_name_inconsistent"
		result.IssueDetail = fmt.Sprintf("申请的资源类型是 '%s'，但资源池中存在相似但不同的类型: %v（共 %d 台），可能是导入时类型名称不一致",
			requestedType, result.SimilarTypes, similarCount)
		result.Suggestion = "建议联系管理员统一资源类型名称（建议使用小写）"
	}

	return result, nil
}

// ========== 亲和性问题分析 ==========

// AffinityAnalysisResult 亲和性分析结果
type AffinityAnalysisResult struct {
	Summary              string                  `json:"summary"`
	AffinityType         string                  `json:"affinity_type"`
	RequestCount         int                     `json:"request_count"`
	AvailableCount       int                     `json:"available_count"`
	Tolerance            float64                 `json:"tolerance,omitempty"`
	MaxPerSubZone        int                     `json:"max_per_subzone,omitempty"`
	ResourceDistribution ResourceDistribution    `json:"resource_distribution"`
	ConstraintCheck      AffinityConstraintCheck `json:"constraint_check"`
	IssueDetail          string                  `json:"issue_detail"`
	Suggestion           string                  `json:"suggestion"`
	SQL                  string                  `json:"sql,omitempty"` // 用于调试的 SQL 语句
}

// ResourceDistribution 资源分布情况
type ResourceDistribution struct {
	SubZone          string         `json:"subzone,omitempty"`
	SubZoneIds       []string       `json:"sub_zone_ids,omitempty"`
	TotalMachines    int            `json:"total_machines"`
	BySubZone        map[string]int `json:"by_subzone,omitempty"`
	UniqueSubZones   int            `json:"unique_subzones,omitempty"`
	ByRack           map[string]int `json:"by_rack"`
	UniqueRacks      int            `json:"unique_racks"`
	ByNetDevice      map[string]int `json:"by_net_device"`
	UniqueNetDevices int            `json:"unique_net_devices"`
	// 详细列表，用于展示
	RackList      []RackInfo      `json:"rack_list"`
	NetDeviceList []NetDeviceInfo `json:"net_device_list"`
}

// RackInfo 机架信息
type RackInfo struct {
	RackID string `json:"rack_id"`
	Count  int    `json:"count"`
}

// NetDeviceInfo 网络设备信息
type NetDeviceInfo struct {
	NetDeviceID string `json:"net_device_id"`
	Count       int    `json:"count"`
}

// AffinityConstraintCheck 亲和性约束检查
type AffinityConstraintCheck struct {
	SubZonesRequired  int  `json:"subzones_required,omitempty"`
	SubZonesAvailable int  `json:"subzones_available,omitempty"`
	SubZonesSatisfied bool `json:"subzones_satisfied,omitempty"`
	RacksRequired     int  `json:"racks_required,omitempty"`
	RacksAvailable    int  `json:"racks_available,omitempty"`
	RacksSatisfied    bool `json:"racks_satisfied"`
	SwitchesRequired  int  `json:"switches_required,omitempty"`
	SwitchesAvailable int  `json:"switches_available,omitempty"`
	SwitchesSatisfied bool `json:"switches_satisfied"`
	OverallSatisfied  bool `json:"overall_satisfied"`
}

// AnalyzeAffinityIssues 分析亲和性问题
func (t *ResourceTools) AnalyzeAffinityIssues(args map[string]interface{}) (*AffinityAnalysisResult, error) {
	bkCloudID := getBkCloudID(args)
	city, _ := args["city"].(string)
	affinityType, _ := args["affinity_type"].(string)
	requestCount := int(args["request_count"].(float64))
	cpuMin, _ := args["cpu_min"].(float64)
	memMin, _ := args["mem_min"].(float64)
	tolerance, _ := args["tolerance"].(float64)

	// 处理 sub_zone_ids 数组
	var subZoneIds []string
	if ids, ok := args["sub_zone_ids"].([]interface{}); ok {
		for _, id := range ids {
			if s, ok := id.(string); ok && s != "" {
				subZoneIds = append(subZoneIds, s)
			}
		}
	}

	// 解析新增参数
	var deviceClasses []string
	if classes, ok := args["device_class"].([]interface{}); ok {
		for _, c := range classes {
			if s, ok := c.(string); ok && s != "" {
				deviceClasses = append(deviceClasses, s)
			}
		}
	}
	resourceType, _ := args["resource_type"].(string)
	resourceType = model.NormalizeResourceType(resourceType)
	labels, _ := args["labels"].([]interface{})
	diskMountPoint, _ := args["disk_mount_point"].(string)
	diskType, _ := args["disk_type"].(string)
	diskMinSize, _ := args["disk_min_size"].(float64)
	diskMaxSize, _ := args["disk_max_size"].(float64)

	// 处理排除条件
	var excludeSubZoneIds []string
	if ids, ok := args["exclude_sub_zone_ids"].([]interface{}); ok {
		for _, id := range ids {
			if s, ok := id.(string); ok && s != "" {
				excludeSubZoneIds = append(excludeSubZoneIds, s)
			}
		}
	}
	var excludeRackIds []string
	if ids, ok := args["exclude_rack_ids"].([]interface{}); ok {
		for _, id := range ids {
			if s, ok := id.(string); ok && s != "" {
				excludeRackIds = append(excludeRackIds, s)
			}
		}
	}

	result := &AffinityAnalysisResult{
		AffinityType: affinityType,
		RequestCount: requestCount,
		Tolerance:    tolerance,
		ResourceDistribution: ResourceDistribution{
			ByRack:        make(map[string]int),
			ByNetDevice:   make(map[string]int),
			BySubZone:     make(map[string]int),
			RackList:      make([]RackInfo, 0),
			NetDeviceList: make([]NetDeviceInfo, 0),
		},
	}

	// 构建基础查询（含与 apply.SearchContext.pickBase 对齐的 dedicated_biz/os_type 过滤，
	// 避免亲和性分析阶段把专属业务资源/异操作系统资源误算成候选）
	baseQuery := t.db.Table(model.TbRpDetailName()).
		Where("bk_cloud_id = ? AND status = ? AND gse_agent_status_code = ?",
			bkCloudID, model.Unused, bk.GseAlive)
	baseQuery = applyBizAndOsFilters(baseQuery, args)
	if city != "" {
		baseQuery = baseQuery.Where("city = ?", city)
	}
	// 支持多园区ID过滤
	if len(subZoneIds) > 0 {
		baseQuery = baseQuery.Where("sub_zone_id IN ?", subZoneIds)
		result.ResourceDistribution.SubZoneIds = subZoneIds
	}
	// 排除园区
	if len(excludeSubZoneIds) > 0 {
		baseQuery = baseQuery.Where("sub_zone_id NOT IN ?", excludeSubZoneIds)
	}
	// 排除机架
	if len(excludeRackIds) > 0 {
		baseQuery = baseQuery.Where("rack_id NOT IN ?", excludeRackIds)
	}
	// 机型规格过滤（如果有 device_class，则只匹配 device_class，不使用 cpu/mem）
	if len(deviceClasses) > 0 {
		baseQuery = baseQuery.Where("device_class IN ?", deviceClasses)
	} else {
		// 如果没有 device_class，则使用 CPU 和内存过滤
		if cpuMin > 0 {
			baseQuery = baseQuery.Where("cpu_num >= ?", int(cpuMin))
		}
		if memMin > 0 {
			baseQuery = baseQuery.Where("dram_cap >= ?", int(memMin))
		}
	}
	// 资源类型过滤
	if resourceType != "" {
		baseQuery = baseQuery.Where("rs_type IN (?)", []string{model.RESOURCE_TYPE_PUBLIC, resourceType})
	} else {
		baseQuery = baseQuery.Where("rs_type = ?", model.RESOURCE_TYPE_PUBLIC)
	}
	// 标签过滤
	if len(labels) > 0 {
		labelStrs := make([]string, 0, len(labels))
		for _, l := range labels {
			if s, ok := l.(string); ok {
				labelStrs = append(labelStrs, s)
			}
		}
		if len(labelStrs) > 0 {
			baseQuery = baseQuery.Where(model.JSONQuery("labels").JointOrContains(labelStrs))
		}
	} else {
		baseQuery = baseQuery.Where("JSON_TYPE(labels) = 'NULL' OR JSON_LENGTH(labels) < 1")
	}
	// 磁盘过滤
	if diskMountPoint != "" {
		if diskMaxSize > 0 && diskMinSize > 0 {
			// 使用范围匹配 [min, max]
			baseQuery = baseQuery.Where(model.JSONQuery("storage_device").NumRange(int(diskMinSize), int(diskMaxSize), diskMountPoint, "size"))
		} else if diskMinSize > 0 {
			// 只使用最小值 >= min
			baseQuery = baseQuery.Where(model.JSONQuery("storage_device").Gte(int(diskMinSize), diskMountPoint, "size"))
		}
		if diskType != "" {
			baseQuery = baseQuery.Where(model.JSONQuery("storage_device").Equals(diskType, diskMountPoint, "disk_type"))
		}
	}

	// 获取 SQL（用于调试）
	result.SQL = t.getSQLFromQuery(baseQuery.Select("id"))

	// 查询符合条件的机器
	var machines []model.TbRpDetail
	if err := baseQuery.Find(&machines).Error; err != nil {
		return nil, err
	}

	result.AvailableCount = len(machines)
	result.ResourceDistribution.TotalMachines = len(machines)

	// 统计园区、机架和交换机分布
	subZoneSet := make(map[string]bool)
	rackSet := make(map[string]bool)
	netDeviceSet := make(map[string]bool)

	for _, m := range machines {
		// 园区统计 - 使用友好格式 "城市-园区名(ID)"
		subZoneDisplay := formatSubZoneDisplay(m.City, m.SubZone, m.SubZoneID)
		result.ResourceDistribution.BySubZone[subZoneDisplay]++
		subZoneSet[subZoneDisplay] = true

		// 机架统计
		rackID := m.RackID
		if rackID == "" {
			rackID = "UNKNOWN"
		}
		result.ResourceDistribution.ByRack[rackID]++
		rackSet[rackID] = true

		// 交换机统计
		netDeviceID := m.NetDeviceID
		if netDeviceID == "" {
			netDeviceID = "UNKNOWN"
		}
		result.ResourceDistribution.ByNetDevice[netDeviceID]++
		netDeviceSet[netDeviceID] = true
	}

	result.ResourceDistribution.UniqueSubZones = len(subZoneSet)
	result.ResourceDistribution.UniqueRacks = len(rackSet)
	result.ResourceDistribution.UniqueNetDevices = len(netDeviceSet)

	// 转换为列表（方便展示）
	for rackID, count := range result.ResourceDistribution.ByRack {
		result.ResourceDistribution.RackList = append(result.ResourceDistribution.RackList,
			RackInfo{RackID: rackID, Count: count})
	}
	for netDeviceID, count := range result.ResourceDistribution.ByNetDevice {
		result.ResourceDistribution.NetDeviceList = append(result.ResourceDistribution.NetDeviceList,
			NetDeviceInfo{NetDeviceID: netDeviceID, Count: count})
	}

	// 计算容忍度相关参数（用于 CROS_SUBZONE 等亲和性）
	if tolerance > 0 {
		result.MaxPerSubZone = int(math.Ceil(float64(requestCount) * tolerance))
	}

	// 如果应用所有条件后没有找到机器，逐步放宽强约束条件进行诊断
	if result.AvailableCount == 0 {
		// 构建基础查询（只包含地域和基础状态条件）
		// 这里同样应用 dedicated_biz/os_type 过滤，否则放宽诊断会把专属池/异操作系统资源算成可用
		baseRelaxedQuery := t.db.Table(model.TbRpDetailName()).
			Where("bk_cloud_id = ? AND status = ? AND gse_agent_status_code = ?",
				bkCloudID, model.Unused, bk.GseAlive)
		baseRelaxedQuery = applyBizAndOsFilters(baseRelaxedQuery, args)
		if city != "" {
			baseRelaxedQuery = baseRelaxedQuery.Where("city = ?", city)
		}
		if len(subZoneIds) > 0 {
			baseRelaxedQuery = baseRelaxedQuery.Where("sub_zone_id IN ?", subZoneIds)
		}
		if len(excludeSubZoneIds) > 0 {
			baseRelaxedQuery = baseRelaxedQuery.Where("sub_zone_id NOT IN ?", excludeSubZoneIds)
		}
		if len(excludeRackIds) > 0 {
			baseRelaxedQuery = baseRelaxedQuery.Where("rack_id NOT IN ?", excludeRackIds)
		}

		// 逐步放宽条件，找出是哪个条件导致资源不足
		// 1. 先尝试放宽 device_class 条件（如果有 device_class）
		if len(deviceClasses) > 0 {
			relaxedQuery := baseRelaxedQuery
			if resourceType != "" {
				relaxedQuery = relaxedQuery.Where("rs_type IN (?)", []string{model.RESOURCE_TYPE_PUBLIC, resourceType})
			} else {
				relaxedQuery = relaxedQuery.Where("rs_type = ?", model.RESOURCE_TYPE_PUBLIC)
			}
			// 放宽 device_class 后，如果有 cpu/mem 条件，则应用 cpu/mem（因为 device_class 和 cpu/mem 互斥）
			if cpuMin > 0 {
				relaxedQuery = relaxedQuery.Where("cpu_num >= ?", int(cpuMin))
			}
			if memMin > 0 {
				relaxedQuery = relaxedQuery.Where("dram_cap >= ?", int(memMin))
			}
			if diskMountPoint != "" {
				if diskMaxSize > 0 && diskMinSize > 0 {
					// 使用范围匹配 [min, max]
					relaxedQuery = relaxedQuery.Where(model.JSONQuery("storage_device").NumRange(int(diskMinSize), int(diskMaxSize), diskMountPoint, "size"))
				} else if diskMinSize > 0 {
					// 只使用最小值 >= min
					relaxedQuery = relaxedQuery.Where(model.JSONQuery("storage_device").Gte(int(diskMinSize), diskMountPoint, "size"))
				}
				if diskType != "" {
					relaxedQuery = relaxedQuery.Where(model.JSONQuery("storage_device").Equals(diskType, diskMountPoint, "disk_type"))
				}
			}
			// 不应用 device_class 和 labels 过滤
			var relaxedMachines []model.TbRpDetail
			if err := relaxedQuery.Find(&relaxedMachines).Error; err == nil && len(relaxedMachines) > 0 {
				// 统计机架分布
				relaxedRackSet := make(map[string]bool)
				relaxedRackCount := make(map[string]int)
				for _, m := range relaxedMachines {
					rackID := m.RackID
					if rackID == "" {
						rackID = "UNKNOWN"
					}
					relaxedRackSet[rackID] = true
					relaxedRackCount[rackID]++
				}
				if len(relaxedRackSet) == 1 {
					for rackID, count := range relaxedRackCount {
						result.IssueDetail = fmt.Sprintf(
							"放宽机型规格(device_class)条件后找到%d台符合其他条件的机器，但这些机器全部位于同一机架(rack_id=%s)，无法满足跨机架要求",
							count, rackID)
						break
					}
					return result, nil
				} else if len(relaxedRackSet) > 0 {
					result.IssueDetail = fmt.Sprintf(
						"放宽机型规格(device_class)条件后找到%d台符合其他条件的机器，分布在%d个机架上，说明机型规格(device_class=%v)是导致资源不足的关键约束",
						len(relaxedMachines), len(relaxedRackSet), deviceClasses)
					return result, nil
				}
			}
		}

		// 2. 如果放宽 device_class 后仍找不到，尝试放宽 resource_type
		if resourceType != "" {
			relaxedQuery := baseRelaxedQuery
			// 应用规格条件（device_class 和 cpu/mem 互斥）
			if len(deviceClasses) > 0 {
				relaxedQuery = relaxedQuery.Where("device_class IN ?", deviceClasses)
			} else {
				// 如果没有 device_class，则使用 cpu/mem
				if cpuMin > 0 {
					relaxedQuery = relaxedQuery.Where("cpu_num >= ?", int(cpuMin))
				}
				if memMin > 0 {
					relaxedQuery = relaxedQuery.Where("dram_cap >= ?", int(memMin))
				}
			}
			if diskMountPoint != "" {
				if diskMaxSize > 0 && diskMinSize > 0 {
					// 使用范围匹配 [min, max]
					relaxedQuery = relaxedQuery.Where(model.JSONQuery("storage_device").NumRange(int(diskMinSize), int(diskMaxSize), diskMountPoint, "size"))
				} else if diskMinSize > 0 {
					// 只使用最小值 >= min
					relaxedQuery = relaxedQuery.Where(model.JSONQuery("storage_device").Gte(int(diskMinSize), diskMountPoint, "size"))
				}
				if diskType != "" {
					relaxedQuery = relaxedQuery.Where(model.JSONQuery("storage_device").Equals(diskType, diskMountPoint, "disk_type"))
				}
			}
			// 不应用 resource_type 和 labels 过滤
			var relaxedMachines []model.TbRpDetail
			if err := relaxedQuery.Find(&relaxedMachines).Error; err == nil && len(relaxedMachines) > 0 {
				relaxedRackSet := make(map[string]bool)
				relaxedRackCount := make(map[string]int)
				for _, m := range relaxedMachines {
					rackID := m.RackID
					if rackID == "" {
						rackID = "UNKNOWN"
					}
					relaxedRackSet[rackID] = true
					relaxedRackCount[rackID]++
				}
				if len(relaxedRackSet) == 1 {
					for rackID, count := range relaxedRackCount {
						result.IssueDetail = fmt.Sprintf(
							"放宽资源类型(rs_type=%s)条件后找到%d台符合其他条件的机器，但这些机器全部位于同一机架(rack_id=%s)，无法满足跨机架要求",
							resourceType, count, rackID)
						break
					}
					return result, nil
				} else if len(relaxedRackSet) > 0 {
					result.IssueDetail = fmt.Sprintf(
						"放宽资源类型(rs_type=%s)条件后找到%d台符合其他条件的机器，分布在%d个机架上，说明资源类型是导致资源不足的关键约束",
						resourceType, len(relaxedMachines), len(relaxedRackSet))
					return result, nil
				}
			}
		}

		// 3. 如果放宽 resource_type 后仍找不到，尝试放宽磁盘条件
		if diskMountPoint != "" {
			relaxedQuery := baseRelaxedQuery
			// 应用规格条件（device_class 和 cpu/mem 互斥）
			if len(deviceClasses) > 0 {
				relaxedQuery = relaxedQuery.Where("device_class IN ?", deviceClasses)
			} else {
				// 如果没有 device_class，则使用 cpu/mem
				if cpuMin > 0 {
					relaxedQuery = relaxedQuery.Where("cpu_num >= ?", int(cpuMin))
				}
				if memMin > 0 {
					relaxedQuery = relaxedQuery.Where("dram_cap >= ?", int(memMin))
				}
			}
			if resourceType != "" {
				relaxedQuery = relaxedQuery.Where("rs_type IN (?)", []string{model.RESOURCE_TYPE_PUBLIC, resourceType})
			} else {
				relaxedQuery = relaxedQuery.Where("rs_type = ?", model.RESOURCE_TYPE_PUBLIC)
			}
			// 不应用磁盘和 labels 过滤
			var relaxedMachines []model.TbRpDetail
			if err := relaxedQuery.Find(&relaxedMachines).Error; err == nil && len(relaxedMachines) > 0 {
				relaxedRackSet := make(map[string]bool)
				relaxedRackCount := make(map[string]int)
				for _, m := range relaxedMachines {
					rackID := m.RackID
					if rackID == "" {
						rackID = "UNKNOWN"
					}
					relaxedRackSet[rackID] = true
					relaxedRackCount[rackID]++
				}
				if len(relaxedRackSet) == 1 {
					for rackID, count := range relaxedRackCount {
						result.IssueDetail = fmt.Sprintf(
							"放宽磁盘条件(挂载点=%s)后找到%d台符合其他条件的机器，但这些机器全部位于同一机架(rack_id=%s)，无法满足跨机架要求",
							diskMountPoint, count, rackID)
						break
					}
					return result, nil
				} else if len(relaxedRackSet) > 0 {
					result.IssueDetail = fmt.Sprintf(
						"放宽磁盘条件(挂载点=%s)后找到%d台符合其他条件的机器，分布在%d个机架上，说明磁盘条件是导致资源不足的关键约束",
						diskMountPoint, len(relaxedMachines), len(relaxedRackSet))
					return result, nil
				}
			}
		}

		// 4. 最后尝试放宽标签条件
		if len(labels) > 0 {
			relaxedQuery := baseRelaxedQuery
			// 应用规格条件（device_class 和 cpu/mem 互斥）
			if len(deviceClasses) > 0 {
				relaxedQuery = relaxedQuery.Where("device_class IN ?", deviceClasses)
			} else {
				// 如果没有 device_class，则使用 cpu/mem
				if cpuMin > 0 {
					relaxedQuery = relaxedQuery.Where("cpu_num >= ?", int(cpuMin))
				}
				if memMin > 0 {
					relaxedQuery = relaxedQuery.Where("dram_cap >= ?", int(memMin))
				}
			}
			if resourceType != "" {
				relaxedQuery = relaxedQuery.Where("rs_type IN (?)", []string{model.RESOURCE_TYPE_PUBLIC, resourceType})
			} else {
				relaxedQuery = relaxedQuery.Where("rs_type = ?", model.RESOURCE_TYPE_PUBLIC)
			}
			if diskMountPoint != "" {
				if diskMaxSize > 0 && diskMinSize > 0 {
					// 使用范围匹配 [min, max]
					relaxedQuery = relaxedQuery.Where(model.JSONQuery("storage_device").NumRange(int(diskMinSize), int(diskMaxSize), diskMountPoint, "size"))
				} else if diskMinSize > 0 {
					// 只使用最小值 >= min
					relaxedQuery = relaxedQuery.Where(model.JSONQuery("storage_device").Gte(int(diskMinSize), diskMountPoint, "size"))
				}
				if diskType != "" {
					relaxedQuery = relaxedQuery.Where(model.JSONQuery("storage_device").Equals(diskType, diskMountPoint, "disk_type"))
				}
			}
			// 不应用 labels 过滤
			var relaxedMachines []model.TbRpDetail
			if err := relaxedQuery.Find(&relaxedMachines).Error; err == nil && len(relaxedMachines) > 0 {
				relaxedRackSet := make(map[string]bool)
				relaxedRackCount := make(map[string]int)
				for _, m := range relaxedMachines {
					rackID := m.RackID
					if rackID == "" {
						rackID = "UNKNOWN"
					}
					relaxedRackSet[rackID] = true
					relaxedRackCount[rackID]++
				}
				if len(relaxedRackSet) == 1 {
					for rackID, count := range relaxedRackCount {
						result.IssueDetail = fmt.Sprintf(
							"放宽标签条件后找到%d台符合其他条件的机器，但这些机器全部位于同一机架(rack_id=%s)，无法满足跨机架要求",
							count, rackID)
						break
					}
					return result, nil
				} else if len(relaxedRackSet) > 0 {
					result.IssueDetail = fmt.Sprintf(
						"放宽标签条件后找到%d台符合其他条件的机器，分布在%d个机架上，说明标签条件是导致资源不足的关键约束",
						len(relaxedMachines), len(relaxedRackSet))
					return result, nil
				}
			}
		}
	}

	// 根据亲和性类型检查约束
	result.ConstraintCheck = t.checkAffinityConstraintEx(affinityType, requestCount, tolerance,
		result.ResourceDistribution.UniqueSubZones,
		result.ResourceDistribution.UniqueRacks,
		result.ResourceDistribution.UniqueNetDevices)

	// 生成分析结果
	if result.AvailableCount < requestCount {
		result.Summary = fmt.Sprintf("资源数量不足：需要 %d 台，但仅有 %d 台符合所有条件（机型、规格、磁盘、标签等）",
			requestCount, result.AvailableCount)
		// 如果没有设置 IssueDetail（即没有放宽条件查询的情况），使用默认描述
		if result.IssueDetail == "" {
			result.IssueDetail = "符合规格条件的资源数量本身就不足，与亲和性无关"
		}
		result.Suggestion = "需要在该区域补充符合规格的资源"
	} else if !result.ConstraintCheck.OverallSatisfied {
		// 资源数量够，但亲和性不满足
		issueDetail := t.generateAffinityIssueDetailEx(affinityType, requestCount, tolerance, result)
		// 如果都在同一机架，Summary 更明确地说明
		if result.ConstraintCheck.RacksAvailable == 1 && result.AvailableCount >= requestCount {
			result.Summary = fmt.Sprintf("找到%d台符合所有条件的机器，但这些机器全部位于同一机架，无法满足%s跨机架要求",
				result.AvailableCount, affinityType)
		} else {
			result.Summary = fmt.Sprintf("资源数量足够（%d台），但因%s亲和性分布不足无法满足：%s",
				result.AvailableCount, affinityType, issueDetail)
		}
		result.IssueDetail = issueDetail
		result.Suggestion = t.generateAffinitySuggestionEx(affinityType, requestCount, tolerance, result)
	} else {
		result.Summary = fmt.Sprintf("资源充足且分布满足亲和性要求: %d 台可用，%d 个园区，%d 个机架，%d 个交换机",
			result.AvailableCount, result.ResourceDistribution.UniqueSubZones,
			result.ResourceDistribution.UniqueRacks, result.ResourceDistribution.UniqueNetDevices)
	}

	return result, nil
}

// checkAffinityConstraint 检查亲和性约束
func (t *ResourceTools) checkAffinityConstraint(affinityType string, requestCount, uniqueRacks, uniqueNetDevices int) AffinityConstraintCheck {
	check := AffinityConstraintCheck{}

	switch affinityType {
	case "SAME_SUBZONE_CROSS_SWTICH":
		// 同城同园区跨机架跨交换机：需要每台机器在不同机架且不同交换机上
		check.RacksRequired = requestCount
		check.RacksAvailable = uniqueRacks
		check.RacksSatisfied = uniqueRacks >= requestCount
		check.SwitchesRequired = requestCount
		check.SwitchesAvailable = uniqueNetDevices
		check.SwitchesSatisfied = uniqueNetDevices >= requestCount
		check.OverallSatisfied = check.RacksSatisfied && check.SwitchesSatisfied

	case "CROSS_RACK":
		// 跨机架：需要每台机器在不同机架上
		check.RacksRequired = requestCount
		check.RacksAvailable = uniqueRacks
		check.RacksSatisfied = uniqueRacks >= requestCount
		check.SwitchesRequired = 0
		check.SwitchesSatisfied = true
		check.OverallSatisfied = check.RacksSatisfied

	case "SAME_SUBZONE":
		// 同城同园区：不要求跨机架跨交换机
		check.RacksSatisfied = true
		check.SwitchesSatisfied = true
		check.OverallSatisfied = true

	case "CROS_SUBZONE", "CROSS_SUBZONE_STRONG":
		// 跨园区：不在此工具处理，需要结合多园区数据
		check.RacksSatisfied = true
		check.SwitchesSatisfied = true
		check.OverallSatisfied = true

	default:
		// 其他类型，假设同时要求跨机架和跨交换机
		check.RacksRequired = requestCount
		check.RacksAvailable = uniqueRacks
		check.RacksSatisfied = uniqueRacks >= requestCount
		check.SwitchesRequired = requestCount
		check.SwitchesAvailable = uniqueNetDevices
		check.SwitchesSatisfied = uniqueNetDevices >= requestCount
		check.OverallSatisfied = check.RacksSatisfied && check.SwitchesSatisfied
	}

	return check
}

// checkAffinityConstraintEx 检查亲和性约束（扩展版，支持容忍度和园区检查）
func (t *ResourceTools) checkAffinityConstraintEx(affinityType string, requestCount int, tolerance float64,
	uniqueSubZones, uniqueRacks, uniqueNetDevices int) AffinityConstraintCheck {
	check := AffinityConstraintCheck{}

	switch affinityType {
	case "SAME_SUBZONE_CROSS_SWTICH":
		check.RacksRequired = requestCount
		check.RacksAvailable = uniqueRacks
		check.RacksSatisfied = uniqueRacks >= requestCount
		check.SwitchesRequired = requestCount
		check.SwitchesAvailable = uniqueNetDevices
		check.SwitchesSatisfied = uniqueNetDevices >= requestCount
		check.OverallSatisfied = check.RacksSatisfied && check.SwitchesSatisfied

	case "CROSS_RACK":
		check.RacksRequired = requestCount
		check.RacksAvailable = uniqueRacks
		check.RacksSatisfied = uniqueRacks >= requestCount
		check.SwitchesRequired = 0
		check.SwitchesSatisfied = true
		check.OverallSatisfied = check.RacksSatisfied

	case "SAME_SUBZONE":
		check.RacksSatisfied = true
		check.SwitchesSatisfied = true
		check.OverallSatisfied = true

	case "CROS_SUBZONE":
		// 同城跨园区：需要根据容忍度检查园区数量
		var minSubZones int
		if tolerance == 0 {
			minSubZones = requestCount // 容忍度为0，需要每个机器在不同园区
		} else {
			minSubZones = int(math.Ceil(1.0 / tolerance)) // 最少园区数
		}
		check.SubZonesRequired = minSubZones
		check.SubZonesAvailable = uniqueSubZones
		check.SubZonesSatisfied = uniqueSubZones >= minSubZones
		check.RacksSatisfied = true
		check.SwitchesSatisfied = true
		check.OverallSatisfied = check.SubZonesSatisfied

	case "CROSS_SUBZONE_STRONG":
		// 跨园区(强)：至少3个园区，园区容忍度1/3
		check.SubZonesRequired = 3
		check.SubZonesAvailable = uniqueSubZones
		check.SubZonesSatisfied = uniqueSubZones >= 3
		check.RacksRequired = 2 // 每园区至少2机架
		check.RacksAvailable = uniqueRacks
		check.RacksSatisfied = uniqueRacks >= 2*uniqueSubZones // 简化检查
		check.SwitchesSatisfied = true
		check.OverallSatisfied = check.SubZonesSatisfied && uniqueSubZones >= 3

	case "CROSS_SUBZONE_WEAK":
		// 跨园区(弱)：至少2个园区，园区容忍度1/2
		check.SubZonesRequired = 2
		check.SubZonesAvailable = uniqueSubZones
		check.SubZonesSatisfied = uniqueSubZones >= 2
		check.RacksRequired = 2 // 每园区至少2机架
		check.RacksAvailable = uniqueRacks
		check.RacksSatisfied = uniqueRacks >= 2*uniqueSubZones
		check.SwitchesSatisfied = true
		check.OverallSatisfied = check.SubZonesSatisfied && uniqueSubZones >= 2

	default:
		check.RacksSatisfied = true
		check.SwitchesSatisfied = true
		check.OverallSatisfied = true
	}

	return check
}

// generateAffinityIssueDetailEx 生成亲和性问题详情（扩展版）
func (t *ResourceTools) generateAffinityIssueDetailEx(affinityType string, requestCount int, tolerance float64, result *AffinityAnalysisResult) string {
	check := result.ConstraintCheck
	dist := result.ResourceDistribution

	var details []string

	if !check.SubZonesSatisfied {
		details = append(details, fmt.Sprintf(
			"需要至少 %d 个园区（容忍度 %.2f），当前仅有 %d 个园区。园区分布: %v",
			check.SubZonesRequired, tolerance, check.SubZonesAvailable, dist.BySubZone))
	}

	if !check.RacksSatisfied {
		if check.RacksAvailable == 1 {
			// 所有机器在同一机架
			for rackID, count := range dist.ByRack {
				details = append(details, fmt.Sprintf(
					"实际找到%d台符合所有条件的机器，但这些机器全部位于同一机架(rack_id=%s)，无法满足跨机架要求(需要%d个不同机架)",
					count, rackID, check.RacksRequired))
				break
			}
		} else {
			details = append(details, fmt.Sprintf(
				"需要 %d 个不同机架，当前仅有 %d 个机架。机架分布: %v",
				check.RacksRequired, check.RacksAvailable, dist.ByRack))
		}
	}

	if !check.SwitchesSatisfied {
		if check.SwitchesAvailable == 1 {
			// 所有机器在同一交换机
			for switchID, count := range dist.ByNetDevice {
				details = append(details, fmt.Sprintf(
					"实际找到%d台符合所有条件的机器，但这些机器全部位于同一交换机(net_device_id=%s)，无法满足跨交换机要求(需要%d个不同交换机)",
					count, switchID, check.SwitchesRequired))
				break
			}
		} else {
			details = append(details, fmt.Sprintf(
				"需要 %d 个不同交换机，当前仅有 %d 个交换机。交换机分布: %v",
				check.SwitchesRequired, check.SwitchesAvailable, dist.ByNetDevice))
		}
	}

	return strings.Join(details, "; ")
}

// generateAffinitySuggestionEx 生成亲和性建议（扩展版）
func (t *ResourceTools) generateAffinitySuggestionEx(affinityType string, requestCount int, tolerance float64, result *AffinityAnalysisResult) string {
	check := result.ConstraintCheck

	var suggestions []string

	if !check.SubZonesSatisfied {
		needMore := check.SubZonesRequired - check.SubZonesAvailable
		suggestions = append(suggestions, fmt.Sprintf(
			"需要在该城市补充至少 %d 个新园区上的资源", needMore))
	}

	if !check.RacksSatisfied {
		needMore := check.RacksRequired - check.RacksAvailable
		suggestions = append(suggestions, fmt.Sprintf(
			"需要在该园区补充至少 %d 个新机架上的资源", needMore))
	}

	if !check.SwitchesSatisfied {
		needMore := check.SwitchesRequired - check.SwitchesAvailable
		suggestions = append(suggestions, fmt.Sprintf(
			"需要在该园区补充至少 %d 个新交换机上的资源", needMore))
	}

	if len(suggestions) == 0 {
		return "资源分布满足亲和性要求"
	}

	return strings.Join(suggestions, "; ")
}

// generateAffinityIssueDetail 生成亲和性问题详情
func (t *ResourceTools) generateAffinityIssueDetail(affinityType string, requestCount int, result *AffinityAnalysisResult) string {
	check := result.ConstraintCheck
	dist := result.ResourceDistribution

	var details []string

	if !check.RacksSatisfied {
		details = append(details, fmt.Sprintf(
			"需要 %d 个不同机架，当前仅有 %d 个机架。机架分布: %v",
			check.RacksRequired, check.RacksAvailable, dist.ByRack))
	}

	if !check.SwitchesSatisfied {
		details = append(details, fmt.Sprintf(
			"需要 %d 个不同交换机，当前仅有 %d 个交换机。交换机分布: %v",
			check.SwitchesRequired, check.SwitchesAvailable, dist.ByNetDevice))
	}

	return strings.Join(details, "; ")
}

// generateAffinitySuggestion 生成亲和性建议
func (t *ResourceTools) generateAffinitySuggestion(affinityType string, requestCount int, result *AffinityAnalysisResult) string {
	check := result.ConstraintCheck

	var suggestions []string

	if !check.RacksSatisfied {
		needMore := check.RacksRequired - check.RacksAvailable
		suggestions = append(suggestions, fmt.Sprintf(
			"需要在该园区补充至少 %d 个新机架上的资源", needMore))
	}

	if !check.SwitchesSatisfied {
		needMore := check.SwitchesRequired - check.SwitchesAvailable
		suggestions = append(suggestions, fmt.Sprintf(
			"需要在该园区补充至少 %d 个新交换机上的资源", needMore))
	}

	if len(suggestions) == 0 {
		return "资源分布满足亲和性要求"
	}

	return strings.Join(suggestions, "; ")
}

// ========== 验证预测 ==========

// VerifyPredictionResult 验证预测结果
type VerifyPredictionResult struct {
	ActualCount     int               `json:"actual_count"`                // Actual resource count after applying conditions
	QueryUsed       string            `json:"query_used"`                  // Description of query conditions used
	SQL             string            `json:"sql,omitempty"`               // SQL for debugging
	Verified        bool              `json:"verified"`                    // Whether the verification passed (actual_count >= request_count)
	RequestCount    int               `json:"request_count,omitempty"`     // Requested count for comparison
	SuggestionType  string            `json:"suggestion_type,omitempty"`   // Type of suggestion being verified
	Reason          string            `json:"reason,omitempty"`            // Reason for verification result
	Confidence      string            `json:"confidence,omitempty"`        // Confidence level: high/medium/low
	DiskMatchDetail []DiskMatchResult `json:"disk_match_detail,omitempty"` // Detailed disk match results for multi-disk scenarios
}

// VerifyPrediction 验证预测，支持多磁盘条件验证
func (t *ResourceTools) VerifyPrediction(args map[string]interface{}) (*VerifyPredictionResult, error) {
	bkCloudID := getBkCloudID(args)
	city, _ := args["city"].(string)
	cpuMin, _ := args["cpu_min"].(float64)
	memMin, _ := args["mem_min"].(float64)
	resourceType, _ := args["resource_type"].(string)
	resourceType = model.NormalizeResourceType(resourceType)
	requestCount, _ := args["request_count"].(float64)
	suggestionType, _ := args["suggestion_type"].(string)

	// Parse disk specs (support both new and old format)
	diskSpecs := parseDiskSpecs(args)

	// 解析 device_class 参数
	var deviceClasses []string
	if classes, ok := args["device_class"].([]interface{}); ok {
		for _, c := range classes {
			if s, ok := c.(string); ok && s != "" {
				deviceClasses = append(deviceClasses, s)
			}
		}
	}

	// 解析 labels 参数
	var labels []string
	if labelList, ok := args["labels"].([]interface{}); ok {
		for _, l := range labelList {
			if s, ok := l.(string); ok && s != "" {
				labels = append(labels, s)
			}
		}
	}

	query := t.db.Table(model.TbRpDetailName()).
		Where("bk_cloud_id = ? AND status = ? AND gse_agent_status_code = ?",
			bkCloudID, model.Unused, bk.GseAlive)

	queryDesc := fmt.Sprintf("云区域=%d, 状态=unused", bkCloudID)

	if city != "" {
		query = query.Where("city = ?", city)
		queryDesc += fmt.Sprintf(", 城市=%s", city)
	}

	// 应用规格条件（device_class 和 cpu/mem 互斥）
	if len(deviceClasses) > 0 {
		query = query.Where("device_class IN ?", deviceClasses)
		queryDesc += fmt.Sprintf(", 机型规格=%v", deviceClasses)
	} else {
		// 如果没有 device_class，则使用 cpu/mem
		if cpuMin > 0 {
			query = query.Where("cpu_num >= ?", int(cpuMin))
			queryDesc += fmt.Sprintf(", CPU>=%d", int(cpuMin))
		}
		if memMin > 0 {
			query = query.Where("dram_cap >= ?", int(memMin))
			queryDesc += fmt.Sprintf(", 内存>=%d", int(memMin))
		}
	}

	// 标签过滤
	if len(labels) > 0 {
		for _, label := range labels {
			query = query.Where(model.JSONQuery("labels").Contains([]string{label}))
		}
		queryDesc += fmt.Sprintf(", 标签=%v", labels)
	}

	// 多磁盘过滤
	if len(diskSpecs) > 0 {
		query = buildDiskConditions(query, diskSpecs)
		for _, spec := range diskSpecs {
			queryDesc += fmt.Sprintf(", 磁盘(%s", spec.MountPoint)
			if spec.DiskType != "" && spec.DiskType != "ALL" {
				queryDesc += fmt.Sprintf(" 类型=%s", spec.DiskType)
			}
			if spec.MaxSize > 0 {
				queryDesc += fmt.Sprintf(" [%d-%d]GB", spec.MinSize, spec.MaxSize)
			} else if spec.MinSize > 0 {
				queryDesc += fmt.Sprintf(" >=%dGB", spec.MinSize)
			}
			queryDesc += ")"
		}
	}

	if resourceType != "" {
		query = query.Where("rs_type IN (?)", []string{model.RESOURCE_TYPE_PUBLIC, resourceType})
		queryDesc += fmt.Sprintf(", 类型=PUBLIC或%s", resourceType)
	} else {
		query = query.Where("rs_type = ?", model.RESOURCE_TYPE_PUBLIC)
		queryDesc += ", 类型=PUBLIC"
	}

	// 获取 SQL（用于调试）
	sql := t.getSQLFromQuery(query)

	var count int64
	query.Count(&count)

	result := &VerifyPredictionResult{
		ActualCount:    int(count),
		QueryUsed:      queryDesc,
		SQL:            sql,
		RequestCount:   int(requestCount),
		SuggestionType: suggestionType,
	}

	// Determine verification result
	if requestCount > 0 {
		result.Verified = result.ActualCount >= result.RequestCount
		if result.Verified {
			result.Reason = fmt.Sprintf("可用资源数(%d)满足申请需求(%d)", result.ActualCount, result.RequestCount)
			result.Confidence = "high"
		} else {
			result.Reason = fmt.Sprintf("可用资源数(%d)不足，需要%d台", result.ActualCount, result.RequestCount)
			result.Confidence = "high"
		}
	} else {
		// No request count provided, just return the actual count
		result.Verified = result.ActualCount > 0
		result.Reason = fmt.Sprintf("查询到%d台可用资源", result.ActualCount)
		result.Confidence = "medium"
	}

	// Analyze disk match details for multi-disk scenarios
	if len(diskSpecs) > 0 {
		baseQuery := t.db.Table(model.TbRpDetailName()).
			Where("bk_cloud_id = ? AND status = ? AND gse_agent_status_code = ?",
				bkCloudID, model.Unused, bk.GseAlive)
		if city != "" {
			baseQuery = baseQuery.Where("city = ?", city)
		}
		if len(deviceClasses) > 0 {
			baseQuery = baseQuery.Where("device_class IN ?", deviceClasses)
		} else {
			if cpuMin > 0 {
				baseQuery = baseQuery.Where("cpu_num >= ?", int(cpuMin))
			}
			if memMin > 0 {
				baseQuery = baseQuery.Where("dram_cap >= ?", int(memMin))
			}
		}
		if resourceType != "" {
			baseQuery = baseQuery.Where("rs_type IN (?)", []string{model.RESOURCE_TYPE_PUBLIC, resourceType})
		} else {
			baseQuery = baseQuery.Where("rs_type = ?", model.RESOURCE_TYPE_PUBLIC)
		}
		result.DiskMatchDetail = t.analyzeDiskSpecMatches(baseQuery, diskSpecs)

		// Adjust confidence based on disk match analysis
		anyDiskIssue := false
		for _, dr := range result.DiskMatchDetail {
			if dr.FailureReason != "" {
				anyDiskIssue = true
				break
			}
		}
		if anyDiskIssue && !result.Verified {
			result.Confidence = "high" // We know exactly why it failed
		}
	}

	return result, nil
}

// ========== 自定义 SQL 查询 ==========

// CustomQueryResult 自定义查询结果
type CustomQueryResult struct {
	Description  string        `json:"description"`             // 查询目的说明
	SQL          string        `json:"sql"`                     // 实际执行的 SQL
	SQLRewritten bool          `json:"sql_rewritten,omitempty"` // 是否纠正过 JSON Path
	Warning      string        `json:"warning,omitempty"`
	RowCount     int           `json:"row_count"` // 返回的行数
	Columns      []string      `json:"columns"`   // 列名
	Rows         []interface{} `json:"rows"`      // 查询结果（每行是一个 map）
	Error        string        `json:"error,omitempty"`
}

// ExecuteCustomQuery 执行自定义 SQL 查询（仅允许 SELECT，用于验证推测）
func (t *ResourceTools) ExecuteCustomQuery(args map[string]interface{}) (*CustomQueryResult, error) {
	sql, _ := args["sql"].(string)
	description, _ := args["description"].(string)

	result := &CustomQueryResult{
		Description: description,
		SQL:         sql,
	}

	if rewritten, changed := rewriteStorageDeviceJSONExtract(sql); changed {
		sql = rewritten
		result.SQL = sql
		result.SQLRewritten = true
		result.Warning = `storage_device 的 JSON_EXTRACT 路径已纠正。挂载点含斜杠必须写成 $."/data".size，不能写成 /data/size 或 $./data.size`
	}

	// 安全检查：只允许 SELECT 查询
	sqlUpper := strings.TrimSpace(strings.ToUpper(sql))
	if !strings.HasPrefix(sqlUpper, "SELECT") {
		result.Error = "只允许执行 SELECT 查询"
		return result, fmt.Errorf("只允许执行 SELECT 查询")
	}

	// 安全检查：必须包含 tb_rp_detail 表
	if !strings.Contains(strings.ToUpper(sql), strings.ToUpper(model.TbRpDetailName())) {
		result.Error = fmt.Sprintf("只能查询 %s 表", model.TbRpDetailName())
		return result, fmt.Errorf("只能查询 %s 表", model.TbRpDetailName())
	}

	// 安全检查：禁止危险操作
	dangerousKeywords := []string{"DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE", "EXEC", "EXECUTE"}
	for _, keyword := range dangerousKeywords {
		if strings.Contains(sqlUpper, keyword) {
			result.Error = fmt.Sprintf("禁止使用 %s 操作", keyword)
			return result, fmt.Errorf("禁止使用 %s 操作", keyword)
		}
	}

	// 限制结果数量：如果 SQL 中没有 LIMIT，自动添加 LIMIT 100
	if !strings.Contains(sqlUpper, "LIMIT") {
		sql = sql + " LIMIT 100"
		result.SQL = sql
	}

	// 执行查询
	rows, err := t.db.Raw(sql).Rows()
	if err != nil {
		result.Error = err.Error()
		return result, fmt.Errorf("SQL 执行失败: %v", err)
	}
	defer rows.Close()

	// 获取列名
	columns, err := rows.Columns()
	if err != nil {
		result.Error = err.Error()
		return result, fmt.Errorf("获取列名失败: %v", err)
	}
	result.Columns = columns

	// 读取数据
	var allRows []interface{}
	for rows.Next() {
		// 创建值的切片
		values := make([]interface{}, len(columns))
		valuePtrs := make([]interface{}, len(columns))
		for i := range values {
			valuePtrs[i] = &values[i]
		}

		if err := rows.Scan(valuePtrs...); err != nil {
			result.Error = err.Error()
			return result, fmt.Errorf("读取数据失败: %v", err)
		}

		// 转换为 map
		rowMap := make(map[string]interface{})
		for i, col := range columns {
			val := values[i]
			// 处理 []byte 类型（如 JSON）
			if b, ok := val.([]byte); ok {
				val = string(b)
			}
			rowMap[col] = val
		}
		allRows = append(allRows, rowMap)
	}

	filteredCols, filteredRows, stripped := stripIrrelevantColumns(columns, allRows)
	if stripped {
		result.Columns = filteredCols
		result.Rows = filteredRows
	} else {
		result.Columns = columns
		result.Rows = allRows
	}
	if stripped || sqlMentionsIrrelevantColumns(sql) {
		result.Warning = appendAnalysisWarning(result.Warning, analysisIrrelevantWarning)
	}
	result.RowCount = len(allRows)

	return result, nil
}

// ========== 资源类型推测相关辅助函数 ==========

// isResourceTypeSupported 检查资源类型是否支持推测
func isResourceTypeSupported(resourceType string) bool {
	return supportedResourceTypes[resourceType]
}

// getAlternativeResourceType 获取替代资源类型（向后兼容）
func getAlternativeResourceType(currentType string) (string, bool) {
	alternatives, exists := globalResourceTypeRegistry.GetAlternativeResourceTypes(currentType)
	if !exists || len(alternatives) == 0 {
		return "", false
	}
	// 返回第一个替代类型以保持向后兼容
	return alternatives[0], true
}

// validateResourceTypeInferenceParams 验证资源类型推测参数
func validateResourceTypeInferenceParams(args map[string]interface{}) error {
	// 检查必需参数
	currentType, ok := args["current_resource_type"].(string)
	if !ok || currentType == "" {
		return fmt.Errorf("current_resource_type is required and must be a non-empty string")
	}

	// 检查资源类型是否支持
	if !isResourceTypeSupported(currentType) {
		return fmt.Errorf("resource type '%s' is not supported for inference. Supported types: %v",
			currentType, []string{ResourceTypeMySQL, ResourceTypeTenDBCluster})
	}

	// 检查云区域ID
	if _, ok := args["bk_cloud_id"]; !ok {
		return fmt.Errorf("bk_cloud_id is required")
	}

	// 验证 bk_cloud_id 类型和值
	switch v := args["bk_cloud_id"].(type) {
	case int:
		if v < 0 {
			return fmt.Errorf("bk_cloud_id must be non-negative, got: %d", v)
		}
	case int64:
		if v < 0 {
			return fmt.Errorf("bk_cloud_id must be non-negative, got: %d", v)
		}
	case float64:
		// 允许 float64，但必须是整数值且非负
		if v != float64(int(v)) {
			return fmt.Errorf("bk_cloud_id must be an integer value, got: %f", v)
		}
		if v < 0 {
			return fmt.Errorf("bk_cloud_id must be non-negative, got: %f", v)
		}
	default:
		return fmt.Errorf("bk_cloud_id must be an integer type (int, int64, or float64), got: %T", v)
	}

	// 验证可选参数的有效性
	if city, ok := args["city"].(string); ok && city != "" {
		if len(city) > 100 {
			return fmt.Errorf("city name too long, maximum 100 characters")
		}
	}

	// 验证园区ID列表
	if subZoneIds, ok := args["sub_zone_ids"].([]interface{}); ok {
		if len(subZoneIds) > 50 {
			return fmt.Errorf("too many sub_zone_ids, maximum 50 allowed")
		}
		for i, id := range subZoneIds {
			if s, ok := id.(string); !ok || s == "" {
				return fmt.Errorf("sub_zone_ids[%d] must be a non-empty string", i)
			} else if len(s) > 200 {
				return fmt.Errorf("sub_zone_ids[%d] too long, maximum 200 characters", i)
			}
		}
	}

	// 验证CPU范围
	if cpuMin, ok := args["cpu_min"].(float64); ok {
		if cpuMin < 0 || cpuMin > 1000 {
			return fmt.Errorf("cpu_min must be between 0 and 1000")
		}
	}
	if cpuMax, ok := args["cpu_max"].(float64); ok {
		if cpuMax < 0 || cpuMax > 1000 {
			return fmt.Errorf("cpu_max must be between 0 and 1000")
		}
	}
	if cpuMin, hasMin := args["cpu_min"].(float64); hasMin {
		if cpuMax, hasMax := args["cpu_max"].(float64); hasMax && cpuMin > cpuMax {
			return fmt.Errorf("cpu_min (%v) cannot be greater than cpu_max (%v)", cpuMin, cpuMax)
		}
	}

	// 验证内存范围
	if memMin, ok := args["mem_min"].(float64); ok {
		if memMin < 0 || memMin > 10000000 { // 10TB in MB
			return fmt.Errorf("mem_min must be between 0 and 10000000 MB")
		}
	}
	if memMax, ok := args["mem_max"].(float64); ok {
		if memMax < 0 || memMax > 10000000 {
			return fmt.Errorf("mem_max must be between 0 and 10000000 MB")
		}
	}
	if memMin, hasMin := args["mem_min"].(float64); hasMin {
		if memMax, hasMax := args["mem_max"].(float64); hasMax && memMin > memMax {
			return fmt.Errorf("mem_min (%v) cannot be greater than mem_max (%v)", memMin, memMax)
		}
	}

	// 验证机型规格列表
	if deviceClasses, ok := args["device_class"].([]interface{}); ok {
		if len(deviceClasses) > 40 {
			return fmt.Errorf("too many device_class entries, maximum 40 allowed")
		}
		for i, c := range deviceClasses {
			if s, ok := c.(string); !ok || s == "" {
				return fmt.Errorf("device_class[%d] must be a non-empty string", i)
			} else if len(s) > 100 {
				return fmt.Errorf("device_class[%d] too long, maximum 100 characters", i)
			}
		}
	}

	// 验证标签列表
	if labels, ok := args["labels"].([]interface{}); ok {
		if len(labels) > 50 {
			return fmt.Errorf("too many labels, maximum 50 allowed")
		}
		for i, label := range labels {
			if s, ok := label.(string); !ok || s == "" {
				return fmt.Errorf("labels[%d] must be a non-empty string", i)
			} else if len(s) > 200 {
				return fmt.Errorf("labels[%d] too long, maximum 200 characters", i)
			}
		}
	}

	// 验证磁盘规格
	if diskSpecs, ok := args["disk_specs"].([]interface{}); ok {
		if len(diskSpecs) > 10 {
			return fmt.Errorf("too many disk_specs, maximum 10 allowed")
		}
		for i, spec := range diskSpecs {
			if specMap, ok := spec.(map[string]interface{}); ok {
				if err := validateDiskSpec(specMap, i); err != nil {
					return err
				}
			} else {
				return fmt.Errorf("disk_specs[%d] must be an object", i)
			}
		}
	}

	return nil
}

// validateDiskSpec 验证单个磁盘规格
func validateDiskSpec(spec map[string]interface{}, index int) error {
	mountPoint, ok := spec["mount_point"].(string)
	if !ok || mountPoint == "" {
		return fmt.Errorf("disk_specs[%d].mount_point is required and must be a non-empty string", index)
	}
	if len(mountPoint) > 100 {
		return fmt.Errorf("disk_specs[%d].mount_point too long, maximum 100 characters", index)
	}

	if diskType, ok := spec["disk_type"].(string); ok && diskType != "" {
		if len(diskType) > 50 {
			return fmt.Errorf("disk_specs[%d].disk_type too long, maximum 50 characters", index)
		}
		// 验证磁盘类型是否在允许的范围内
		validTypes := []string{"SSD", "HDD", "CLOUD_SSD", "CLOUD_PREMIUM", "CLOUD_BASIC", "NVME"}
		isValid := false
		for _, vt := range validTypes {
			if strings.EqualFold(diskType, vt) {
				isValid = true
				break
			}
		}
		if !isValid {
			return fmt.Errorf("disk_specs[%d].disk_type '%s' is not supported. Valid types: %v", index, diskType, validTypes)
		}
	}

	if minSize, ok := spec["min_size"].(float64); ok {
		if minSize < 0 || minSize > 100000000 { // 100TB in GB
			return fmt.Errorf("disk_specs[%d].min_size must be between 0 and 100000000 GB", index)
		}
	}

	if maxSize, ok := spec["max_size"].(float64); ok {
		if maxSize < 0 || maxSize > 100000000 {
			return fmt.Errorf("disk_specs[%d].max_size must be between 0 and 100000000 GB", index)
		}
	}

	if minSize, hasMin := spec["min_size"].(float64); hasMin {
		if maxSize, hasMax := spec["max_size"].(float64); hasMax && minSize > maxSize {
			return fmt.Errorf("disk_specs[%d].min_size (%v) cannot be greater than max_size (%v)", index, minSize, maxSize)
		}
	}

	return nil
}

// QueryOptimizer 查询优化器
type QueryOptimizer struct {
	mu                sync.RWMutex
	queryCache        map[string]*CachedQueryResult
	concurrentQueries chan struct{}
}

// CachedQueryResult 缓存的查询结果
type CachedQueryResult struct {
	Result    *ResourceTypeInferenceResult
	ExpiresAt time.Time
	QueryHash string
}

// QueryMetrics 查询性能指标
type QueryMetrics struct {
	QueryDuration     time.Duration `json:"query_duration_ms"`
	CacheHit          bool          `json:"cache_hit"`
	DatabaseQueries   int           `json:"database_queries"`
	ResultCount       int           `json:"result_count"`
	OptimizationsUsed []string      `json:"optimizations_used"`
}

// 全局查询优化器实例
var globalQueryOptimizer = &QueryOptimizer{
	queryCache:        make(map[string]*CachedQueryResult),
	concurrentQueries: make(chan struct{}, MaxConcurrentQueries),
}

// ResourceTypeInferenceResult 资源类型推测结果
type ResourceTypeInferenceResult struct {
	CurrentResourceType     string                 `json:"current_resource_type"`     // 当前资源类型
	AlternativeResourceType string                 `json:"alternative_resource_type"` // 替代资源类型
	AlternativeAvailable    bool                   `json:"alternative_available"`     // 替代资源类型是否有可用资源
	AlternativeCount        int                    `json:"alternative_count"`         // 替代资源类型可用数量
	AlternativeDistribution map[string]interface{} `json:"alternative_distribution"`  // 替代资源分布信息
	Verified                bool                   `json:"verified"`                  // 推测结果是否已验证
	Confidence              string                 `json:"confidence"`                // 置信度 (high/medium/low)
	Suggestion              string                 `json:"suggestion"`                // 推测建议
	FailureReason           string                 `json:"failure_reason,omitempty"`  // 失败原因
	Error                   string                 `json:"error,omitempty"`           // 错误信息
	Metrics                 *QueryMetrics          `json:"metrics,omitempty"`         // 查询性能指标
}

// StandardAnalysisResult 标准化分析结果格式（与现有分析结果兼容）
type StandardAnalysisResult struct {
	AnalysisType    string                 `json:"analysis_type"`   // 分析类型：resource_type_inference
	Status          string                 `json:"status"`          // 状态：success/failed/warning
	Summary         string                 `json:"summary"`         // 分析摘要
	Details         map[string]interface{} `json:"details"`         // 详细信息
	Recommendations []Recommendation       `json:"recommendations"` // 推荐建议
	Metadata        AnalysisMetadata       `json:"metadata"`        // 元数据
}

// Recommendation 推荐建议
type Recommendation struct {
	Type        string                 `json:"type"`        // 建议类型：resource_type_change/parameter_adjustment
	Priority    string                 `json:"priority"`    // 优先级：high/medium/low
	Title       string                 `json:"title"`       // 建议标题
	Description string                 `json:"description"` // 建议描述
	Action      string                 `json:"action"`      // 具体行动
	Impact      string                 `json:"impact"`      // 预期影响
	Parameters  map[string]interface{} `json:"parameters"`  // 相关参数
}

// AnalysisMetadata 分析元数据
type AnalysisMetadata struct {
	AnalysisTime    time.Time     `json:"analysis_time"`    // 分析时间
	Duration        time.Duration `json:"duration"`         // 分析耗时
	Version         string        `json:"version"`          // 工具版本
	Confidence      string        `json:"confidence"`       // 整体置信度
	DataSources     []string      `json:"data_sources"`     // 数据来源
	LimitationsNote string        `json:"limitations_note"` // 限制说明
}

// ResourceTypeDetail 资源类型详细信息
type ResourceTypeDetail struct {
	ResourceType  string                 `json:"resource_type"`  // 资源类型
	Available     bool                   `json:"available"`      // 是否可用
	Count         int                    `json:"count"`          // 可用数量
	Distribution  map[string]interface{} `json:"distribution"`   // 分布信息
	Compatibility string                 `json:"compatibility"`  // 兼容性评估
	MigrationCost string                 `json:"migration_cost"` // 迁移成本
	Advantages    []string               `json:"advantages"`     // 优势
	Disadvantages []string               `json:"disadvantages"`  // 劣势
}

// inferResourceTypeToolDef 资源类型推测工具定义
func (t *ResourceTools) inferResourceTypeToolDef() ToolDefinition {
	return NewFunctionTool(
		"infer_resource_type",
		"当 mysql 或 tendbcluster 相关资源申请失败时，辅助判断库内是否仍有可用机。资源池中二者已统一为 rs_type=mysql；申请侧仍可能传入 tendbcluster（兼容旧参数）。本工具在相同筛选条件下按与申请接口 MatchRsType 一致的方式统计：rs_type IN (PUBLIC, 归一化后的 mysql)。",
		map[string]interface{}{
			"type": "object",
			"properties": map[string]interface{}{
				"current_resource_type": map[string]interface{}{
					"type":        "string",
					"description": "申请失败时所填资源类型；支持 mysql 或 tendbcluster（后者仅为请求参数兼容，与 mysql 共用 mysql 资源池）",
					"enum":        []string{"mysql", "tendbcluster"},
				},
				"bk_cloud_id": map[string]interface{}{
					"type":        "integer",
					"description": "云区域ID",
				},
				"city": map[string]interface{}{
					"type":        "string",
					"description": "城市名称，可选",
				},
				"sub_zone_ids": map[string]interface{}{
					"type":        "array",
					"items":       map[string]interface{}{"type": "string"},
					"description": "园区ID列表，可选",
				},
				"device_class": map[string]interface{}{
					"type":        "array",
					"items":       map[string]interface{}{"type": "string"},
					"description": "机型规格列表(如['S5.MEDIUM8'])，可选",
				},
				"cpu_min": map[string]interface{}{
					"type":        "integer",
					"description": "最小CPU核数，可选",
				},
				"cpu_max": map[string]interface{}{
					"type":        "integer",
					"description": "最大CPU核数，可选",
				},
				"mem_min": map[string]interface{}{
					"type":        "integer",
					"description": "最小内存(MB)，可选",
				},
				"mem_max": map[string]interface{}{
					"type":        "integer",
					"description": "最大内存(MB)，可选",
				},
				"labels": map[string]interface{}{
					"type":        "array",
					"items":       map[string]interface{}{"type": "string"},
					"description": "标签列表，可选",
				},
				"disk_specs": map[string]interface{}{
					"type": "array",
					"items": map[string]interface{}{
						"type": "object",
						"properties": map[string]interface{}{
							"mount_point": map[string]interface{}{
								"type":        "string",
								"description": "挂载点(如'/data', '/data1')",
							},
							"disk_type": map[string]interface{}{
								"type":        "string",
								"description": "磁盘类型(SSD/HDD/CLOUD_SSD/CLOUD_PREMIUM等)",
							},
							"min_size": map[string]interface{}{
								"type":        "integer",
								"description": "最小磁盘大小(GB)",
							},
							"max_size": map[string]interface{}{
								"type":        "integer",
								"description": "最大磁盘大小(GB)，若>0则使用范围匹配[min,max]",
							},
						},
						"required": []string{"mount_point"},
					},
					"description": "磁盘规格要求列表，可选",
				},
			},
			"required": []string{"current_resource_type", "bk_cloud_id"},
		},
	)
}

// inferResourceType 执行资源类型推测（与申请 MatchRsType 默认分支一致：PUBLIC + 归一化 rs_type）
func (t *ResourceTools) inferResourceType(args map[string]interface{}) (*ResourceTypeInferenceResult, error) {
	result := &ResourceTypeInferenceResult{
		AlternativeDistribution: make(map[string]interface{}),
	}
	if err := validateResourceTypeInferenceParams(args); err != nil {
		result.Error = err.Error()
		result.Verified = false
		result.Confidence = "low"
		result.FailureReason = "parameter validation failed"
		return result, err
	}
	currentType := args["current_resource_type"].(string)
	poolRsType := model.NormalizeResourceType(currentType)
	return t.inferResourceTypeForApplyPool(args, currentType, poolRsType)
}

// inferResourceTypeForApplyPool 按与 SearchContext.MatchRsType 默认规则一致的 rs_type 集合做库存推测
func (t *ResourceTools) inferResourceTypeForApplyPool(
	args map[string]interface{},
	currentType string,
	poolRsType string,
) (*ResourceTypeInferenceResult, error) {
	result := &ResourceTypeInferenceResult{
		AlternativeDistribution: make(map[string]interface{}),
		CurrentResourceType:     currentType,
		AlternativeResourceType: poolRsType,
	}
	bkCloudID := getBkCloudID(args)
	rsTypes := []string{model.RESOURCE_TYPE_PUBLIC, poolRsType}
	query := t.db.Table(model.TbRpDetailName()).
		Where("bk_cloud_id = ? AND status = ? AND gse_agent_status_code = ? AND rs_type IN ?",
			bkCloudID, model.Unused, bk.GseAlive, rsTypes)

	// 应用查询优化
	optimizedQuery, optimizations := t.optimizeQuery(query, args)

	// 应用可选条件，并处理潜在的SQL注入风险
	optimizedQuery, err := t.applyOptionalConditions(optimizedQuery, args)
	if err != nil {
		result.Error = fmt.Sprintf("failed to apply query conditions: %v", err)
		result.Verified = false
		result.Confidence = "low"
		result.FailureReason = "query condition error"
		return result, err
	}

	// 执行查询获取总数，添加超时控制
	ctx, cancel := context.WithTimeout(context.Background(), DefaultQueryTimeout)
	defer cancel()

	var totalCount int64
	if err := optimizedQuery.WithContext(ctx).Count(&totalCount).Error; err != nil {
		// 根据错误类型提供不同的处理
		if errors.Is(err, context.DeadlineExceeded) {
			result.Error = "query timeout: database query took too long"
			result.FailureReason = "query timeout"
		} else if strings.Contains(err.Error(), "connection") {
			result.Error = "database connection error"
			result.FailureReason = "database connection lost"
		} else {
			result.Error = fmt.Sprintf("database query failed: %v", err)
			result.FailureReason = "database query error"
		}
		result.Verified = false
		result.Confidence = "low"
		return result, err
	}

	result.AlternativeCount = int(totalCount)
	result.AlternativeAvailable = totalCount > 0

	// 如果有可用资源，获取分布信息
	if totalCount > 0 {
		distribution, err := t.getResourceDistribution(optimizedQuery.WithContext(ctx), poolRsType)
		if err != nil {
			// 分布信息获取失败不影响主要结果，但要记录错误
			result.Error = fmt.Sprintf("failed to get distribution details: %v", err)
			result.AlternativeDistribution = map[string]interface{}{
				"error": "distribution data unavailable",
			}
		} else {
			result.AlternativeDistribution = distribution
		}

		// 验证推测结果的准确性
		confidence, verified := t.verifyInferenceResult(optimizedQuery.WithContext(ctx), args, int(totalCount))
		result.Verified = verified
		result.Confidence = confidence

		// 根据验证结果生成建议
		result.Suggestion = t.generateSuggestion(poolRsType, int(totalCount), confidence, verified)

		// 添加性能指标
		if result.Metrics == nil {
			result.Metrics = &QueryMetrics{}
		}
		result.Metrics.OptimizationsUsed = optimizations
		result.Metrics.DatabaseQueries = 2 // Count查询 + 分布查询
	} else {
		result.Verified = true
		result.Confidence = "high"
		result.Suggestion = t.generateNoResourceSuggestion(currentType, poolRsType, args)
		result.FailureReason = "no available resources in PUBLIC or normalized pool matching the criteria"

		// 提供一些可能的解决方案
		result.AlternativeDistribution = map[string]interface{}{
			"suggestions": []string{
				"Try relaxing CPU/memory requirements",
				"Consider different sub-zones or cities",
				"Check if device class requirements are too restrictive",
				"Verify disk specifications are not overly specific",
			},
		}
	}

	return result, nil
}

// applyOptionalConditions 应用可选查询条件
func (t *ResourceTools) applyOptionalConditions(query *gorm.DB, args map[string]interface{}) (*gorm.DB, error) {
	// 城市条件
	if city, ok := args["city"].(string); ok && city != "" {
		query = query.Where("city = ?", city)
	}

	// 园区条件
	if subZoneIds, ok := args["sub_zone_ids"].([]interface{}); ok && len(subZoneIds) > 0 {
		var zones []string
		for _, id := range subZoneIds {
			if s, ok := id.(string); ok && s != "" {
				zones = append(zones, s)
			}
		}
		if len(zones) > 0 {
			query = query.Where("sub_zone_id IN ?", zones)
		}
	}

	// CPU条件
	if cpuMin, ok := args["cpu_min"].(float64); ok && cpuMin > 0 {
		query = query.Where("cpu >= ?", int(cpuMin))
	}
	if cpuMax, ok := args["cpu_max"].(float64); ok && cpuMax > 0 {
		query = query.Where("cpu <= ?", int(cpuMax))
	}

	// 内存条件
	if memMin, ok := args["mem_min"].(float64); ok && memMin > 0 {
		query = query.Where("mem >= ?", int(memMin))
	}
	if memMax, ok := args["mem_max"].(float64); ok && memMax > 0 {
		query = query.Where("mem <= ?", int(memMax))
	}

	// 机型规格条件
	if deviceClasses, ok := args["device_class"].([]interface{}); ok && len(deviceClasses) > 0 {
		var classes []string
		for _, c := range deviceClasses {
			if s, ok := c.(string); ok && s != "" {
				classes = append(classes, s)
			}
		}
		if len(classes) > 0 {
			query = query.Where("device_class IN ?", classes)
		}
	}

	// 标签条件
	if labels, ok := args["labels"].([]interface{}); ok && len(labels) > 0 {
		for _, label := range labels {
			if s, ok := label.(string); ok && s != "" {
				// 使用参数化查询防止SQL注入
				query = query.Where("JSON_CONTAINS(labels, ?)", fmt.Sprintf(`"%s"`, s))
			}
		}
	}

	// 磁盘条件
	if diskSpecs, ok := args["disk_specs"].([]interface{}); ok && len(diskSpecs) > 0 {
		var err error
		query, err = t.applyDiskSpecConditions(query, diskSpecs)
		if err != nil {
			return nil, fmt.Errorf("failed to apply disk conditions: %w", err)
		}
	}

	return query, nil
}

// generateSuggestion 生成推测建议（poolRsType 为库内归一化后的业务 rs_type，与 PUBLIC 组合匹配申请逻辑）
func (t *ResourceTools) generateSuggestion(poolRsType string, count int, confidence string, verified bool) string {
	poolDesc := fmt.Sprintf("PUBLIC 或 %s（与申请 MatchRsType 一致）", poolRsType)
	if !verified {
		return fmt.Sprintf("在 rs_type 为 %s 的机器上，当前条件下约有 %d 台可用，但推测结果需要进一步验证", poolDesc, count)
	}

	switch confidence {
	case "high":
		return fmt.Sprintf("在 rs_type 为 %s 的机器上，当前条件下有 %d 台可用，完全符合申请条件", poolDesc, count)
	case "medium":
		return fmt.Sprintf("在 rs_type 为 %s 的机器上，当前条件下有 %d 台可用，基本符合申请条件", poolDesc, count)
	case "low":
		return fmt.Sprintf("在 rs_type 为 %s 的机器上，当前条件下有 %d 台可用，但匹配度较低，建议调整申请条件", poolDesc, count)
	default:
		return fmt.Sprintf("在 rs_type 为 %s 的机器上，当前条件下有 %d 台可用", poolDesc, count)
	}
}

// generateNoResourceSuggestion 生成无资源时的建议（poolRsType 为库内归一化后的业务 rs_type）
func (t *ResourceTools) generateNoResourceSuggestion(currentType, poolRsType string, args map[string]interface{}) string {
	suggestions := []string{
		fmt.Sprintf("申请侧资源类型为 '%s'；与申请一致的可匹配 rs_type 为 PUBLIC 或 '%s'。在当前筛选条件下未匹配到可用资源",
			currentType, poolRsType),
	}

	// 根据申请条件提供具体建议
	if _, hasCity := args["city"]; hasCity {
		suggestions = append(suggestions, "建议尝试其他城市或移除城市限制")
	}

	if subZones, ok := args["sub_zone_ids"].([]interface{}); ok && len(subZones) > 0 {
		suggestions = append(suggestions, "建议扩大园区选择范围或移除园区限制")
	}

	if _, hasCPU := args["cpu_min"]; hasCPU {
		suggestions = append(suggestions, "建议适当降低CPU要求")
	}

	if _, hasMem := args["mem_min"]; hasMem {
		suggestions = append(suggestions, "建议适当降低内存要求")
	}

	if deviceClasses, ok := args["device_class"].([]interface{}); ok && len(deviceClasses) > 0 {
		suggestions = append(suggestions, "建议扩大机型规格选择范围")
	}

	if diskSpecs, ok := args["disk_specs"].([]interface{}); ok && len(diskSpecs) > 0 {
		suggestions = append(suggestions, "建议简化磁盘规格要求")
	}

	return strings.Join(suggestions, "；")
}

// applyDiskSpecConditions 应用磁盘规格条件
func (t *ResourceTools) applyDiskSpecConditions(query *gorm.DB, diskSpecs []interface{}) (*gorm.DB, error) {
	if len(diskSpecs) == 0 {
		return query, nil
	}

	for i, spec := range diskSpecs {
		specMap, ok := spec.(map[string]interface{})
		if !ok {
			return nil, fmt.Errorf("disk_specs[%d] must be an object", i)
		}

		mountPoint, ok := specMap["mount_point"].(string)
		if !ok || mountPoint == "" {
			return nil, fmt.Errorf("disk_specs[%d].mount_point is required", i)
		}

		// 安全检查：防止SQL注入，只允许安全的挂载点字符
		if !isValidMountPoint(mountPoint) {
			return nil, fmt.Errorf("disk_specs[%d].mount_point contains invalid characters", i)
		}

		// 构建磁盘条件。挂载点含 "/"，JSON Path 必须写成 $."/data".size
		query = query.Where(
			fmt.Sprintf("JSON_EXTRACT(storage_device, '%s') IS NOT NULL", storageDeviceJSONPath(mountPoint)))

		if diskType, ok := specMap["disk_type"].(string); ok && diskType != "" {
			if !isValidDiskType(diskType) {
				return nil, fmt.Errorf("disk_specs[%d].disk_type '%s' is not valid", i, diskType)
			}
			query = query.Where(
				fmt.Sprintf("JSON_UNQUOTE(JSON_EXTRACT(storage_device, '%s')) = ?",
					storageDeviceJSONPath(mountPoint, "disk_type")),
				diskType)
		}

		if minSize, ok := specMap["min_size"].(float64); ok && minSize > 0 {
			if minSize < 0 || minSize > 100000000 { // 100TB limit
				return nil, fmt.Errorf("disk_specs[%d].min_size %v is out of valid range", i, minSize)
			}
			query = query.Where(
				fmt.Sprintf("CAST(JSON_EXTRACT(storage_device, '%s') AS SIGNED) >= ?",
					storageDeviceJSONPath(mountPoint, "size")),
				int(minSize))
		}

		if maxSize, ok := specMap["max_size"].(float64); ok && maxSize > 0 {
			if maxSize < 0 || maxSize > 100000000 { // 100TB limit
				return nil, fmt.Errorf("disk_specs[%d].max_size %v is out of valid range", i, maxSize)
			}
			query = query.Where(
				fmt.Sprintf("CAST(JSON_EXTRACT(storage_device, '%s') AS SIGNED) <= ?",
					storageDeviceJSONPath(mountPoint, "size")),
				int(maxSize))
		}
	}
	return query, nil
}

// isValidMountPoint 检查挂载点是否安全
func isValidMountPoint(mountPoint string) bool {
	// 只允许字母、数字、下划线、斜杠和短横线
	for _, r := range mountPoint {
		if !((r >= 'a' && r <= 'z') || (r >= 'A' && r <= 'Z') ||
			(r >= '0' && r <= '9') || r == '_' || r == '/' || r == '-') {
			return false
		}
	}
	return len(mountPoint) > 0 && len(mountPoint) <= 100
}

// isValidDiskType 检查磁盘类型是否有效
func isValidDiskType(diskType string) bool {
	validTypes := []string{"SSD", "HDD", "CLOUD_SSD", "CLOUD_PREMIUM", "CLOUD_BASIC", "NVME"}
	for _, vt := range validTypes {
		if strings.EqualFold(diskType, vt) {
			return true
		}
	}
	return false
}

// getResourceDistribution 获取资源分布信息
func (t *ResourceTools) getResourceDistribution(query *gorm.DB, resourceType string) (map[string]interface{}, error) {
	resourceType = model.NormalizeResourceType(resourceType)
	distribution := make(map[string]interface{})

	// 检查查询对象是否有效
	if query == nil {
		return nil, fmt.Errorf("query object is nil")
	}

	// 按园区统计
	var subZoneStats []struct {
		SubZone string
		City    string
		Count   int
	}

	subZoneQuery := query.Session(&gorm.Session{}).
		Select("sub_zone_id as sub_zone, city, count(*) as count").
		Group("sub_zone_id, city").
		Limit(100) // 限制结果数量，防止过多数据

	if err := subZoneQuery.Scan(&subZoneStats).Error; err != nil {
		// 如果是超时错误，返回特定错误信息
		if errors.Is(err, context.DeadlineExceeded) {
			return nil, fmt.Errorf("timeout while getting sub zone statistics: %w", err)
		}
		return nil, fmt.Errorf("failed to get sub zone stats: %w", err)
	}

	// 检查结果数量是否合理
	if len(subZoneStats) > 50 {
		// 如果园区太多，只取前50个并添加说明
		subZoneStats = subZoneStats[:50]
		distribution["sub_zone_truncated"] = true
	}

	bySubZone := make(map[string]interface{})
	totalBySubZone := 0
	for _, s := range subZoneStats {
		if s.Count <= 0 {
			continue // 跳过无效数据
		}
		displayName := formatSubZoneDisplay(s.City, "", s.SubZone)
		bySubZone[displayName] = s.Count
		totalBySubZone += s.Count
	}
	distribution["by_sub_zone"] = bySubZone
	distribution["total_by_sub_zone"] = totalBySubZone

	// 按机型规格统计
	var deviceStats []struct {
		DeviceClass string
		Count       int
	}

	deviceQuery := query.Session(&gorm.Session{}).
		Select("device_class, count(*) as count").
		Group("device_class").
		Limit(50) // 限制机型数量

	if err := deviceQuery.Scan(&deviceStats).Error; err != nil {
		// 设备统计失败不影响园区统计，但要记录错误
		distribution["device_stats_error"] = fmt.Sprintf("failed to get device stats: %v", err)
	} else {
		// 检查结果数量
		if len(deviceStats) > 30 {
			deviceStats = deviceStats[:30]
			distribution["device_class_truncated"] = true
		}

		byDevice := make(map[string]int)
		totalByDevice := 0
		for _, s := range deviceStats {
			if s.Count <= 0 || s.DeviceClass == "" {
				continue // 跳过无效数据
			}
			byDevice[s.DeviceClass] = s.Count
			totalByDevice += s.Count
		}
		distribution["by_device_class"] = byDevice
		distribution["total_by_device_class"] = totalByDevice
	}

	// 添加一些元数据
	distribution["resource_type"] = resourceType
	distribution["generated_at"] = time.Now().Unix()

	// 验证分布数据的完整性
	if len(bySubZone) == 0 && totalBySubZone == 0 {
		return nil, fmt.Errorf("no valid distribution data found")
	}

	return distribution, nil
}

// verifyInferenceResult 验证推测结果的准确性和置信度
func (t *ResourceTools) verifyInferenceResult(query *gorm.DB, args map[string]interface{}, availableCount int) (confidence string, verified bool) {
	// 基础验证：检查是否有足够的资源
	if availableCount == 0 {
		return "high", true // 没有资源是确定的结果
	}

	// 计算置信度分数
	confidenceScore := 100.0

	// 检查关键条件的匹配度
	// 1. 检查园区分布是否合理
	if subZoneIds, ok := args["sub_zone_ids"].([]interface{}); ok && len(subZoneIds) > 0 {
		// 如果指定了园区，检查资源是否在指定园区内
		var matchingCount int64
		zones := make([]string, 0, len(subZoneIds))
		for _, id := range subZoneIds {
			if s, ok := id.(string); ok && s != "" {
				zones = append(zones, s)
			}
		}
		if len(zones) > 0 {
			query.Session(&gorm.Session{}).Where("sub_zone_id IN ?", zones).Count(&matchingCount)
			if matchingCount == 0 {
				confidenceScore -= 30 // 没有在指定园区的资源
			} else if float64(matchingCount)/float64(availableCount) < 0.5 {
				confidenceScore -= 15 // 指定园区资源较少
			}
		}
	}

	// 2. 检查机型规格匹配度
	if deviceClasses, ok := args["device_class"].([]interface{}); ok && len(deviceClasses) > 0 {
		var matchingCount int64
		classes := make([]string, 0, len(deviceClasses))
		for _, c := range deviceClasses {
			if s, ok := c.(string); ok && s != "" {
				classes = append(classes, s)
			}
		}
		if len(classes) > 0 {
			query.Session(&gorm.Session{}).Where("device_class IN ?", classes).Count(&matchingCount)
			if matchingCount == 0 {
				confidenceScore -= 25 // 没有匹配的机型规格
			} else if float64(matchingCount)/float64(availableCount) < 0.3 {
				confidenceScore -= 10 // 匹配的机型规格较少
			}
		}
	}

	// 3. 检查磁盘条件的复杂度
	if diskSpecs, ok := args["disk_specs"].([]interface{}); ok && len(diskSpecs) > 0 {
		complexDiskConditions := 0
		for _, spec := range diskSpecs {
			if specMap, ok := spec.(map[string]interface{}); ok {
				if _, hasType := specMap["disk_type"]; hasType {
					complexDiskConditions++
				}
				if minSize, hasMin := specMap["min_size"].(float64); hasMin && minSize > 0 {
					complexDiskConditions++
				}
				if maxSize, hasMax := specMap["max_size"].(float64); hasMax && maxSize > 0 {
					complexDiskConditions++
				}
			}
		}
		if complexDiskConditions > 3 {
			confidenceScore -= 15 // 复杂的磁盘条件可能影响准确性
		}
	}

	// 4. 检查资源数量是否充足
	if availableCount < 5 {
		confidenceScore -= 10 // 可用资源较少
	} else if availableCount >= 20 {
		confidenceScore += 5 // 充足的资源增加置信度
	}

	// 5. 检查CPU和内存条件的严格程度
	cpuRange := 0.0
	if cpuMin, hasMin := args["cpu_min"].(float64); hasMin {
		if cpuMax, hasMax := args["cpu_max"].(float64); hasMax {
			cpuRange = cpuMax - cpuMin
		}
	}
	memRange := 0.0
	if memMin, hasMin := args["mem_min"].(float64); hasMin {
		if memMax, hasMax := args["mem_max"].(float64); hasMax {
			memRange = memMax - memMin
		}
	}

	// 如果CPU或内存范围很窄，可能影响匹配
	if cpuRange > 0 && cpuRange <= 2 {
		confidenceScore -= 5 // CPU范围很窄
	}
	if memRange > 0 && memRange <= 1024 { // 1GB
		confidenceScore -= 5 // 内存范围很窄
	}

	// 根据置信度分数确定等级
	verified = true
	if confidenceScore >= 85 {
		confidence = "high"
	} else if confidenceScore >= 65 {
		confidence = "medium"
	} else {
		confidence = "low"
		if confidenceScore < 50 {
			verified = false // 置信度太低，标记为未验证
		}
	}

	return confidence, verified
}

// ========== 查询优化器相关方法 ==========

// generateQueryHash 生成查询哈希值用于缓存
func generateQueryHash(args map[string]interface{}) string {
	// 创建一个稳定的哈希值
	keys := make([]string, 0, len(args))
	for k := range args {
		keys = append(keys, k)
	}
	sort.Strings(keys)

	var parts []string
	for _, k := range keys {
		if v := args[k]; v != nil {
			parts = append(parts, fmt.Sprintf("%s=%v", k, v))
		}
	}

	h := sha256.Sum256([]byte(strings.Join(parts, "&")))
	return fmt.Sprintf("%x", h)[:16] // 使用前16个字符
}

// getCachedResult 获取缓存的查询结果
func (opt *QueryOptimizer) getCachedResult(queryHash string) (*ResourceTypeInferenceResult, bool) {
	opt.mu.RLock()
	defer opt.mu.RUnlock()

	cached, exists := opt.queryCache[queryHash]
	if !exists {
		return nil, false
	}

	// 检查是否过期
	if time.Now().After(cached.ExpiresAt) {
		// 异步清理过期缓存
		go func() {
			opt.mu.Lock()
			delete(opt.queryCache, queryHash)
			opt.mu.Unlock()
		}()
		return nil, false
	}

	return cached.Result, true
}

// setCachedResult 设置缓存的查询结果
func (opt *QueryOptimizer) setCachedResult(queryHash string, result *ResourceTypeInferenceResult) {
	opt.mu.Lock()
	defer opt.mu.Unlock()

	// 清理过期缓存
	if len(opt.queryCache) >= QueryResultCacheSize {
		opt.cleanExpiredCache()
	}

	// 如果缓存仍然满了，删除最旧的条目
	if len(opt.queryCache) >= QueryResultCacheSize {
		for k := range opt.queryCache {
			delete(opt.queryCache, k)
			break
		}
	}

	opt.queryCache[queryHash] = &CachedQueryResult{
		Result:    result,
		ExpiresAt: time.Now().Add(QueryResultCacheTTL),
		QueryHash: queryHash,
	}
}

// cleanExpiredCache 清理过期缓存
func (opt *QueryOptimizer) cleanExpiredCache() {
	now := time.Now()
	for k, v := range opt.queryCache {
		if now.After(v.ExpiresAt) {
			delete(opt.queryCache, k)
		}
	}
}

// acquireQuerySlot 获取查询槽位（并发控制）
func (opt *QueryOptimizer) acquireQuerySlot(ctx context.Context) error {
	select {
	case opt.concurrentQueries <- struct{}{}:
		return nil
	case <-ctx.Done():
		return ctx.Err()
	}
}

// releaseQuerySlot 释放查询槽位
func (opt *QueryOptimizer) releaseQuerySlot() {
	select {
	case <-opt.concurrentQueries:
	default:
		// 槽位已经被释放或者从未获取
	}
}

// optimizeQuery 优化查询条件
func (t *ResourceTools) optimizeQuery(query *gorm.DB, args map[string]interface{}) (*gorm.DB, []string) {
	optimizations := make([]string, 0)

	// 1. 添加查询优化（基于云区域ID）
	if _, ok := args["bk_cloud_id"]; ok {
		// 优先使用云区域ID相关的排序，提高查询效率
		query = query.Order("bk_cloud_id, status, rs_type")
		optimizations = append(optimizations, "cloud_id_ordering")
	}

	// 注意：不在这里添加LIMIT和SELECT，因为这会影响COUNT查询
	// 这些优化应该在具体的查询方法中根据需要添加

	// 4. 添加查询提示
	if deviceClasses, ok := args["device_class"].([]interface{}); ok && len(deviceClasses) > 0 {
		// 如果指定了机型，优先使用机型索引
		optimizations = append(optimizations, "device_class_index")
	}

	return query, optimizations
}

// optimizedInferResourceType 带性能优化的资源类型推测
func (t *ResourceTools) optimizedInferResourceType(args map[string]interface{}) (*ResourceTypeInferenceResult, error) {
	startTime := time.Now()
	metrics := &QueryMetrics{
		DatabaseQueries:   0,
		OptimizationsUsed: make([]string, 0),
	}

	// 生成查询哈希
	queryHash := generateQueryHash(args)

	// 尝试从缓存获取结果
	if cachedResult, found := globalQueryOptimizer.getCachedResult(queryHash); found {
		metrics.CacheHit = true
		metrics.QueryDuration = time.Since(startTime)
		cachedResult.Metrics = metrics
		return cachedResult, nil
	}

	metrics.CacheHit = false

	// 获取查询槽位（并发控制）
	ctx, cancel := context.WithTimeout(context.Background(), DefaultQueryTimeout)
	defer cancel()

	if err := globalQueryOptimizer.acquireQuerySlot(ctx); err != nil {
		return &ResourceTypeInferenceResult{
			Error:         "query slot acquisition timeout",
			FailureReason: "system overload",
			Verified:      false,
			Confidence:    "low",
			Metrics:       metrics,
		}, err
	}
	defer globalQueryOptimizer.releaseQuerySlot()

	// 执行实际的推测逻辑
	result, err := t.inferResourceType(args)
	if result != nil {
		metrics.QueryDuration = time.Since(startTime)
		metrics.ResultCount = result.AlternativeCount
		result.Metrics = metrics

		// 缓存结果（仅缓存成功的结果）
		if err == nil && result.Error == "" {
			globalQueryOptimizer.setCachedResult(queryHash, result)
		}
	}

	return result, err
}

// ========== 标准化结果格式相关方法 ==========

// toStandardAnalysisResult 将推测结果转换为标准化分析结果格式
func (result *ResourceTypeInferenceResult) toStandardAnalysisResult() *StandardAnalysisResult {
	startTime := time.Now()
	if result.Metrics != nil {
		startTime = startTime.Add(-result.Metrics.QueryDuration)
	}

	// 确定状态
	status := "success"
	if result.Error != "" {
		status = "failed"
	} else if !result.AlternativeAvailable {
		status = "warning"
	}

	// 生成摘要
	summary := generateAnalysisSummary(result)

	// 构建详细信息
	details := map[string]interface{}{
		"current_resource_type":     result.CurrentResourceType,
		"alternative_resource_type": result.AlternativeResourceType,
		"alternative_available":     result.AlternativeAvailable,
		"alternative_count":         result.AlternativeCount,
		"distribution":              result.AlternativeDistribution,
		"verified":                  result.Verified,
		"confidence":                result.Confidence,
		"failure_reason":            result.FailureReason,
	}

	// 添加资源类型详细信息
	if result.AlternativeResourceType != "" {
		details["resource_type_details"] = generateResourceTypeDetails(result)
	}

	// 生成推荐建议
	recommendations := generateRecommendations(result)

	// 构建元数据
	metadata := AnalysisMetadata{
		AnalysisTime:    startTime,
		Duration:        result.Metrics.QueryDuration,
		Version:         "1.0.0",
		Confidence:      result.Confidence,
		DataSources:     []string{"tb_rp_detail"},
		LimitationsNote: "推测结果基于当前资源池状态，实际可用性可能因资源分配策略而异",
	}

	if result.Metrics != nil {
		metadata.Duration = result.Metrics.QueryDuration
	}

	return &StandardAnalysisResult{
		AnalysisType:    "resource_type_inference",
		Status:          status,
		Summary:         summary,
		Details:         details,
		Recommendations: recommendations,
		Metadata:        metadata,
	}
}

// generateAnalysisSummary 生成分析摘要
func generateAnalysisSummary(result *ResourceTypeInferenceResult) string {
	if result.Error != "" {
		return fmt.Sprintf("资源类型推测失败：%s", result.Error)
	}

	if result.AlternativeAvailable {
		return fmt.Sprintf("在与申请一致的 rs_type（PUBLIC 或 '%s'）范围内，发现 %d 台可用资源，置信度：%s",
			result.AlternativeResourceType, result.AlternativeCount, result.Confidence)
	}

	return fmt.Sprintf("在与申请一致的 rs_type（PUBLIC 或 '%s'）范围内，申请侧类型 '%s' 当前条件下未匹配到可用资源",
		result.AlternativeResourceType, result.CurrentResourceType)
}

// generateResourceTypeDetails 生成资源类型详细信息
func generateResourceTypeDetails(result *ResourceTypeInferenceResult) *ResourceTypeDetail {
	detail := &ResourceTypeDetail{
		ResourceType:  result.AlternativeResourceType,
		Available:     result.AlternativeAvailable,
		Count:         result.AlternativeCount,
		Distribution:  result.AlternativeDistribution,
		Compatibility: assessCompatibility(result.CurrentResourceType, result.AlternativeResourceType),
		MigrationCost: assessMigrationCost(result.CurrentResourceType, result.AlternativeResourceType),
	}

	// 添加优势和劣势分析
	detail.Advantages, detail.Disadvantages = analyzeResourceTypeTradeoffs(
		result.CurrentResourceType, result.AlternativeResourceType)

	return detail
}

// assessCompatibility 评估兼容性
func assessCompatibility(currentType, alternativeType string) string {
	if model.NormalizeResourceType(currentType) == model.NormalizeResourceType(alternativeType) {
		return "high"
	}
	return "unknown"
}

// assessMigrationCost 评估迁移成本
func assessMigrationCost(currentType, alternativeType string) string {
	if model.NormalizeResourceType(currentType) == model.NormalizeResourceType(alternativeType) {
		return "none"
	}
	return "unknown"
}

// analyzeResourceTypeTradeoffs 分析资源类型的优劣势
func analyzeResourceTypeTradeoffs(currentType, alternativeType string) (advantages []string, disadvantages []string) {
	if model.NormalizeResourceType(currentType) == model.NormalizeResourceType(alternativeType) {
		return []string{
				"与资源申请 MatchRsType 一致：可匹配 rs_type 为 PUBLIC 或归一化后的业务类型",
				"mysql 与 tendbcluster 请求参数对库内资源池等效",
			},
			[]string{"若仍申请失败，需检查 CPU、地域、机型、磁盘等其它条件是否过严"}
	}
	advantages = []string{"资源可用"}
	disadvantages = []string{"兼容性需要进一步评估"}
	return
}

// generateRecommendations 生成推荐建议
func generateRecommendations(result *ResourceTypeInferenceResult) []Recommendation {
	var recommendations []Recommendation

	if result.Error != "" {
		// 错误情况的建议
		recommendations = append(recommendations, Recommendation{
			Type:        "error_resolution",
			Priority:    "high",
			Title:       "解决推测错误",
			Description: "资源类型推测过程中出现错误，需要检查参数和系统状态",
			Action:      "检查输入参数的有效性，确认数据库连接正常",
			Impact:      "解决错误后可以获得准确的推测结果",
			Parameters:  map[string]interface{}{"error": result.Error},
		})
		return recommendations
	}

	if result.AlternativeAvailable {
		// 有可用替代资源的建议
		priority := "medium"
		if result.Confidence == "high" {
			priority = "high"
		}
		sameNormalized := model.NormalizeResourceType(result.CurrentResourceType) == result.AlternativeResourceType
		title := fmt.Sprintf("在 PUBLIC 或 '%s' 范围内存在可用资源", result.AlternativeResourceType)
		action := fmt.Sprintf("保持 resource_type 为 '%s' 或与库内等效的 mysql/tendbcluster；若申请仍失败请收紧/放宽其它筛选与亲和条件",
			result.CurrentResourceType)
		if !sameNormalized {
			action = fmt.Sprintf("可将申请 resource_type 与库内归一化类型对齐（当前库内业务 rs_type 为 '%s'）", result.AlternativeResourceType)
		}

		recommendations = append(recommendations, Recommendation{
			Type:        "resource_type_change",
			Priority:    priority,
			Title:       title,
			Description: result.Suggestion,
			Action:      action,
			Impact:      fmt.Sprintf("可以获得 %d 台可用资源", result.AlternativeCount),
			Parameters: map[string]interface{}{
				"alternative_type": result.AlternativeResourceType,
				"available_count":  result.AlternativeCount,
				"confidence":       result.Confidence,
			},
		})

		// 如果置信度不高，添加验证建议
		if result.Confidence != "high" {
			recommendations = append(recommendations, Recommendation{
				Type:        "verification",
				Priority:    "medium",
				Title:       "验证资源兼容性",
				Description: "由于置信度不是很高，建议进一步验证资源的兼容性",
				Action:      "在正式申请前，先申请少量资源进行测试验证",
				Impact:      "确保资源完全符合业务需求",
				Parameters: map[string]interface{}{
					"confidence": result.Confidence,
					"verified":   result.Verified,
				},
			})
		}
	} else {
		// 无可用资源的建议
		recommendations = append(recommendations, Recommendation{
			Type:        "parameter_adjustment",
			Priority:    "high",
			Title:       "调整资源申请条件",
			Description: "在 PUBLIC 与归一化业务 rs_type 范围内仍无可用资源，建议调整申请条件",
			Action:      "放宽CPU、内存、地域或其它限制条件",
			Impact:      "增加找到可用资源的可能性",
			Parameters:  map[string]interface{}{"failure_reason": result.FailureReason},
		})

		// 从分布信息中提取具体建议
		if suggestions, ok := result.AlternativeDistribution["suggestions"].([]string); ok {
			for i, suggestion := range suggestions {
				recommendations = append(recommendations, Recommendation{
					Type:        "parameter_adjustment",
					Priority:    "medium",
					Title:       fmt.Sprintf("建议 %d", i+1),
					Description: suggestion,
					Action:      suggestion,
					Impact:      "可能增加资源可用性",
					Parameters:  map[string]interface{}{"suggestion_index": i + 1},
				})
			}
		}
	}

	return recommendations
}

// formatForLLMAnalysis 格式化结果供LLM分析使用
func (result *ResourceTypeInferenceResult) formatForLLMAnalysis() map[string]interface{} {
	formatted := map[string]interface{}{
		"analysis_type": "resource_type_inference",
		"input": map[string]interface{}{
			"current_resource_type": result.CurrentResourceType,
			"alternative_checked":   result.AlternativeResourceType,
		},
		"output": map[string]interface{}{
			"alternative_available": result.AlternativeAvailable,
			"alternative_count":     result.AlternativeCount,
			"confidence":            result.Confidence,
			"verified":              result.Verified,
			"suggestion":            result.Suggestion,
		},
		"context": map[string]interface{}{
			"distribution": result.AlternativeDistribution,
			"metrics":      result.Metrics,
		},
	}

	if result.Error != "" {
		formatted["error"] = result.Error
		formatted["failure_reason"] = result.FailureReason
	}

	return formatted
}

// ========== 可扩展性支持相关方法 ==========

// getDefaultMappingConfig 获取默认映射配置
func getDefaultMappingConfig() *ResourceTypeMappingConfig {
	return &ResourceTypeMappingConfig{
		// 无「另一 rs_type 池」可枚举；与 infer_resource_type 单次 PUBLIC+归一化池一致
		Mappings: map[string][]string{
			ResourceTypeMySQL:        {},
			ResourceTypeTenDBCluster: {},
		},
		CompatibilityRules: map[string]CompatibilityRule{
			fmt.Sprintf("%s->%s", ResourceTypeMySQL, ResourceTypeTenDBCluster): {
				Level:       "high",
				Conditions:  []string{"request_alias_same_canonical_pool"},
				Limitations: []string{"库内 rs_type 已统一为 mysql；申请侧 mysql/tendbcluster 仅参数别名"},
			},
			fmt.Sprintf("%s->%s", ResourceTypeTenDBCluster, ResourceTypeMySQL): {
				Level:       "high",
				Conditions:  []string{"request_alias_same_canonical_pool"},
				Limitations: []string{"库内 rs_type 已统一为 mysql；申请侧 mysql/tendbcluster 仅参数别名"},
			},
		},
		MigrationCosts: map[string]map[string]string{
			ResourceTypeMySQL: {
				ResourceTypeTenDBCluster: "none",
			},
			ResourceTypeTenDBCluster: {
				ResourceTypeMySQL: "none",
			},
		},
		Priorities: map[string]int{
			ResourceTypeMySQL:        1,
			ResourceTypeTenDBCluster: 1,
		},
		Enabled: true,
	}
}

// RegisterResourceType 注册新的资源类型（扩展接口）
func (registry *ResourceTypeRegistry) RegisterResourceType(resourceType string, alternatives []string,
	validationRule ValidationRule, transformRule TransformRule) error {
	registry.mu.Lock()
	defer registry.mu.Unlock()

	// 验证资源类型名称
	if resourceType == "" {
		return fmt.Errorf("resource type cannot be empty")
	}

	// 添加到自定义映射
	registry.customMappings[resourceType] = alternatives
	registry.validationRules[resourceType] = validationRule
	registry.transformRules[resourceType] = transformRule

	// 更新支持的资源类型
	supportedResourceTypes[resourceType] = true
	for _, alt := range alternatives {
		supportedResourceTypes[alt] = true
	}

	return nil
}

// GetAlternativeResourceTypes 获取替代资源类型（支持一对多）
func (registry *ResourceTypeRegistry) GetAlternativeResourceTypes(currentType string) ([]string, bool) {
	registry.mu.RLock()
	defer registry.mu.RUnlock()

	// 首先检查自定义映射
	if alternatives, exists := registry.customMappings[currentType]; exists {
		return alternatives, true
	}

	// 然后检查默认配置
	if registry.mappingConfig != nil && registry.mappingConfig.Enabled {
		if alternatives, exists := registry.mappingConfig.Mappings[currentType]; exists {
			return alternatives, true
		}
	}

	// 最后检查传统映射（向后兼容）
	if alternative, exists := resourceTypeMapping[currentType]; exists {
		return []string{alternative}, true
	}

	return nil, false
}

// ValidateResourceTypeParameters 验证资源类型参数
func (registry *ResourceTypeRegistry) ValidateResourceTypeParameters(resourceType string, args map[string]interface{}) error {
	registry.mu.RLock()
	defer registry.mu.RUnlock()

	rule, exists := registry.validationRules[resourceType]
	if !exists {
		// 使用默认验证
		return validateResourceTypeInferenceParams(args)
	}

	// 检查必需字段
	for _, field := range rule.RequiredFields {
		if _, ok := args[field]; !ok {
			return fmt.Errorf("required field '%s' is missing for resource type '%s'", field, resourceType)
		}
	}

	// 执行自定义验证
	for field, validator := range rule.Validators {
		if value, ok := args[field]; ok {
			if !validator(value) {
				return fmt.Errorf("validation failed for field '%s' in resource type '%s'", field, resourceType)
			}
		}
	}

	return nil
}

// TransformParameters 转换参数（用于不同资源类型间的参数适配）
func (registry *ResourceTypeRegistry) TransformParameters(fromType, toType string, args map[string]interface{}) (map[string]interface{}, error) {
	registry.mu.RLock()
	defer registry.mu.RUnlock()

	transformRule, exists := registry.transformRules[toType]
	if !exists {
		// 没有转换规则，直接返回原参数
		return args, nil
	}

	transformed := make(map[string]interface{})

	// 复制原始参数
	for k, v := range args {
		transformed[k] = v
	}

	// 应用字段映射
	for fromField, toField := range transformRule.FieldMappings {
		if value, ok := args[fromField]; ok {
			transformed[toField] = value
			if fromField != toField {
				delete(transformed, fromField)
			}
		}
	}

	// 应用自定义转换
	for field, transformer := range transformRule.Transformers {
		if value, ok := transformed[field]; ok {
			transformed[field] = transformer(value)
		}
	}

	return transformed, nil
}

// GetCompatibilityInfo 获取兼容性信息
func (registry *ResourceTypeRegistry) GetCompatibilityInfo(fromType, toType string) (CompatibilityRule, bool) {
	registry.mu.RLock()
	defer registry.mu.RUnlock()

	if registry.mappingConfig == nil {
		return CompatibilityRule{}, false
	}

	key := fmt.Sprintf("%s->%s", fromType, toType)
	rule, exists := registry.mappingConfig.CompatibilityRules[key]
	return rule, exists
}

// UpdateMappingConfig 更新映射配置（运行时配置）
func (registry *ResourceTypeRegistry) UpdateMappingConfig(config *ResourceTypeMappingConfig) error {
	registry.mu.Lock()
	defer registry.mu.Unlock()

	if config == nil {
		return fmt.Errorf("mapping config cannot be nil")
	}

	// 验证配置
	if err := registry.validateMappingConfig(config); err != nil {
		return fmt.Errorf("invalid mapping config: %w", err)
	}

	registry.mappingConfig = config
	return nil
}

// validateMappingConfig 验证映射配置
func (registry *ResourceTypeRegistry) validateMappingConfig(config *ResourceTypeMappingConfig) error {
	// 检查映射关系的有效性
	for resourceType, alternatives := range config.Mappings {
		if resourceType == "" {
			return fmt.Errorf("empty resource type in mappings")
		}
		for _, alt := range alternatives {
			if alt == "" {
				return fmt.Errorf("empty alternative resource type for '%s'", resourceType)
			}
			if alt == resourceType {
				return fmt.Errorf("resource type '%s' cannot map to itself", resourceType)
			}
		}
	}

	// 检查兼容性规则
	for key, rule := range config.CompatibilityRules {
		if rule.Level == "" {
			return fmt.Errorf("compatibility level is required for rule '%s'", key)
		}
		validLevels := []string{"high", "medium", "low", "none"}
		isValid := false
		for _, level := range validLevels {
			if rule.Level == level {
				isValid = true
				break
			}
		}
		if !isValid {
			return fmt.Errorf("invalid compatibility level '%s' for rule '%s'", rule.Level, key)
		}
	}

	return nil
}

// GetSupportedResourceTypes 获取所有支持的资源类型
func (registry *ResourceTypeRegistry) GetSupportedResourceTypes() []string {
	registry.mu.RLock()
	defer registry.mu.RUnlock()

	types := make([]string, 0, len(supportedResourceTypes))
	for resourceType := range supportedResourceTypes {
		types = append(types, resourceType)
	}
	sort.Strings(types)
	return types
}

// extensibleInferResourceType 可扩展的资源类型推测（支持多个替代类型）。
// 当注册表未配置跨类型 alternatives（如 mysql/tendbcluster 已合并为单池）时，回退为与 infer_resource_type 相同的单次 PUBLIC+归一化池推断。
func (t *ResourceTools) extensibleInferResourceType(args map[string]interface{}) (*ResourceTypeInferenceResult, error) {
	currentType := args["current_resource_type"].(string)

	// 获取所有可能的替代资源类型
	alternatives, exists := globalResourceTypeRegistry.GetAlternativeResourceTypes(currentType)
	if !exists || len(alternatives) == 0 {
		if isResourceTypeSupported(currentType) {
			return t.inferResourceType(args)
		}
		return &ResourceTypeInferenceResult{
			CurrentResourceType: currentType,
			Error:               fmt.Sprintf("no alternative resource types found for '%s'", currentType),
			FailureReason:       "no mapping configuration",
			Verified:            true,
			Confidence:          "high",
		}, nil
	}

	// 尝试每个替代类型，选择最佳匹配
	var bestResult *ResourceTypeInferenceResult
	var bestScore float64

	for _, altType := range alternatives {
		// 转换参数以适配目标资源类型
		transformedArgs, err := globalResourceTypeRegistry.TransformParameters(currentType, altType, args)
		if err != nil {
			continue // 跳过转换失败的类型
		}

		// 更新目标资源类型
		transformedArgs["current_resource_type"] = currentType

		// 执行推测
		result, err := t.inferResourceTypeForSpecificAlternative(transformedArgs, altType)
		if err != nil {
			continue // 跳过查询失败的类型
		}

		// 计算匹配分数
		score := t.calculateMatchScore(result, currentType, altType)

		if bestResult == nil || score > bestScore {
			bestResult = result
			bestScore = score
		}
	}

	if bestResult == nil {
		return &ResourceTypeInferenceResult{
			CurrentResourceType: currentType,
			Error:               "all alternative resource types failed to query",
			FailureReason:       "query failures",
			Verified:            false,
			Confidence:          "low",
		}, nil
	}

	return bestResult, nil
}

// inferResourceTypeForSpecificAlternative 为可扩展注册表中的某一替代类型执行推测（库内 rs_type 已归一化）
func (t *ResourceTools) inferResourceTypeForSpecificAlternative(args map[string]interface{}, alternativeType string) (*ResourceTypeInferenceResult, error) {
	if err := validateResourceTypeInferenceParams(args); err != nil {
		result := &ResourceTypeInferenceResult{AlternativeDistribution: make(map[string]interface{})}
		result.Error = err.Error()
		result.Verified = false
		result.Confidence = "low"
		result.FailureReason = "parameter validation failed"
		return result, err
	}
	currentType := args["current_resource_type"].(string)
	poolRsType := model.NormalizeResourceType(alternativeType)
	return t.inferResourceTypeForApplyPool(args, currentType, poolRsType)
}

// calculateMatchScore 计算匹配分数
func (t *ResourceTools) calculateMatchScore(result *ResourceTypeInferenceResult, currentType, alternativeType string) float64 {
	score := 0.0

	// 基础可用性分数
	if result.AlternativeAvailable {
		score += 50.0
	}

	// 资源数量分数
	if result.AlternativeCount > 0 {
		score += math.Min(float64(result.AlternativeCount)/10.0*20.0, 20.0)
	}

	// 置信度分数
	switch result.Confidence {
	case "high":
		score += 20.0
	case "medium":
		score += 10.0
	case "low":
		score += 5.0
	}

	// 兼容性分数
	if compatRule, exists := globalResourceTypeRegistry.GetCompatibilityInfo(currentType, alternativeType); exists {
		switch compatRule.Level {
		case "high":
			score += 10.0
		case "medium":
			score += 5.0
		case "low":
			score += 2.0
		}
	}

	return score
}
