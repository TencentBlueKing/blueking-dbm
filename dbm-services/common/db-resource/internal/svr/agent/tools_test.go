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
	"reflect"
	"testing"
	"time"

	"github.com/DATA-DOG/go-sqlmock"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/bk"
)

// setupTestDB 设置测试数据库
func setupTestDB(t *testing.T) (*gorm.DB, sqlmock.Sqlmock) {
	db, mock, err := sqlmock.New()
	require.NoError(t, err)

	gormDB, err := gorm.Open(mysql.New(mysql.Config{
		Conn:                      db,
		SkipInitializeWithVersion: true,
	}), &gorm.Config{
		Logger: logger.Default.LogMode(logger.Silent),
	})
	require.NoError(t, err)

	return gormDB, mock
}

// TestResourceTools_InferResourceType tests the core inference logic
func TestResourceTools_InferResourceType(t *testing.T) {
	tests := []struct {
		name           string
		args           map[string]interface{}
		mockSetup      func(sqlmock.Sqlmock)
		expectedResult func(*testing.T, *ResourceTypeInferenceResult, error)
	}{
		{
			name: "MySQL to TenDBCluster - Success with available resources",
			args: map[string]interface{}{
				"current_resource_type": "mysql",
				"bk_cloud_id":           float64(0),
				"city":                  "深圳",
			},
			mockSetup: func(mock sqlmock.Sqlmock) {
				// Mock count query
				mock.ExpectQuery("SELECT count\\(\\*\\) FROM `tb_rp_detail`").
					WithArgs(0, model.Unused, bk.GseAlive, "tendbcluster", "深圳").
					WillReturnRows(sqlmock.NewRows([]string{"count"}).AddRow(5))

				// Mock distribution query - sub zone stats
				mock.ExpectQuery("SELECT sub_zone_id as sub_zone, city, count\\(\\*\\) as count FROM `tb_rp_detail`").
					WillReturnRows(sqlmock.NewRows([]string{"sub_zone", "city", "count"}).
						AddRow("深圳-深宇(1109)", "深圳", 3).
						AddRow("深圳-南山(1110)", "深圳", 2))

				// Mock distribution query - device class stats
				mock.ExpectQuery("SELECT device_class, count\\(\\*\\) as count FROM `tb_rp_detail`").
					WillReturnRows(sqlmock.NewRows([]string{"device_class", "count"}).
						AddRow("S5.MEDIUM8", 3).
						AddRow("S5.LARGE16", 2))

				// Mock verification queries - these are executed by verifyInferenceResult
				// Since no sub_zone_ids are specified in args, no additional verification queries are expected
			},
			expectedResult: func(t *testing.T, result *ResourceTypeInferenceResult, err error) {
				assert.NoError(t, err)
				assert.NotNil(t, result)
				assert.Equal(t, "mysql", result.CurrentResourceType)
				assert.Equal(t, "tendbcluster", result.AlternativeResourceType)
				assert.True(t, result.AlternativeAvailable)
				assert.Equal(t, 5, result.AlternativeCount)
				assert.True(t, result.Verified)
				assert.Equal(t, "high", result.Confidence)
				assert.Contains(t, result.Suggestion, "强烈建议")
			},
		},
		{
			name: "TenDBCluster to MySQL - Success with available resources",
			args: map[string]interface{}{
				"current_resource_type": "tendbcluster",
				"bk_cloud_id":           float64(0),
				"cpu_min":               float64(4),
				"cpu_max":               float64(8),
				"mem_min":               float64(8192),
			},
			mockSetup: func(mock sqlmock.Sqlmock) {
				// Mock count query
				mock.ExpectQuery("SELECT count\\(\\*\\) FROM `tb_rp_detail`").
					WithArgs(0, model.Unused, bk.GseAlive, "mysql", 4, 8, 8192).
					WillReturnRows(sqlmock.NewRows([]string{"count"}).AddRow(10))

				// Mock distribution queries
				mock.ExpectQuery("SELECT sub_zone_id as sub_zone, city, count\\(\\*\\) as count FROM `tb_rp_detail`").
					WillReturnRows(sqlmock.NewRows([]string{"sub_zone", "city", "count"}).
						AddRow("默认园区", "默认", 10))

				mock.ExpectQuery("SELECT device_class, count\\(\\*\\) as count FROM `tb_rp_detail`").
					WillReturnRows(sqlmock.NewRows([]string{"device_class", "count"}).
						AddRow("S5.MEDIUM8", 10))

				// No additional verification queries needed for this test case
			},
			expectedResult: func(t *testing.T, result *ResourceTypeInferenceResult, err error) {
				assert.NoError(t, err)
				assert.NotNil(t, result)
				assert.Equal(t, "tendbcluster", result.CurrentResourceType)
				assert.Equal(t, "mysql", result.AlternativeResourceType)
				assert.True(t, result.AlternativeAvailable)
				assert.Equal(t, 10, result.AlternativeCount)
			},
		},
		{
			name: "No available resources in alternative type",
			args: map[string]interface{}{
				"current_resource_type": "mysql",
				"bk_cloud_id":           float64(0),
			},
			mockSetup: func(mock sqlmock.Sqlmock) {
				// Mock count query returning 0
				mock.ExpectQuery("SELECT count\\(\\*\\) FROM `tb_rp_detail`").
					WithArgs(0, model.Unused, bk.GseAlive, "tendbcluster").
					WillReturnRows(sqlmock.NewRows([]string{"count"}).AddRow(0))
			},
			expectedResult: func(t *testing.T, result *ResourceTypeInferenceResult, err error) {
				assert.NoError(t, err)
				assert.NotNil(t, result)
				assert.Equal(t, "mysql", result.CurrentResourceType)
				assert.Equal(t, "tendbcluster", result.AlternativeResourceType)
				assert.False(t, result.AlternativeAvailable)
				assert.Equal(t, 0, result.AlternativeCount)
				assert.Contains(t, result.Suggestion, "没有符合条件的可用资源")
				assert.Equal(t, "both resource types have no available resources matching the criteria", result.FailureReason)
			},
		},
		{
			name: "Invalid resource type",
			args: map[string]interface{}{
				"current_resource_type": "invalid_type",
				"bk_cloud_id":           float64(0),
			},
			mockSetup: func(mock sqlmock.Sqlmock) {
				// No mock setup needed as validation should fail first
			},
			expectedResult: func(t *testing.T, result *ResourceTypeInferenceResult, err error) {
				assert.Error(t, err)
				assert.NotNil(t, result)
				assert.Contains(t, result.Error, "not supported for inference")
				assert.False(t, result.Verified)
				assert.Equal(t, "low", result.Confidence)
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			db, mock := setupTestDB(t)
			defer func() {
				sqlDB, _ := db.DB()
				sqlDB.Close()
			}()

			tt.mockSetup(mock)

			tools := &ResourceTools{db: db}
			result, err := tools.inferResourceType(tt.args)

			tt.expectedResult(t, result, err)

			// Verify all expectations were met
			assert.NoError(t, mock.ExpectationsWereMet())
		})
	}
}

// TestValidateResourceTypeInferenceParams tests parameter validation
func TestValidateResourceTypeInferenceParams(t *testing.T) {
	tests := []struct {
		name        string
		args        map[string]interface{}
		expectError bool
		errorMsg    string
	}{
		{
			name: "Valid parameters",
			args: map[string]interface{}{
				"current_resource_type": "mysql",
				"bk_cloud_id":           float64(0),
			},
			expectError: false,
		},
		{
			name: "Missing current_resource_type",
			args: map[string]interface{}{
				"bk_cloud_id": float64(0),
			},
			expectError: true,
			errorMsg:    "current_resource_type is required",
		},
		{
			name: "Missing bk_cloud_id",
			args: map[string]interface{}{
				"current_resource_type": "mysql",
			},
			expectError: true,
			errorMsg:    "bk_cloud_id is required",
		},
		{
			name: "Invalid resource type",
			args: map[string]interface{}{
				"current_resource_type": "invalid",
				"bk_cloud_id":           float64(0),
			},
			expectError: true,
			errorMsg:    "not supported for inference",
		},
		{
			name: "Negative cloud ID",
			args: map[string]interface{}{
				"current_resource_type": "mysql",
				"bk_cloud_id":           float64(-1),
			},
			expectError: true,
			errorMsg:    "must be non-negative",
		},
		{
			name: "Invalid CPU range",
			args: map[string]interface{}{
				"current_resource_type": "mysql",
				"bk_cloud_id":           float64(0),
				"cpu_min":               float64(8),
				"cpu_max":               float64(4),
			},
			expectError: true,
			errorMsg:    "cannot be greater than cpu_max",
		},
		{
			name: "Invalid memory range",
			args: map[string]interface{}{
				"current_resource_type": "mysql",
				"bk_cloud_id":           float64(0),
				"mem_min":               float64(16384),
				"mem_max":               float64(8192),
			},
			expectError: true,
			errorMsg:    "cannot be greater than mem_max",
		},
		{
			name: "Too many sub zones",
			args: map[string]interface{}{
				"current_resource_type": "mysql",
				"bk_cloud_id":           float64(0),
				"sub_zone_ids":          make([]interface{}, 51), // More than limit
			},
			expectError: true,
			errorMsg:    "too many sub_zone_ids",
		},
		{
			name: "Invalid disk spec",
			args: map[string]interface{}{
				"current_resource_type": "mysql",
				"bk_cloud_id":           float64(0),
				"disk_specs": []interface{}{
					map[string]interface{}{
						"mount_point": "/data",
						"min_size":    float64(1000),
						"max_size":    float64(500), // max < min
					},
				},
			},
			expectError: true,
			errorMsg:    "cannot be greater than max_size",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := validateResourceTypeInferenceParams(tt.args)
			if tt.expectError {
				assert.Error(t, err)
				assert.Contains(t, err.Error(), tt.errorMsg)
			} else {
				assert.NoError(t, err)
			}
		})
	}
}

// TestResourceTypeMapping tests resource type mapping functions
func TestResourceTypeMapping(t *testing.T) {
	tests := []struct {
		name         string
		resourceType string
		expected     string
		shouldExist  bool
	}{
		{
			name:         "MySQL to TenDBCluster",
			resourceType: "mysql",
			expected:     "tendbcluster",
			shouldExist:  true,
		},
		{
			name:         "TenDBCluster to MySQL",
			resourceType: "tendbcluster",
			expected:     "mysql",
			shouldExist:  true,
		},
		{
			name:         "Unknown resource type",
			resourceType: "unknown",
			expected:     "",
			shouldExist:  false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, exists := getAlternativeResourceType(tt.resourceType)
			assert.Equal(t, tt.shouldExist, exists)
			if tt.shouldExist {
				assert.Equal(t, tt.expected, result)
			}
		})
	}
}

// TestIsResourceTypeSupported tests resource type support checking
func TestIsResourceTypeSupported(t *testing.T) {
	tests := []struct {
		name         string
		resourceType string
		expected     bool
	}{
		{"MySQL supported", "mysql", true},
		{"TenDBCluster supported", "tendbcluster", true},
		{"Unknown not supported", "unknown", false},
		{"Empty not supported", "", false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := isResourceTypeSupported(tt.resourceType)
			assert.Equal(t, tt.expected, result)
		})
	}
}

// TestQueryOptimizer tests the query optimization functionality
func TestQueryOptimizer(t *testing.T) {
	t.Run("Cache functionality", func(t *testing.T) {
		optimizer := &QueryOptimizer{
			queryCache:        make(map[string]*CachedQueryResult),
			concurrentQueries: make(chan struct{}, 5),
		}

		// Test cache miss
		result, found := optimizer.getCachedResult("test-hash")
		assert.False(t, found)
		assert.Nil(t, result)

		// Test cache set and hit
		testResult := &ResourceTypeInferenceResult{
			CurrentResourceType:     "mysql",
			AlternativeResourceType: "tendbcluster",
			AlternativeAvailable:    true,
			AlternativeCount:        5,
		}

		optimizer.setCachedResult("test-hash", testResult)

		result, found = optimizer.getCachedResult("test-hash")
		assert.True(t, found)
		assert.NotNil(t, result)
		assert.Equal(t, "mysql", result.CurrentResourceType)
	})

	t.Run("Concurrent query slots", func(t *testing.T) {
		optimizer := &QueryOptimizer{
			queryCache:        make(map[string]*CachedQueryResult),
			concurrentQueries: make(chan struct{}, 2), // Small limit for testing
		}

		ctx := context.Background()

		// Acquire first slot
		err := optimizer.acquireQuerySlot(ctx)
		assert.NoError(t, err)

		// Acquire second slot
		err = optimizer.acquireQuerySlot(ctx)
		assert.NoError(t, err)

		// Third slot should timeout
		ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
		defer cancel()
		err = optimizer.acquireQuerySlot(ctx)
		assert.Error(t, err)
		assert.Equal(t, context.DeadlineExceeded, err)

		// Release slots
		optimizer.releaseQuerySlot()
		optimizer.releaseQuerySlot()

		// Should be able to acquire again
		ctx = context.Background()
		err = optimizer.acquireQuerySlot(ctx)
		assert.NoError(t, err)
		optimizer.releaseQuerySlot()
	})
}

// TestStandardAnalysisResult tests the standard result format conversion
func TestStandardAnalysisResult(t *testing.T) {
	result := &ResourceTypeInferenceResult{
		CurrentResourceType:     "mysql",
		AlternativeResourceType: "tendbcluster",
		AlternativeAvailable:    true,
		AlternativeCount:        5,
		Verified:                true,
		Confidence:              "high",
		Suggestion:              "建议使用 tendbcluster",
		Metrics: &QueryMetrics{
			QueryDuration: 100 * time.Millisecond,
			CacheHit:      false,
		},
	}

	standardResult := result.toStandardAnalysisResult()

	assert.Equal(t, "resource_type_inference", standardResult.AnalysisType)
	assert.Equal(t, "success", standardResult.Status)
	assert.Contains(t, standardResult.Summary, "tendbcluster")
	assert.Contains(t, standardResult.Summary, "5 台可用资源")
	assert.Equal(t, "high", standardResult.Metadata.Confidence)
	assert.True(t, len(standardResult.Recommendations) > 0)

	// Check recommendation
	rec := standardResult.Recommendations[0]
	assert.Equal(t, "resource_type_change", rec.Type)
	assert.Contains(t, rec.Title, "tendbcluster")
}

// TestExtensibleResourceTypeRegistry tests the extensible registry functionality
func TestExtensibleResourceTypeRegistry(t *testing.T) {
	registry := &ResourceTypeRegistry{
		mappingConfig:   getDefaultMappingConfig(),
		customMappings:  make(map[string][]string),
		validationRules: make(map[string]ValidationRule),
		transformRules:  make(map[string]TransformRule),
	}

	t.Run("Register new resource type", func(t *testing.T) {
		err := registry.RegisterResourceType(
			"postgresql",
			[]string{"mysql", "tendbcluster"},
			ValidationRule{RequiredFields: []string{"current_resource_type", "bk_cloud_id"}},
			TransformRule{FieldMappings: map[string]string{"pg_version": "version"}},
		)
		assert.NoError(t, err)

		// Test retrieval
		alternatives, exists := registry.GetAlternativeResourceTypes("postgresql")
		assert.True(t, exists)
		assert.Contains(t, alternatives, "mysql")
		assert.Contains(t, alternatives, "tendbcluster")
	})

	t.Run("Get compatibility info", func(t *testing.T) {
		rule, exists := registry.GetCompatibilityInfo("mysql", "tendbcluster")
		assert.True(t, exists)
		assert.Equal(t, "high", rule.Level)
	})

	t.Run("Update mapping config", func(t *testing.T) {
		newConfig := &ResourceTypeMappingConfig{
			Mappings: map[string][]string{
				"mysql": {"tendbcluster", "postgresql"},
			},
			CompatibilityRules: map[string]CompatibilityRule{
				"mysql->postgresql": {
					Level:      "medium",
					Conditions: []string{"version_compatible"},
				},
			},
			MigrationCosts: map[string]map[string]string{
				"mysql": {"postgresql": "medium"},
			},
			Priorities: map[string]int{"mysql": 1, "postgresql": 2},
			Enabled:    true,
		}

		err := registry.UpdateMappingConfig(newConfig)
		assert.NoError(t, err)

		// Verify update
		alternatives, exists := registry.GetAlternativeResourceTypes("mysql")
		assert.True(t, exists)
		assert.Contains(t, alternatives, "postgresql")
	})
}

// TestDiskSpecValidation tests disk specification validation
func TestDiskSpecValidation(t *testing.T) {
	tests := []struct {
		name        string
		spec        map[string]interface{}
		index       int
		expectError bool
		errorMsg    string
	}{
		{
			name: "Valid disk spec",
			spec: map[string]interface{}{
				"mount_point": "/data",
				"disk_type":   "SSD",
				"min_size":    float64(100),
				"max_size":    float64(500),
			},
			index:       0,
			expectError: false,
		},
		{
			name: "Missing mount point",
			spec: map[string]interface{}{
				"disk_type": "SSD",
			},
			index:       0,
			expectError: true,
			errorMsg:    "mount_point is required",
		},
		{
			name: "Invalid disk type",
			spec: map[string]interface{}{
				"mount_point": "/data",
				"disk_type":   "INVALID_TYPE",
			},
			index:       0,
			expectError: true,
			errorMsg:    "is not supported",
		},
		{
			name: "Invalid size range",
			spec: map[string]interface{}{
				"mount_point": "/data",
				"min_size":    float64(500),
				"max_size":    float64(100),
			},
			index:       0,
			expectError: true,
			errorMsg:    "cannot be greater than max_size",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := validateDiskSpec(tt.spec, tt.index)
			if tt.expectError {
				assert.Error(t, err)
				assert.Contains(t, err.Error(), tt.errorMsg)
			} else {
				assert.NoError(t, err)
			}
		})
	}
}

// TestGenerateQueryHash tests query hash generation
func TestGenerateQueryHash(t *testing.T) {
	args1 := map[string]interface{}{
		"current_resource_type": "mysql",
		"bk_cloud_id":           float64(0),
		"city":                  "深圳",
	}

	args2 := map[string]interface{}{
		"bk_cloud_id":           float64(0),
		"current_resource_type": "mysql",
		"city":                  "深圳",
	}

	args3 := map[string]interface{}{
		"current_resource_type": "mysql",
		"bk_cloud_id":           float64(0),
		"city":                  "北京",
	}

	hash1 := generateQueryHash(args1)
	hash2 := generateQueryHash(args2)
	hash3 := generateQueryHash(args3)

	// Same parameters should generate same hash regardless of order
	assert.Equal(t, hash1, hash2)

	// Different parameters should generate different hash
	assert.NotEqual(t, hash1, hash3)

	// Hash should be 16 characters
	assert.Len(t, hash1, 16)
}

// TestParseDiskSpecs_NewFormat tests parseDiskSpecs with the new disk_specs array format
func TestParseDiskSpecs_NewFormat(t *testing.T) {
	args := map[string]interface{}{
		"disk_specs": []interface{}{
			map[string]interface{}{
				"mount_point": "/data",
				"disk_type":   "SSD",
				"min_size":    float64(100),
				"max_size":    float64(500),
			},
			map[string]interface{}{
				"mount_point": "/data1",
				"disk_type":   "HDD",
				"min_size":    float64(200),
			},
		},
	}

	specs := parseDiskSpecs(args)

	if len(specs) != 2 {
		t.Errorf("Expected 2 specs, got %d", len(specs))
	}

	// Check first spec
	if specs[0].MountPoint != "/data" {
		t.Errorf("Expected mount_point /data, got %s", specs[0].MountPoint)
	}
	if specs[0].DiskType != "SSD" {
		t.Errorf("Expected disk_type SSD, got %s", specs[0].DiskType)
	}
	if specs[0].MinSize != 100 {
		t.Errorf("Expected min_size 100, got %d", specs[0].MinSize)
	}
	if specs[0].MaxSize != 500 {
		t.Errorf("Expected max_size 500, got %d", specs[0].MaxSize)
	}

	// Check second spec
	if specs[1].MountPoint != "/data1" {
		t.Errorf("Expected mount_point /data1, got %s", specs[1].MountPoint)
	}
	if specs[1].DiskType != "HDD" {
		t.Errorf("Expected disk_type HDD, got %s", specs[1].DiskType)
	}
	if specs[1].MinSize != 200 {
		t.Errorf("Expected min_size 200, got %d", specs[1].MinSize)
	}
	if specs[1].MaxSize != 0 {
		t.Errorf("Expected max_size 0, got %d", specs[1].MaxSize)
	}
}

// TestParseDiskSpecs_OldFormat tests parseDiskSpecs with the old single disk parameter format
func TestParseDiskSpecs_OldFormat(t *testing.T) {
	args := map[string]interface{}{
		"disk_mount_point": "/data",
		"disk_type":        "CLOUD_SSD",
		"disk_min_size":    float64(100),
		"disk_max_size":    float64(500),
	}

	specs := parseDiskSpecs(args)

	if len(specs) != 1 {
		t.Errorf("Expected 1 spec, got %d", len(specs))
	}

	if specs[0].MountPoint != "/data" {
		t.Errorf("Expected mount_point /data, got %s", specs[0].MountPoint)
	}
	if specs[0].DiskType != "CLOUD_SSD" {
		t.Errorf("Expected disk_type CLOUD_SSD, got %s", specs[0].DiskType)
	}
	if specs[0].MinSize != 100 {
		t.Errorf("Expected min_size 100, got %d", specs[0].MinSize)
	}
	if specs[0].MaxSize != 500 {
		t.Errorf("Expected max_size 500, got %d", specs[0].MaxSize)
	}
}

// TestParseDiskSpecs_AlternativeOldFormat tests parseDiskSpecs with alternative old format (mount_point/min_size/max_size)
func TestParseDiskSpecs_AlternativeOldFormat(t *testing.T) {
	args := map[string]interface{}{
		"mount_point": "/data",
		"disk_type":   "HDD",
		"min_size":    float64(200),
		"max_size":    float64(1000),
	}

	specs := parseDiskSpecs(args)

	if len(specs) != 1 {
		t.Errorf("Expected 1 spec, got %d", len(specs))
	}

	if specs[0].MountPoint != "/data" {
		t.Errorf("Expected mount_point /data, got %s", specs[0].MountPoint)
	}
	if specs[0].MinSize != 200 {
		t.Errorf("Expected min_size 200, got %d", specs[0].MinSize)
	}
	if specs[0].MaxSize != 1000 {
		t.Errorf("Expected max_size 1000, got %d", specs[0].MaxSize)
	}
}

// TestParseDiskSpecs_NewFormatTakesPrecedence tests that new format takes precedence over old format
func TestParseDiskSpecs_NewFormatTakesPrecedence(t *testing.T) {
	args := map[string]interface{}{
		// New format
		"disk_specs": []interface{}{
			map[string]interface{}{
				"mount_point": "/data_new",
				"disk_type":   "SSD",
				"min_size":    float64(300),
			},
		},
		// Old format (should be ignored)
		"disk_mount_point": "/data_old",
		"disk_type":        "HDD",
		"disk_min_size":    float64(100),
	}

	specs := parseDiskSpecs(args)

	if len(specs) != 1 {
		t.Errorf("Expected 1 spec (new format), got %d", len(specs))
	}

	if specs[0].MountPoint != "/data_new" {
		t.Errorf("Expected mount_point /data_new (from new format), got %s", specs[0].MountPoint)
	}
}

// TestParseDiskSpecs_EmptyArgs tests parseDiskSpecs with empty arguments
func TestParseDiskSpecs_EmptyArgs(t *testing.T) {
	args := map[string]interface{}{}

	specs := parseDiskSpecs(args)

	if len(specs) != 0 {
		t.Errorf("Expected 0 specs, got %d", len(specs))
	}
}

// TestParseDiskSpecs_EmptyMountPoint tests parseDiskSpecs filters out specs with empty mount_point
func TestParseDiskSpecs_EmptyMountPoint(t *testing.T) {
	args := map[string]interface{}{
		"disk_specs": []interface{}{
			map[string]interface{}{
				"mount_point": "",
				"disk_type":   "SSD",
				"min_size":    float64(100),
			},
			map[string]interface{}{
				"mount_point": "/data",
				"disk_type":   "HDD",
				"min_size":    float64(200),
			},
		},
	}

	specs := parseDiskSpecs(args)

	if len(specs) != 1 {
		t.Errorf("Expected 1 spec (empty mount_point filtered), got %d", len(specs))
	}

	if specs[0].MountPoint != "/data" {
		t.Errorf("Expected mount_point /data, got %s", specs[0].MountPoint)
	}
}

// TestBuildDiskConditionsSQL_SingleDisk tests buildDiskConditionsSQL with a single disk spec
func TestBuildDiskConditionsSQL_SingleDisk(t *testing.T) {
	specs := []DiskSpec{
		{
			MountPoint: "/data",
			DiskType:   "SSD",
			MinSize:    100,
			MaxSize:    500,
		},
	}

	conditions, args := buildDiskConditionsSQL(specs)

	// Expect 3 conditions: mount point exists, disk type, size range
	if len(conditions) != 3 {
		t.Errorf("Expected 3 conditions, got %d", len(conditions))
	}

	// Expect 3 args: disk_type, min_size, max_size
	if len(args) != 3 {
		t.Errorf("Expected 3 args, got %d", len(args))
	}

	if args[0] != "SSD" {
		t.Errorf("Expected first arg to be SSD, got %v", args[0])
	}
	if args[1] != 100 {
		t.Errorf("Expected second arg to be 100, got %v", args[1])
	}
	if args[2] != 500 {
		t.Errorf("Expected third arg to be 500, got %v", args[2])
	}
}

// TestBuildDiskConditionsSQL_MultipleDisk tests buildDiskConditionsSQL with multiple disk specs
func TestBuildDiskConditionsSQL_MultipleDisk(t *testing.T) {
	specs := []DiskSpec{
		{
			MountPoint: "/data",
			DiskType:   "SSD",
			MinSize:    100,
		},
		{
			MountPoint: "/data1",
			DiskType:   "HDD",
			MinSize:    200,
		},
	}

	conditions, args := buildDiskConditionsSQL(specs)

	// Each spec generates: mount point exists + type + min_size
	// First spec: 3 conditions (exists, type, min_size), 2 args (type, min_size)
	// Second spec: 3 conditions (exists, type, min_size), 2 args (type, min_size)
	// Total: 6 conditions, 4 args
	if len(conditions) != 6 {
		t.Errorf("Expected 6 conditions, got %d", len(conditions))
	}

	if len(args) != 4 {
		t.Errorf("Expected 4 args, got %d", len(args))
	}
}

// TestBuildDiskConditionsSQL_OnlyMinSize tests buildDiskConditionsSQL with only min_size specified
func TestBuildDiskConditionsSQL_OnlyMinSize(t *testing.T) {
	specs := []DiskSpec{
		{
			MountPoint: "/data",
			MinSize:    100,
		},
	}

	conditions, args := buildDiskConditionsSQL(specs)

	// Expect 2 conditions: mount point exists, size >= min_size
	if len(conditions) != 2 {
		t.Errorf("Expected 2 conditions, got %d", len(conditions))
	}

	// Expect 1 arg: min_size
	if len(args) != 1 {
		t.Errorf("Expected 1 arg, got %d", len(args))
	}

	if args[0] != 100 {
		t.Errorf("Expected first arg to be 100, got %v", args[0])
	}
}

// TestBuildDiskConditionsSQL_OnlyMaxSize tests buildDiskConditionsSQL with only max_size specified
func TestBuildDiskConditionsSQL_OnlyMaxSize(t *testing.T) {
	specs := []DiskSpec{
		{
			MountPoint: "/data",
			MaxSize:    500,
		},
	}

	conditions, args := buildDiskConditionsSQL(specs)

	// Expect 2 conditions: mount point exists, size <= max_size
	if len(conditions) != 2 {
		t.Errorf("Expected 2 conditions, got %d", len(conditions))
	}

	// Expect 1 arg: max_size
	if len(args) != 1 {
		t.Errorf("Expected 1 arg, got %d", len(args))
	}

	if args[0] != 500 {
		t.Errorf("Expected first arg to be 500, got %v", args[0])
	}
}

// TestBuildDiskConditionsSQL_AllDiskType tests that disk_type "ALL" is not added to conditions
func TestBuildDiskConditionsSQL_AllDiskType(t *testing.T) {
	specs := []DiskSpec{
		{
			MountPoint: "/data",
			DiskType:   "ALL",
			MinSize:    100,
		},
	}

	conditions, args := buildDiskConditionsSQL(specs)

	// Expect 2 conditions: mount point exists, min_size (no disk_type)
	if len(conditions) != 2 {
		t.Errorf("Expected 2 conditions (disk_type ALL should be ignored), got %d", len(conditions))
	}

	// Expect 1 arg: min_size (no disk_type)
	if len(args) != 1 {
		t.Errorf("Expected 1 arg, got %d", len(args))
	}
}

// TestBuildDiskConditionsSQL_EmptySpecs tests buildDiskConditionsSQL with empty specs
func TestBuildDiskConditionsSQL_EmptySpecs(t *testing.T) {
	specs := []DiskSpec{}

	conditions, args := buildDiskConditionsSQL(specs)

	if len(conditions) != 0 {
		t.Errorf("Expected 0 conditions, got %d", len(conditions))
	}

	if len(args) != 0 {
		t.Errorf("Expected 0 args, got %d", len(args))
	}
}

// TestDiskSpec_Struct tests DiskSpec struct fields
func TestDiskSpec_Struct(t *testing.T) {
	spec := DiskSpec{
		MountPoint: "/data",
		DiskType:   "CLOUD_SSD",
		MinSize:    100,
		MaxSize:    500,
	}

	if spec.MountPoint != "/data" {
		t.Errorf("Expected MountPoint /data, got %s", spec.MountPoint)
	}
	if spec.DiskType != "CLOUD_SSD" {
		t.Errorf("Expected DiskType CLOUD_SSD, got %s", spec.DiskType)
	}
	if spec.MinSize != 100 {
		t.Errorf("Expected MinSize 100, got %d", spec.MinSize)
	}
	if spec.MaxSize != 500 {
		t.Errorf("Expected MaxSize 500, got %d", spec.MaxSize)
	}
}

// TestDiskParamDefs tests diskParamDefs returns correct parameter definitions
func TestDiskParamDefs(t *testing.T) {
	params := diskParamDefs()

	expectedKeys := []string{"disk_mount_point", "disk_type", "disk_min_size", "disk_max_size"}
	for _, key := range expectedKeys {
		if _, ok := params[key]; !ok {
			t.Errorf("Expected key %s in diskParamDefs, but not found", key)
		}
	}
}

// TestDiskSpecParamDefs tests diskSpecParamDefs returns correct parameter definitions
func TestDiskSpecParamDefs(t *testing.T) {
	params := diskSpecParamDefs()

	if _, ok := params["disk_specs"]; !ok {
		t.Errorf("Expected key disk_specs in diskSpecParamDefs, but not found")
	}

	diskSpecs, ok := params["disk_specs"].(map[string]interface{})
	if !ok {
		t.Errorf("disk_specs should be a map")
	}

	if diskSpecs["type"] != "array" {
		t.Errorf("Expected disk_specs type to be array, got %v", diskSpecs["type"])
	}
}

// TestMergeParams tests mergeParams merges multiple parameter maps correctly
func TestMergeParams(t *testing.T) {
	map1 := map[string]interface{}{
		"key1": "value1",
		"key2": "value2",
	}
	map2 := map[string]interface{}{
		"key3": "value3",
		"key4": "value4",
	}
	map3 := map[string]interface{}{
		"key2": "value2_overwritten",
		"key5": "value5",
	}

	merged := mergeParams(map1, map2, map3)

	if merged["key1"] != "value1" {
		t.Errorf("Expected key1=value1, got %v", merged["key1"])
	}
	if merged["key2"] != "value2_overwritten" {
		t.Errorf("Expected key2=value2_overwritten, got %v", merged["key2"])
	}
	if merged["key3"] != "value3" {
		t.Errorf("Expected key3=value3, got %v", merged["key3"])
	}
	if merged["key4"] != "value4" {
		t.Errorf("Expected key4=value4, got %v", merged["key4"])
	}
	if merged["key5"] != "value5" {
		t.Errorf("Expected key5=value5, got %v", merged["key5"])
	}
}

// TestDiskMatchResult_Struct tests DiskMatchResult struct fields
func TestDiskMatchResult_Struct(t *testing.T) {
	result := DiskMatchResult{
		MountPoint:    "/data",
		Exists:        true,
		TypeMatched:   true,
		SizeMatched:   true,
		MatchedCount:  10,
		RequiredType:  "SSD",
		RequiredSize:  100,
		FailureReason: "",
	}

	if result.MountPoint != "/data" {
		t.Errorf("Expected MountPoint /data, got %s", result.MountPoint)
	}
	if !result.Exists {
		t.Errorf("Expected Exists true, got false")
	}
	if !result.TypeMatched {
		t.Errorf("Expected TypeMatched true, got false")
	}
	if !result.SizeMatched {
		t.Errorf("Expected SizeMatched true, got false")
	}
	if result.MatchedCount != 10 {
		t.Errorf("Expected MatchedCount 10, got %d", result.MatchedCount)
	}
	if result.FailureReason != "" {
		t.Errorf("Expected FailureReason empty, got %s", result.FailureReason)
	}
}

// TestVerifyPredictionResult_Struct tests VerifyPredictionResult struct fields
func TestVerifyPredictionResult_Struct(t *testing.T) {
	result := VerifyPredictionResult{
		ActualCount:    50,
		QueryUsed:      "test query",
		SQL:            "SELECT * FROM tb_rp_detail",
		Verified:       true,
		RequestCount:   30,
		SuggestionType: "add_resources",
		Reason:         "可用资源数(50)满足申请需求(30)",
		Confidence:     "high",
	}

	if result.ActualCount != 50 {
		t.Errorf("Expected ActualCount 50, got %d", result.ActualCount)
	}
	if !result.Verified {
		t.Errorf("Expected Verified true, got false")
	}
	if result.RequestCount != 30 {
		t.Errorf("Expected RequestCount 30, got %d", result.RequestCount)
	}
	if result.SuggestionType != "add_resources" {
		t.Errorf("Expected SuggestionType add_resources, got %s", result.SuggestionType)
	}
	if result.Confidence != "high" {
		t.Errorf("Expected Confidence high, got %s", result.Confidence)
	}
}

// TestDiskAnalysisResult_Struct tests DiskAnalysisResult struct fields
func TestDiskAnalysisResult_Struct(t *testing.T) {
	result := DiskAnalysisResult{
		TotalMachines:        100,
		WithMountPoint:       80,
		WithCorrectType:      60,
		WithEnoughSize:       50,
		MaxAvailableSize:     500,
		DiskTypeDistribution: map[string]int{"SSD": 40, "HDD": 20},
		IssueType:            "disk_size_insufficient",
		IssueDetail:          "test issue",
		Suggestion:           "test suggestion",
		AllDisksMatched:      45,
	}

	if result.TotalMachines != 100 {
		t.Errorf("Expected TotalMachines 100, got %d", result.TotalMachines)
	}
	if result.WithMountPoint != 80 {
		t.Errorf("Expected WithMountPoint 80, got %d", result.WithMountPoint)
	}
	if result.AllDisksMatched != 45 {
		t.Errorf("Expected AllDisksMatched 45, got %d", result.AllDisksMatched)
	}
	if result.DiskTypeDistribution["SSD"] != 40 {
		t.Errorf("Expected SSD count 40, got %d", result.DiskTypeDistribution["SSD"])
	}
}

// TestDiskStatistics_Struct tests DiskStatistics struct fields
func TestDiskStatistics_Struct(t *testing.T) {
	stats := DiskStatistics{
		MountPoint:           "/data",
		WithMountPoint:       50,
		WithCorrectType:      40,
		WithEnoughSize:       30,
		MaxAvailableSize:     500,
		DiskTypeDistribution: map[string]int{"SSD": 30, "HDD": 10},
	}

	if stats.MountPoint != "/data" {
		t.Errorf("Expected MountPoint /data, got %s", stats.MountPoint)
	}
	if stats.WithMountPoint != 50 {
		t.Errorf("Expected WithMountPoint 50, got %d", stats.WithMountPoint)
	}
	if stats.WithCorrectType != 40 {
		t.Errorf("Expected WithCorrectType 40, got %d", stats.WithCorrectType)
	}
	if stats.WithEnoughSize != 30 {
		t.Errorf("Expected WithEnoughSize 30, got %d", stats.WithEnoughSize)
	}
}

// TestParseDiskSpecs_TypedSlice tests parseDiskSpecs with typed DiskSpec slice (edge case)
func TestParseDiskSpecs_TypedSlice(t *testing.T) {
	// This tests the edge case where disk_specs is already a []DiskSpec
	specs := []DiskSpec{
		{
			MountPoint: "/data",
			DiskType:   "SSD",
			MinSize:    100,
		},
	}

	args := map[string]interface{}{
		"disk_specs": specs,
	}

	result := parseDiskSpecs(args)

	if !reflect.DeepEqual(result, specs) {
		t.Errorf("Expected specs to be returned as-is, got %v", result)
	}
}

// TestFormatSubZoneDisplay tests the formatSubZoneDisplay function
func TestFormatSubZoneDisplay(t *testing.T) {
	tests := []struct {
		name      string
		city      string
		subZone   string
		subZoneID string
		expected  string
	}{
		{
			name:      "full info - city, subzone and id",
			city:      "深圳",
			subZone:   "光明",
			subZoneID: "268",
			expected:  "深圳-光明(268)",
		},
		{
			name:      "only subzone and id",
			city:      "",
			subZone:   "光明",
			subZoneID: "268",
			expected:  "光明(268)",
		},
		{
			name:      "only city and id",
			city:      "深圳",
			subZone:   "",
			subZoneID: "268",
			expected:  "深圳(268)",
		},
		{
			name:      "only id",
			city:      "",
			subZone:   "",
			subZoneID: "268",
			expected:  "268",
		},
		{
			name:      "empty id",
			city:      "深圳",
			subZone:   "光明",
			subZoneID: "",
			expected:  "UNKNOWN",
		},
		{
			name:      "city with different subzone format",
			city:      "上海",
			subZone:   "张江",
			subZoneID: "1109",
			expected:  "上海-张江(1109)",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := formatSubZoneDisplay(tt.city, tt.subZone, tt.subZoneID)
			if result != tt.expected {
				t.Errorf("formatSubZoneDisplay(%q, %q, %q) = %q, expected %q",
					tt.city, tt.subZone, tt.subZoneID, result, tt.expected)
			}
		})
	}
}
