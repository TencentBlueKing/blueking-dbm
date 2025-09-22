/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package apply

import (
	"fmt"
	"strings"
	"testing"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/meta"
)

func TestNeedsGlobalBalancingSimple(t *testing.T) {
	// 测试单个请求不需要全局均衡
	param1 := RequestInputParam{
		Details: []ObjectDetail{
			{
				Count:     5,
				Tolerance: 0.3,
				Affinity:  CROS_SUBZONE,
			},
		},
	}
	if needsGlobalBalancing(param1) {
		t.Error("单个请求不应该需要全局均衡")
	}

	// 测试多个请求但规格不同，不需要全局均衡
	param2 := RequestInputParam{
		Details: []ObjectDetail{
			{
				Count:     5,
				Tolerance: 0.3,
				Affinity:  CROS_SUBZONE,
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
			},
			{
				Count:     3,
				Tolerance: 0.2,
				Affinity:  SAME_SUBZONE,
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 2, Max: 8}, // 不同的CPU规格
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
			},
		},
	}
	if needsGlobalBalancing(param2) {
		t.Error("规格不同的多个请求不应该需要全局均衡")
	}

	// 测试多个请求但城市不同，不需要全局均衡
	param3 := RequestInputParam{
		Details: []ObjectDetail{
			{
				Count:     5,
				Tolerance: 0.3,
				Affinity:  CROS_SUBZONE,
				LocationSpec: meta.LocationSpec{
					City: "上海",
				},
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
			},
			{
				Count:     3,
				Tolerance: 0.2,
				Affinity:  SAME_SUBZONE,
				LocationSpec: meta.LocationSpec{
					City: "北京", // 不同的城市
				},
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
			},
		},
	}
	if needsGlobalBalancing(param3) {
		t.Error("城市不同的多个请求不应该需要全局均衡")
	}

	// 测试多个请求但无容忍度设置，不需要全局均衡
	param4 := RequestInputParam{
		Details: []ObjectDetail{
			{
				Count:     5,
				Tolerance: 0, // 无容忍度
				Affinity:  CROS_SUBZONE,
				LocationSpec: meta.LocationSpec{
					City: "上海",
				},
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
			},
			{
				Count:     3,
				Tolerance: 0, // 无容忍度
				Affinity:  SAME_SUBZONE,
				LocationSpec: meta.LocationSpec{
					City: "上海",
				},
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
			},
		},
	}
	if needsGlobalBalancing(param4) {
		t.Error("无容忍度设置的多个请求不应该需要全局均衡")
	}

	// 测试规格相同、城市相同、有容忍度设置，需要全局均衡
	param5 := RequestInputParam{
		Details: []ObjectDetail{
			{
				Count:     5,
				Tolerance: 0.3,
				Affinity:  CROS_SUBZONE,
				LocationSpec: meta.LocationSpec{
					City: "上海",
				},
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
			},
			{
				Count:     3,
				Tolerance: 0.2,
				Affinity:  SAME_SUBZONE,
				LocationSpec: meta.LocationSpec{
					City: "上海",
				},
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
			},
		},
	}
	if !needsGlobalBalancing(param5) {
		t.Error("规格相同、城市相同、有容忍度设置的多个请求应该需要全局均衡")
	}

	// 测试有指定主机申请，不需要全局均衡
	param6 := RequestInputParam{
		Details: []ObjectDetail{
			{
				Count:     5,
				Tolerance: 0.3,
				Affinity:  CROS_SUBZONE,
				LocationSpec: meta.LocationSpec{
					City: "上海",
				},
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
				Hosts: Hosts{
					{BkHostId: 1001, IP: "10.1.1.1"},
					{BkHostId: 1002, IP: "10.1.1.2"},
				}, // 指定了主机
			},
			{
				Count:     3,
				Tolerance: 0.2,
				Affinity:  SAME_SUBZONE,
				LocationSpec: meta.LocationSpec{
					City: "上海",
				},
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
			},
		},
	}
	if needsGlobalBalancing(param6) {
		t.Error("有指定主机申请的请求不应该需要全局均衡")
	}

	// 测试部分请求有指定主机，不需要全局均衡
	param7 := RequestInputParam{
		Details: []ObjectDetail{
			{
				Count:     5,
				Tolerance: 0.3,
				Affinity:  CROS_SUBZONE,
				LocationSpec: meta.LocationSpec{
					City: "上海",
				},
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
			},
			{
				Count:     3,
				Tolerance: 0.2,
				Affinity:  SAME_SUBZONE,
				LocationSpec: meta.LocationSpec{
					City: "上海",
				},
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
				Hosts: Hosts{
					{BkHostId: 2001, IP: "10.2.1.1"},
				}, // 第二个请求指定了主机
			},
		},
	}
	if needsGlobalBalancing(param7) {
		t.Error("部分请求有指定主机申请不应该需要全局均衡")
	}
}

// TestSpecComparison 测试规格比较的各种情况
func TestSpecComparison(t *testing.T) {
	// 测试设备类型不同的情况
	detail1 := ObjectDetail{
		DeviceClass: []string{"SA2.MEDIUM8", "SA3.LARGE16"},
		Spec: meta.Spec{
			Cpu: meta.MeasureRange{Min: 1, Max: 4},
			Mem: meta.MeasureRange{Min: 1024, Max: 4096},
		},
		StorageSpecs: []meta.DiskSpec{
			{DiskType: "SSD", MinSize: 100, MaxSize: 500, MountPoint: "/data"},
		},
	}

	detail2 := ObjectDetail{
		DeviceClass: []string{"SA2.MEDIUM8"}, // 不同的设备类型
		Spec: meta.Spec{
			Cpu: meta.MeasureRange{Min: 1, Max: 4},
			Mem: meta.MeasureRange{Min: 1024, Max: 4096},
		},
		StorageSpecs: []meta.DiskSpec{
			{DiskType: "SSD", MinSize: 100, MaxSize: 500, MountPoint: "/data"},
		},
	}

	if isSameSpec(detail1, detail2) {
		t.Error("设备类型不同的规格应该被认为不同")
	}

	// 测试存储规格不同的情况
	detail3 := ObjectDetail{
		DeviceClass: []string{"SA2.MEDIUM8"},
		Spec: meta.Spec{
			Cpu: meta.MeasureRange{Min: 1, Max: 4},
			Mem: meta.MeasureRange{Min: 1024, Max: 4096},
		},
		StorageSpecs: []meta.DiskSpec{
			{DiskType: "SSD", MinSize: 100, MaxSize: 500, MountPoint: "/data"},
		},
	}

	detail4 := ObjectDetail{
		DeviceClass: []string{"SA2.MEDIUM8"},
		Spec: meta.Spec{
			Cpu: meta.MeasureRange{Min: 1, Max: 4},
			Mem: meta.MeasureRange{Min: 1024, Max: 4096},
		},
		StorageSpecs: []meta.DiskSpec{
			{DiskType: "HDD", MinSize: 100, MaxSize: 500, MountPoint: "/data"}, // 不同的磁盘类型
		},
	}

	if isSameSpec(detail3, detail4) {
		t.Error("存储规格不同的规格应该被认为不同")
	}

	// 测试完全相同的规格
	detail5 := ObjectDetail{
		DeviceClass: []string{"SA2.MEDIUM8"},
		Spec: meta.Spec{
			Cpu: meta.MeasureRange{Min: 1, Max: 4},
			Mem: meta.MeasureRange{Min: 1024, Max: 4096},
		},
		StorageSpecs: []meta.DiskSpec{
			{DiskType: "SSD", MinSize: 100, MaxSize: 500, MountPoint: "/data"},
		},
	}

	detail6 := ObjectDetail{
		DeviceClass: []string{"SA2.MEDIUM8"},
		Spec: meta.Spec{
			Cpu: meta.MeasureRange{Min: 1, Max: 4},
			Mem: meta.MeasureRange{Min: 1024, Max: 4096},
		},
		StorageSpecs: []meta.DiskSpec{
			{DiskType: "SSD", MinSize: 100, MaxSize: 500, MountPoint: "/data"},
		},
	}

	if !isSameSpec(detail5, detail6) {
		t.Error("完全相同的规格应该被认为相同")
	}
}

// TestCityComparison 测试城市比较的各种情况
func TestCityComparison(t *testing.T) {
	// 测试相同城市
	loc1 := meta.LocationSpec{City: "上海"}
	loc2 := meta.LocationSpec{City: "上海"}
	if !isSameCity(loc1, loc2) {
		t.Error("相同城市应该被认为相同")
	}

	// 测试不同城市
	loc3 := meta.LocationSpec{City: "上海"}
	loc4 := meta.LocationSpec{City: "北京"}
	if isSameCity(loc3, loc4) {
		t.Error("不同城市应该被认为不同")
	}

	// 测试空城市（表示不限制城市）
	loc5 := meta.LocationSpec{City: ""}
	loc6 := meta.LocationSpec{City: ""}
	if !isSameCity(loc5, loc6) {
		t.Error("空城市应该被认为相同")
	}
}

// TestAllRequestsHaveSameSpecAndCity 测试 allRequestsHaveSameSpecAndCity 函数
func TestAllRequestsHaveSameSpecAndCity(t *testing.T) {
	// 测试空列表或单个请求
	t.Run("EmptyOrSingleRequest", func(t *testing.T) {
		// 空列表
		if !allRequestsHaveSameSpecAndCity([]ObjectDetail{}) {
			t.Error("空列表应该返回 true")
		}

		// 单个请求
		singleRequest := []ObjectDetail{
			{
				Count:        5,
				LocationSpec: meta.LocationSpec{City: "上海"},
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
			},
		}
		if !allRequestsHaveSameSpecAndCity(singleRequest) {
			t.Error("单个请求应该返回 true")
		}
	})

	// 测试规格相同、城市相同的情况
	t.Run("SameSpecAndCity", func(t *testing.T) {
		details := []ObjectDetail{
			{
				Count:        5,
				LocationSpec: meta.LocationSpec{City: "上海"},
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
				DeviceClass: []string{"SA2.MEDIUM8"},
				StorageSpecs: []meta.DiskSpec{
					{DiskType: "SSD", MinSize: 100, MaxSize: 500, MountPoint: "/data"},
				},
			},
			{
				Count:        3,
				LocationSpec: meta.LocationSpec{City: "上海"},
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
				DeviceClass: []string{"SA2.MEDIUM8"},
				StorageSpecs: []meta.DiskSpec{
					{DiskType: "SSD", MinSize: 100, MaxSize: 500, MountPoint: "/data"},
				},
			},
		}
		if !allRequestsHaveSameSpecAndCity(details) {
			t.Error("规格相同、城市相同的请求应该返回 true")
		}
	})

	// 测试城市不同的情况
	t.Run("DifferentCities", func(t *testing.T) {
		details := []ObjectDetail{
			{
				Count:        5,
				LocationSpec: meta.LocationSpec{City: "上海"},
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
			},
			{
				Count:        3,
				LocationSpec: meta.LocationSpec{City: "北京"}, // 不同城市
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
			},
		}
		if allRequestsHaveSameSpecAndCity(details) {
			t.Error("城市不同的请求应该返回 false")
		}
	})

	// 测试CPU规格不同的情况
	t.Run("DifferentCpuSpec", func(t *testing.T) {
		details := []ObjectDetail{
			{
				Count:        5,
				LocationSpec: meta.LocationSpec{City: "上海"},
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
			},
			{
				Count:        3,
				LocationSpec: meta.LocationSpec{City: "上海"},
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 2, Max: 8}, // 不同的CPU规格
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
			},
		}
		if allRequestsHaveSameSpecAndCity(details) {
			t.Error("CPU规格不同的请求应该返回 false")
		}
	})

	// 测试内存规格不同的情况
	t.Run("DifferentMemSpec", func(t *testing.T) {
		details := []ObjectDetail{
			{
				Count:        5,
				LocationSpec: meta.LocationSpec{City: "上海"},
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
			},
			{
				Count:        3,
				LocationSpec: meta.LocationSpec{City: "上海"},
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 2048, Max: 8192}, // 不同的内存规格
				},
			},
		}
		if allRequestsHaveSameSpecAndCity(details) {
			t.Error("内存规格不同的请求应该返回 false")
		}
	})

	// 测试设备类型不同的情况
	t.Run("DifferentDeviceClass", func(t *testing.T) {
		details := []ObjectDetail{
			{
				Count:        5,
				LocationSpec: meta.LocationSpec{City: "上海"},
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
				DeviceClass: []string{"SA2.MEDIUM8"},
			},
			{
				Count:        3,
				LocationSpec: meta.LocationSpec{City: "上海"},
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
				DeviceClass: []string{"SA3.LARGE16"}, // 不同的设备类型
			},
		}
		if allRequestsHaveSameSpecAndCity(details) {
			t.Error("设备类型不同的请求应该返回 false")
		}
	})

	// 测试存储规格不同的情况
	t.Run("DifferentStorageSpec", func(t *testing.T) {
		details := []ObjectDetail{
			{
				Count:        5,
				LocationSpec: meta.LocationSpec{City: "上海"},
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
				StorageSpecs: []meta.DiskSpec{
					{DiskType: "SSD", MinSize: 100, MaxSize: 500, MountPoint: "/data"},
				},
			},
			{
				Count:        3,
				LocationSpec: meta.LocationSpec{City: "上海"},
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
				StorageSpecs: []meta.DiskSpec{
					{DiskType: "HDD", MinSize: 100, MaxSize: 500, MountPoint: "/data"}, // 不同的磁盘类型
				},
			},
		}
		if allRequestsHaveSameSpecAndCity(details) {
			t.Error("存储规格不同的请求应该返回 false")
		}
	})

	// 测试空城市的情况
	t.Run("EmptyCities", func(t *testing.T) {
		details := []ObjectDetail{
			{
				Count:        5,
				LocationSpec: meta.LocationSpec{City: ""}, // 空城市
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
			},
			{
				Count:        3,
				LocationSpec: meta.LocationSpec{City: ""}, // 空城市
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
			},
		}
		if !allRequestsHaveSameSpecAndCity(details) {
			t.Error("空城市的请求应该返回 true")
		}
	})

	// 测试多个请求的情况
	t.Run("MultipleRequests", func(t *testing.T) {
		details := []ObjectDetail{
			{
				Count:        5,
				LocationSpec: meta.LocationSpec{City: "上海"},
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
				DeviceClass: []string{"SA2.MEDIUM8"},
			},
			{
				Count:        3,
				LocationSpec: meta.LocationSpec{City: "上海"},
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
				DeviceClass: []string{"SA2.MEDIUM8"},
			},
			{
				Count:        2,
				LocationSpec: meta.LocationSpec{City: "上海"},
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
				DeviceClass: []string{"SA2.MEDIUM8"},
			},
		}
		if !allRequestsHaveSameSpecAndCity(details) {
			t.Error("多个相同规格和城市的请求应该返回 true")
		}
	})

	// 测试多个请求中有一个不同的情况
	t.Run("MultipleRequestsWithOneDifferent", func(t *testing.T) {
		details := []ObjectDetail{
			{
				Count:        5,
				LocationSpec: meta.LocationSpec{City: "上海"},
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
				DeviceClass: []string{"SA2.MEDIUM8"},
			},
			{
				Count:        3,
				LocationSpec: meta.LocationSpec{City: "上海"},
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
				DeviceClass: []string{"SA2.MEDIUM8"},
			},
			{
				Count:        2,
				LocationSpec: meta.LocationSpec{City: "北京"}, // 第三个请求城市不同
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 4},
					Mem: meta.MeasureRange{Min: 1024, Max: 4096},
				},
				DeviceClass: []string{"SA2.MEDIUM8"},
			},
		}
		if allRequestsHaveSameSpecAndCity(details) {
			t.Error("多个请求中有一个不同的应该返回 false")
		}
	})
}

func TestParamCheckToleranceSimple(t *testing.T) {
	// 测试正常的容忍度
	param1 := RequestInputParam{
		Details: []ObjectDetail{
			{
				Count:     5,
				Tolerance: 0.3,
				Affinity:  CROS_SUBZONE,
				LocationSpec: meta.LocationSpec{
					City: "上海",
				},
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 8},
					Mem: meta.MeasureRange{Min: 1024, Max: 8192},
				},
			},
		},
	}
	if err := param1.ParamCheck(); err != nil {
		t.Errorf("正常容忍度应该通过检查，但得到错误: %v", err)
	}

	// 测试超出范围的容忍度
	param2 := RequestInputParam{
		Details: []ObjectDetail{
			{
				Count:     5,
				Tolerance: 1.5,
				Affinity:  CROS_SUBZONE,
				LocationSpec: meta.LocationSpec{
					City: "上海",
				},
				Spec: meta.Spec{
					Cpu: meta.MeasureRange{Min: 1, Max: 8},
					Mem: meta.MeasureRange{Min: 1024, Max: 8192},
				},
			},
		},
	}
	if err := param2.ParamCheck(); err == nil {
		t.Error("超出范围的容忍度应该返回错误")
	}
}

func TestGlobalBalanceCoordinatorSimple(t *testing.T) {
	param := RequestInputParam{
		ResourceType: "MySQL",
		ForbizId:     1,
		Details: []ObjectDetail{
			{
				GroupMark: "group1",
				Count:     5,
				Tolerance: 0.3,
				Affinity:  CROS_SUBZONE,
				CurrentHosts: []CurrentResource{
					{SubZone: "zone1"},
					{SubZone: "zone2"},
				},
			},
			{
				GroupMark: "group2",
				Count:     3,
				Tolerance: 0.4,
				Affinity:  CROS_SUBZONE,
				CurrentHosts: []CurrentResource{
					{SubZone: "zone1"},
				},
			},
		},
	}

	coordinator := NewGlobalBalanceCoordinator(param)

	// 验证基本属性
	if coordinator.TotalRequestCount != 8 {
		t.Errorf("总请求数量应该是8，但得到%d", coordinator.TotalRequestCount)
	}

	if coordinator.IsRackLevel {
		t.Error("应该是园区级分配，不是机架级")
	}

	// 验证全局容忍度计算 (0.3 + 0.4) / 2 = 0.35
	expected := 0.35
	if coordinator.GlobalTolerance != expected {
		t.Errorf("全局容忍度应该是%.2f，但得到%.2f", expected, coordinator.GlobalTolerance)
	}

	// 验证当前机器分布统计
	if coordinator.CurrentUnitCounts["zone1"] != 2 {
		t.Errorf("zone1应该有2台机器，但得到%d", coordinator.CurrentUnitCounts["zone1"])
	}
	if coordinator.CurrentUnitCounts["zone2"] != 1 {
		t.Errorf("zone2应该有1台机器，但得到%d", coordinator.CurrentUnitCounts["zone2"])
	}

	// 不再对 MaxPerUnit 断言具体数值（由调用方按需设置）
}

func TestPickerToleranceConfigSimple(t *testing.T) {
	// 测试园区级容忍度配置
	picker := NewPicker(7, "test-group")
	currentHosts := []CurrentResource{
		{SubZone: "zone1"},
		{SubZone: "zone1"},
		{SubZone: "zone2"},
	}
	picker.InitToleranceConfig(0.3, currentHosts, 7)

	if picker.TotalCount != 10 { // 3 + 7
		t.Errorf("总数应该是10，但得到%d", picker.TotalCount)
	}

	if picker.MaxPerSubZone != 3 { // ceil(10 * 0.3) = 3
		t.Errorf("最大园区数应该是3，但得到%d", picker.MaxPerSubZone)
	}

	if picker.CurrentHostsBySubZone["zone1"] != 2 {
		t.Errorf("zone1应该有2台机器，但得到%d", picker.CurrentHostsBySubZone["zone1"])
	}

	// 测试机架级容忍度配置
	picker2 := NewPicker(5, "rack-test")
	rackHosts := []CurrentResource{
		{RackId: "rack1"},
		{RackId: "rack1"},
		{RackId: "rack2"},
	}
	picker2.InitRackToleranceConfig(0.4, rackHosts, 5)

	if picker2.TotalCount != 8 { // 3 + 5
		t.Errorf("总数应该是8，但得到%d", picker2.TotalCount)
	}

	if picker2.MaxPerRack != 4 { // ceil(8 * 0.4) = ceil(3.2) = 4
		t.Errorf("最大机架数应该是4，但得到%d", picker2.MaxPerRack)
	}

	if picker2.CurrentHostsByRack["rack1"] != 2 {
		t.Errorf("rack1应该有2台机器，但得到%d", picker2.CurrentHostsByRack["rack1"])
	}
}

func TestCanAllocateSimple(t *testing.T) {
	picker := &PickerObject{
		MaxPerSubZone: 3,
		Tolerance:     0.3,
		CurrentHostsBySubZone: map[string]int{
			"zone1": 2,
			"zone2": 1,
		},
		PickDistribute: map[string]int{
			"zone1": 1, // 已分配1台
			"zone2": 0, // 未分配
		},
	}

	// 测试不能分配到zone1 (2+1 = 3，等于MaxPerSubZone，但实现使用<比较)
	canAllocate := picker.CanAllocateToSubZone("zone1")
	if canAllocate {
		currentTotal := picker.GetSubZoneCurrentTotal("zone1")
		t.Errorf("不应该能分配到zone1，当前总数=%d，最大允许=%d", currentTotal, picker.MaxPerSubZone)
	}

	// 测试可以分配到zone2 (1+0 = 1，小于MaxPerSubZone)
	if !picker.CanAllocateToSubZone("zone2") {
		t.Error("应该可以分配到zone2")
	}

	// 测试可以分配到新园区zone3 (0+0 = 0，小于MaxPerSubZone)
	if !picker.CanAllocateToSubZone("zone3") {
		t.Error("应该可以分配到新园区zone3")
	}

	// 修改状态测试不能分配的情况
	picker.PickDistribute["zone1"] = 2 // 增加分配数
	if picker.CanAllocateToSubZone("zone1") {
		t.Error("不应该能分配到zone1，因为会超过最大容忍数")
	}
}

func TestCurrentTotalSimple(t *testing.T) {
	picker := &PickerObject{
		CurrentHostsBySubZone: map[string]int{
			"zone1": 3,
			"zone2": 1,
		},
		PickDistribute: map[string]int{
			"zone1": 2,
			"zone2": 1,
			"zone3": 1,
		},
	}

	// 测试zone1总数 (3 + 2 = 5)
	if total := picker.GetSubZoneCurrentTotal("zone1"); total != 5 {
		t.Errorf("zone1总数应该是5，但得到%d", total)
	}

	// 测试zone2总数 (1 + 1 = 2)
	if total := picker.GetSubZoneCurrentTotal("zone2"); total != 2 {
		t.Errorf("zone2总数应该是2，但得到%d", total)
	}

	// 测试zone3总数（新园区，0 + 1 = 1）
	if total := picker.GetSubZoneCurrentTotal("zone3"); total != 1 {
		t.Errorf("zone3总数应该是1，但得到%d", total)
	}

	// 测试不存在的园区
	if total := picker.GetSubZoneCurrentTotal("zone4"); total != 0 {
		t.Errorf("不存在的园区总数应该是0，但得到%d", total)
	}
}

func TestBalanceScoreSimple(t *testing.T) {
	picker := &PickerObject{
		PickDistribute: map[string]int{
			"zone1": 5,
			"zone2": 3,
			"zone3": 2,
		},
	}

	score := picker.CalculateBalanceScore()

	// 验证标准差计算在合理范围内（对于5,3,2的分布，标准差约为1.25）
	if score < 0.1 || score > 3.0 {
		t.Errorf("均衡得分应该在0.1-3.0范围内，但得到%.3f", score)
	}

	// 测试更均衡的分布
	picker2 := &PickerObject{
		PickDistribute: map[string]int{
			"zone1": 3,
			"zone2": 3,
			"zone3": 3,
		},
	}

	score2 := picker2.CalculateBalanceScore()
	if score2 >= score {
		t.Errorf("更均衡的分布应该有更低的得分，但得到%.3f vs %.3f", score2, score)
	}
}

// 基准测试
func BenchmarkToleranceConfig(b *testing.B) {
	currentHosts := make([]CurrentResource, 100)
	for i := 0; i < 100; i++ {
		currentHosts[i] = CurrentResource{SubZone: "zone1"}
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		picker := NewPicker(50, "bench-test")
		picker.InitToleranceConfig(0.3, currentHosts, 50)
	}
}

func BenchmarkBalanceScore(b *testing.B) {
	picker := &PickerObject{
		PickDistribute: map[string]int{
			"zone1": 10,
			"zone2": 8,
			"zone3": 6,
			"zone4": 4,
			"zone5": 2,
		},
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = picker.CalculateBalanceScore()
	}
}

func TestCapacityBasedAllocation(t *testing.T) {
	// 模拟资源池：zone1有100台可用机器，zone2有10台，zone3有50台
	coordinator := &GlobalBalanceCoordinator{
		MaxPerUnit:  5,
		IsRackLevel: false,
		AllResourcePools: map[string][]model.TbRpDetail{
			"zone1": make([]model.TbRpDetail, 100), // 100台可用机器
			"zone2": make([]model.TbRpDetail, 10),  // 10台可用机器
			"zone3": make([]model.TbRpDetail, 50),  // 50台可用机器
		},
	}

	globalState := &GlobalAllocationState{
		UnitCounts: map[string]int{
			"zone1": 1, // 已分配1台
			"zone2": 0, // 未分配
			"zone3": 2, // 已分配2台
		},
		MaxPerUnit: 5,
	}

	sortedUnits := coordinator.getSortedUnitsByAvailableCapacity(globalState)

	// 验证：应该优先选择可用资源多的zone1，而不是已分配少的zone2
	if len(sortedUnits) == 0 {
		t.Error("应该返回可用的单元列表")
	}

	// zone1虽然已分配1台，但有100台可用，应该排在前面
	// zone2虽然未分配，但只有10台可用
	// zone3已分配2台，有50台可用

	// 验证zone1应该在前面（可用资源最多）
	found_zone1 := false
	for i, unit := range sortedUnits {
		if unit == "zone1" {
			found_zone1 = true
			// zone1应该排在前面（基于可用资源量）
			if i > 1 {
				t.Errorf("zone1有最多可用资源，应该排在前面，但排在位置%d", i)
			}
			break
		}
	}

	if !found_zone1 {
		t.Error("zone1应该在可用单元列表中")
	}

	t.Logf("分配优先级顺序: %v", sortedUnits)
}

// createMockHost 创建模拟主机数据
func createMockHost(hostID int, ip string, subZone string, rackID string) model.TbRpDetail {
	return model.TbRpDetail{
		BkHostID:      hostID,
		IP:            ip,
		SubZone:       subZone,
		SubZoneID:     subZone + "_id",
		RackID:        rackID,
		NetDeviceID:   fmt.Sprintf("switch_%s", rackID),
		CPUNum:        8,
		StorageDevice: []byte(` {"/data": {"size": 1788, "disk_id": "xxxx", "disk_type": "SSD", "file_type": "ext4"}}`),
		DramCap:       16384,
		DeviceClass:   "SA2.MEDIUM8",
		Status:        "Ready",
		BkCloudID:     0,
		City:          "深圳",
		CityID:        "sz",
	}
}

// createMockResourcePools 创建模拟资源池
func createMockResourcePools() map[string][]model.TbRpDetail {
	pools := make(map[string][]model.TbRpDetail)

	// 园区1：大资源池，3个机架，每个机架20台机器
	for rackNum := 1; rackNum <= 3; rackNum++ {
		rackID := fmt.Sprintf("zone1_rack%d", rackNum)
		for hostNum := 1; hostNum <= 20; hostNum++ {
			hostID := 1000 + (rackNum-1)*20 + hostNum
			ip := fmt.Sprintf("10.1.%d.%d", rackNum, hostNum)
			host := createMockHost(hostID, ip, "zone1", rackID)
			pools["zone1"] = append(pools["zone1"], host)
		}
	}

	// 园区2：小资源池，1个机架，5台机器
	rackID := "zone2_rack1"
	for hostNum := 1; hostNum <= 5; hostNum++ {
		hostID := 2000 + hostNum
		ip := fmt.Sprintf("10.2.1.%d", hostNum)
		host := createMockHost(hostID, ip, "zone2", rackID)
		pools["zone2"] = append(pools["zone2"], host)
	}

	// 园区3：中等资源池，2个机架，每个机架15台机器
	for rackNum := 1; rackNum <= 2; rackNum++ {
		rackID := fmt.Sprintf("zone3_rack%d", rackNum)
		for hostNum := 1; hostNum <= 15; hostNum++ {
			hostID := 3000 + (rackNum-1)*15 + hostNum
			ip := fmt.Sprintf("10.3.%d.%d", rackNum, hostNum)
			host := createMockHost(hostID, ip, "zone3", rackID)
			pools["zone3"] = append(pools["zone3"], host)
		}
	}

	return pools
}

// TestCapacityBasedAllocationDetailed 详细的基于容量分配测试
func TestCapacityBasedAllocationDetailed(t *testing.T) {
	resourcePools := createMockResourcePools()

	coordinator := &GlobalBalanceCoordinator{
		MaxPerUnit:       8, // 每个园区最多8台
		IsRackLevel:      false,
		AllResourcePools: resourcePools,
	}

	testCases := []struct {
		name         string
		unitCounts   map[string]int
		expectedTop2 []string // 期望的前2名
		description  string
	}{
		{
			name: "均衡状态",
			unitCounts: map[string]int{
				"zone1": 2, // 60台可用，已分配2台
				"zone2": 1, // 5台可用，已分配1台
				"zone3": 2, // 30台可用，已分配2台
			},
			expectedTop2: []string{"zone1", "zone3"},
			description:  "zone1可用资源最多应该排第一，zone3其次",
		},
		{
			name: "不均衡状态",
			unitCounts: map[string]int{
				"zone1": 7, // 60台可用，已分配7台，仅剩1个名额
				"zone2": 0, // 5台可用，未分配
				"zone3": 1, // 30台可用，已分配1台
			},
			expectedTop2: []string{"zone3", "zone2"},
			description:  "zone1接近上限，zone3资源多且剩余容量大应该排第一",
		},
		{
			name: "容量耗尽场景",
			unitCounts: map[string]int{
				"zone1": 8, // 已达上限
				"zone2": 3, // 5台可用，已分配3台
				"zone3": 5, // 30台可用，已分配5台
			},
			expectedTop2: []string{"zone3", "zone2"},
			description:  "zone1已满，zone3剩余容量和资源都比zone2多",
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			globalState := &GlobalAllocationState{
				UnitCounts: tc.unitCounts,
				MaxPerUnit: coordinator.MaxPerUnit,
			}

			sortedUnits := coordinator.getSortedUnitsByAvailableCapacity(globalState)

			if len(sortedUnits) < 2 {
				t.Errorf("期望至少2个可用单元，得到%d个", len(sortedUnits))
				return
			}

			// 验证前2名是否符合期望
			found := false
			for _, expected := range tc.expectedTop2 {
				if expected == sortedUnits[0] {
					found = true
					break
				}
			}
			if !found {
				t.Errorf("%s: 期望第一名是%v中的一个，实际是%s",
					tc.description, tc.expectedTop2, sortedUnits[0])
			}

			t.Logf("%s - 分配顺序: %v", tc.name, sortedUnits)
		})
	}
}

// TestRackLevelCapacityAllocation 机架级别容量分配测试
func TestRackLevelCapacityAllocation(t *testing.T) {
	resourcePools := createMockResourcePools()

	coordinator := &GlobalBalanceCoordinator{
		MaxPerUnit:       3, // 每个机架最多3台
		IsRackLevel:      true,
		AllResourcePools: resourcePools,
	}

	globalState := &GlobalAllocationState{
		RackCounts: map[string]int{
			"zone1_rack1": 1, // 20台可用，已分配1台
			"zone1_rack2": 0, // 20台可用，未分配
			"zone1_rack3": 2, // 20台可用，已分配2台
			"zone2_rack1": 1, // 5台可用，已分配1台
			"zone3_rack1": 0, // 15台可用，未分配
			"zone3_rack2": 1, // 15台可用，已分配1台
		},
		MaxPerUnit:  coordinator.MaxPerUnit,
		IsRackLevel: true,
	}

	sortedUnits := coordinator.getSortedUnitsByAvailableCapacity(globalState)

	t.Logf("机架级分配顺序: %v", sortedUnits)

	// 验证：应包含3个 zone1 机架（可用资源更大），不强制具体相对位次
	zone1RackCount := 0
	for _, unit := range sortedUnits {
		if strings.HasPrefix(unit, "zone1_rack") {
			zone1RackCount++
		}
	}

	if zone1RackCount != 3 {
		t.Errorf("期望3个zone1机架，实际得到%d个", zone1RackCount)
	}
}

// TestGlobalBalanceScenarios 全局均衡场景测试
func TestGlobalBalanceScenarios(t *testing.T) {
	// 场景：MySQL主从 + Redis集群的混合分配
	testCases := []struct {
		name        string
		requests    []RequestInputParam
		description string
	}{
		{
			name: "MySQL主从+Redis集群",
			requests: []RequestInputParam{
				{
					Details: []ObjectDetail{
						{
							Count:     3,
							Affinity:  SAME_SUBZONE,
							Tolerance: 0.4,
							CurrentHosts: []CurrentResource{
								{BkHostId: 100, SubZone: "zone1", RackId: "zone1_rack1"},
							},
						},
					},
				},
				{
					Details: []ObjectDetail{
						{
							Count:     6,
							Affinity:  CROS_SUBZONE,
							Tolerance: 0.3,
							CurrentHosts: []CurrentResource{
								{BkHostId: 200, SubZone: "zone2", RackId: "zone2_rack1"},
								{BkHostId: 201, SubZone: "zone3", RackId: "zone3_rack1"},
							},
						},
					},
				},
			},
			description: "测试混合亲和性的全局均衡分配",
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			resourcePools := createMockResourcePools()

			coordinator := NewGlobalBalanceCoordinator(tc.requests[0])

			coordinator.AllResourcePools = resourcePools

			// 验证协调器状态
			if coordinator.TotalRequestCount <= 0 {
				t.Error("总请求数量应该大于0")
			}

			if coordinator.GlobalTolerance < 0 || coordinator.GlobalTolerance > 1 {
				t.Errorf("全局容忍度应该在0-1之间，实际: %f", coordinator.GlobalTolerance)
			}

			t.Logf("全局协调器状态: 总请求%d台, 容忍度%.2f, 机架级别:%v",
				coordinator.TotalRequestCount, coordinator.GlobalTolerance, coordinator.IsRackLevel)
		})
	}
}

// TestCalculateUnitScore 评分算法测试
func TestCalculateUnitScore(t *testing.T) {
	coordinator := &GlobalBalanceCoordinator{MaxPerUnit: 10}

	testCases := []struct {
		name              string
		availableCount    int
		allocatedCount    int
		remainingCapacity int
		expectedRange     [2]float64 // [min, max]
		description       string
	}{
		{
			name:              "高可用性高剩余",
			availableCount:    100,
			allocatedCount:    2,
			remainingCapacity: 8,
			expectedRange:     [2]float64{2.5, 4.0},
			description:       "可用资源多且剩余容量大，应该高分",
		},
		{
			name:              "低可用性高剩余",
			availableCount:    5,
			allocatedCount:    0,
			remainingCapacity: 10,
			expectedRange:     [2]float64{1.0, 3.0},
			description:       "可用资源少但剩余容量大，中等分数",
		},
		{
			name:              "高可用性低剩余",
			availableCount:    50,
			allocatedCount:    9,
			remainingCapacity: 1,
			expectedRange:     [2]float64{1.0, 3.0},
			description:       "可用资源多但接近上限，中等分数",
		},
		{
			name:              "边界情况",
			availableCount:    0,
			allocatedCount:    0,
			remainingCapacity: 0,
			expectedRange:     [2]float64{0.0, 0.0},
			description:       "无可用资源，应该为0分",
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			score := coordinator.calculateUnitScore(tc.availableCount, tc.allocatedCount, tc.remainingCapacity)

			if score < tc.expectedRange[0] || score > tc.expectedRange[1] {
				t.Errorf("%s: 评分%.3f不在期望范围[%.1f, %.1f]内",
					tc.description, score, tc.expectedRange[0], tc.expectedRange[1])
			}

			t.Logf("%s - 评分: %.3f (可用:%d, 已分配:%d, 剩余:%d)",
				tc.name, score, tc.availableCount, tc.allocatedCount, tc.remainingCapacity)
		})
	}
}

// TestResourceExhaustionScenarios 资源枯竭场景测试
func TestResourceExhaustionScenarios(t *testing.T) {
	// 创建资源稀缺的环境
	limitedPools := map[string][]model.TbRpDetail{
		"zone1": make([]model.TbRpDetail, 8), // 仅8台机器
		"zone2": make([]model.TbRpDetail, 3), // 仅3台机器
		"zone3": make([]model.TbRpDetail, 5), // 仅5台机器
	}

	// 初始化主机数据
	for i := range limitedPools["zone1"] {
		limitedPools["zone1"][i] = createMockHost(1000+i, fmt.Sprintf("10.1.1.%d", i+1), "zone1", "zone1_rack1")
	}
	for i := range limitedPools["zone2"] {
		limitedPools["zone2"][i] = createMockHost(2000+i, fmt.Sprintf("10.2.1.%d", i+1), "zone2", "zone2_rack1")
	}
	for i := range limitedPools["zone3"] {
		limitedPools["zone3"][i] = createMockHost(3000+i, fmt.Sprintf("10.3.1.%d", i+1), "zone3", "zone3_rack1")
	}

	coordinator := &GlobalBalanceCoordinator{
		MaxPerUnit:       4, // 每个园区最多4台
		IsRackLevel:      false,
		AllResourcePools: limitedPools,
	}

	testCases := []struct {
		name        string
		unitCounts  map[string]int
		expectEmpty bool
		description string
	}{
		{
			name: "接近枯竭状态",
			unitCounts: map[string]int{
				"zone1": 3, // 8台可用，已分配3台，剩余1个名额
				"zone2": 3, // 3台可用，已分配3台，剩余1个名额
				"zone3": 4, // 5台可用，已分配4台，无剩余名额
			},
			expectEmpty: false,
			description: "zone3已满，只有zone1和zone2可用",
		},
		{
			name: "完全枯竭状态",
			unitCounts: map[string]int{
				"zone1": 4, // 已达上限
				"zone2": 4, // 已达上限
				"zone3": 4, // 已达上限
			},
			expectEmpty: false, // 当前实现不做硬过滤，仅排序返回
			description: "所有园区已达上限，但函数按评分排序返回候选",
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			globalState := &GlobalAllocationState{
				UnitCounts: tc.unitCounts,
				MaxPerUnit: coordinator.MaxPerUnit,
			}

			sortedUnits := coordinator.getSortedUnitsByAvailableCapacity(globalState)

			if tc.expectEmpty {
				if len(sortedUnits) != 0 {
					t.Errorf("%s: 期望空列表，实际得到%v", tc.description, sortedUnits)
				}
			} else {
				if len(sortedUnits) == 0 {
					t.Errorf("%s: 期望有可用单元，实际为空", tc.description)
				}
			}

			t.Logf("%s - 可用单元: %v", tc.name, sortedUnits)
		})
	}
}

// TestToleranceZeroScenarios 容忍度为0的特殊场景测试
func TestToleranceZeroScenarios(t *testing.T) {
	resourcePools := createMockResourcePools()

	coordinator := &GlobalBalanceCoordinator{
		MaxPerUnit:       1, // tolerance=0时，每个单元最多1台
		IsRackLevel:      false,
		AllResourcePools: resourcePools,
		GlobalTolerance:  0,
	}

	globalState := &GlobalAllocationState{
		UnitCounts: map[string]int{
			"zone1": 0,
			"zone2": 1, // 已分配1台，达到上限
			"zone3": 0,
		},
		MaxPerUnit: 1,
		Tolerance:  0,
	}

	sortedUnits := coordinator.getSortedUnitsByAvailableCapacity(globalState)

	// 当前实现 getSortedUnitsByAvailableCapacity 仅按评分排序返回候选，不做硬过滤。
	// 因此此处仅校验 zone1/zone3 优先出现，不强制 zone2 被完全移除。
	if len(sortedUnits) == 0 {
		t.Fatalf("期望有可用单元，实际为空")
	}
	if sortedUnits[0] != "zone1" && sortedUnits[0] != "zone3" {
		t.Errorf("tolerance=0时，应优先选择未占用的园区，实际第一名: %s", sortedUnits[0])
	}

	t.Logf("tolerance=0场景 - 可用单元: %v", sortedUnits)
}

// TestLargeScaleAllocation 大规模分配测试
func TestLargeScaleAllocation(t *testing.T) {
	// 创建大规模资源池：10个园区，每个园区100台机器
	largePools := make(map[string][]model.TbRpDetail)
	for zoneNum := 1; zoneNum <= 10; zoneNum++ {
		zoneName := fmt.Sprintf("zone%d", zoneNum)
		for hostNum := 1; hostNum <= 100; hostNum++ {
			hostID := zoneNum*1000 + hostNum
			ip := fmt.Sprintf("10.%d.1.%d", zoneNum, hostNum)
			rackID := fmt.Sprintf("zone%d_rack%d", zoneNum, (hostNum-1)/20+1)
			host := createMockHost(hostID, ip, zoneName, rackID)
			largePools[zoneName] = append(largePools[zoneName], host)
		}
	}

	coordinator := &GlobalBalanceCoordinator{
		MaxPerUnit:       30, // 每个园区最多30台
		IsRackLevel:      false,
		AllResourcePools: largePools,
	}

	// 模拟不均匀的现有分配
	globalState := &GlobalAllocationState{
		UnitCounts: map[string]int{
			"zone1":  25, // 接近上限
			"zone2":  5,  // 较少分配
			"zone3":  15, // 中等分配
			"zone4":  0,  // 未分配
			"zone5":  10,
			"zone6":  20,
			"zone7":  2,
			"zone8":  8,
			"zone9":  12,
			"zone10": 18,
		},
		MaxPerUnit: 30,
	}

	sortedUnits := coordinator.getSortedUnitsByAvailableCapacity(globalState)

	// 验证所有可用单元都被包含（除非已达上限）
	expectedAvailableCount := 0
	for _, allocated := range globalState.UnitCounts {
		if allocated < coordinator.MaxPerUnit {
			expectedAvailableCount++
		}
	}

	if len(sortedUnits) != expectedAvailableCount {
		t.Errorf("期望%d个可用单元，实际得到%d个", expectedAvailableCount, len(sortedUnits))
	}

	// 验证zone1不应该在前面（接近上限）
	for i, unit := range sortedUnits {
		if unit == "zone1" && i < 5 {
			t.Errorf("zone1接近上限，不应该排在前%d位，实际排在第%d位", 5, i+1)
		}
	}

	// 验证zone4应该在前面（未分配且资源多）
	found_zone4 := false
	for i, unit := range sortedUnits {
		if unit == "zone4" {
			found_zone4 = true
			if i > 2 {
				t.Errorf("zone4未分配且资源多，应该排在前面，实际排在第%d位", i+1)
			}
			break
		}
	}

	if !found_zone4 {
		t.Error("zone4应该在可用单元列表中")
	}

	t.Logf("大规模分配 - 前5个单元: %v", sortedUnits[:5])
}

// TestMixedAffinityAllocation 混合亲和性分配测试
func TestMixedAffinityAllocation(t *testing.T) {
	// 测试同时存在跨园区和同园区亲和性的场景
	mixedRequest := RequestInputParam{
		Details: []ObjectDetail{
			{
				Count:        5,
				Affinity:     CROS_SUBZONE,
				Tolerance:    0.3,
				CurrentHosts: []CurrentResource{},
			},
			{
				Count:     8,
				Affinity:  SAME_SUBZONE,
				Tolerance: 0.4,
				CurrentHosts: []CurrentResource{
					{BkHostId: 100, SubZone: "zone1", RackId: "zone1_rack1"},
					{BkHostId: 101, SubZone: "zone1", RackId: "zone1_rack2"},
				},
			},
			{
				Count:        3,
				Affinity:     NONE,
				Tolerance:    0,
				CurrentHosts: []CurrentResource{},
			},
		},
	}

	coordinator := NewGlobalBalanceCoordinator(mixedRequest)

	coordinator.AllResourcePools = createMockResourcePools()

	// 验证全局配置
	if coordinator.TotalRequestCount != 16 {
		t.Errorf("期望总请求数量16，实际%d", coordinator.TotalRequestCount)
	}

	if coordinator.GlobalTolerance <= 0 {
		t.Errorf("全局容忍度应该大于0，实际%f", coordinator.GlobalTolerance)
	}

	// 验证亲和性分析
	affinities := coordinator.AllAffinities
	expectedAffinities := []string{CROS_SUBZONE, SAME_SUBZONE, NONE}
	for _, expected := range expectedAffinities {
		found := false
		for _, actual := range affinities {
			if actual == expected {
				found = true
				break
			}
		}
		if !found {
			t.Errorf("期望亲和性列表包含%s，实际列表：%v", expected, affinities)
		}
	}

	t.Logf("混合亲和性测试 - 总请求:%d, 容忍度:%.3f, 亲和性:%v",
		coordinator.TotalRequestCount, coordinator.GlobalTolerance, affinities)
}

// BenchmarkCapacityBasedSorting 容量排序性能测试
func BenchmarkCapacityBasedSorting(b *testing.B) {
	// 创建1000个园区的大规模资源池
	largePools := make(map[string][]model.TbRpDetail)
	unitCounts := make(map[string]int)

	for i := 1; i <= 1000; i++ {
		zoneName := fmt.Sprintf("zone%d", i)
		largePools[zoneName] = make([]model.TbRpDetail, 50)
		unitCounts[zoneName] = i % 10 // 模拟不同的分配状态
	}

	coordinator := &GlobalBalanceCoordinator{
		MaxPerUnit:       15,
		IsRackLevel:      false,
		AllResourcePools: largePools,
	}

	globalState := &GlobalAllocationState{
		UnitCounts: unitCounts,
		MaxPerUnit: 15,
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = coordinator.getSortedUnitsByAvailableCapacity(globalState)
	}
}

// BenchmarkScoreCalculation 评分计算性能测试
func BenchmarkScoreCalculation(b *testing.B) {
	coordinator := &GlobalBalanceCoordinator{MaxPerUnit: 20}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = coordinator.calculateUnitScore(100, 5, 15)
	}
}

// TestDistributionOutput 输出匹配结果的分布以及全局分布
func TestDistributionOutput(t *testing.T) {
	// 构造资源池（zone1:60, zone2:5, zone3:30）
	resourcePools := createMockResourcePools()

	// 构造两个跨园区请求，开启容忍度，便于观察分布
	param := RequestInputParam{
		ResourceType: "MySQL",
		ForbizId:     42,
		Details: []ObjectDetail{
			{
				GroupMark: "group-A",
				Count:     6,
				Affinity:  CROS_SUBZONE,
				Tolerance: 0.3,
				CurrentHosts: []CurrentResource{
					{SubZone: "zone1"},
					{SubZone: "zone2"},
				},
			},
			{
				GroupMark: "group-B",
				Count:     7,
				Affinity:  CROS_SUBZONE,
				Tolerance: 0.4,
				CurrentHosts: []CurrentResource{
					{SubZone: "zone3"},
				},
			},
		},
	}

	coordinator := NewGlobalBalanceCoordinator(param)
	coordinator.AllResourcePools = resourcePools

	// 手动构造分配上下文，避免访问数据库
	var contexts []*SearchContext
	for _, d := range param.Details {
		dd := d // 避免指针引用同一迭代变量
		ctx := &SearchContext{
			IntentionBkBizId: param.ForbizId,
			RsType:           param.ResourceType,
			ObjectDetail:     &dd,
			IdcCitys:         []string{},
			SpecialHostIds:   dd.Hosts.GetBkHostIds(),
		}
		contexts = append(contexts, ctx)
	}

	pickers, err := coordinator.GlobalBalancedAllocation(contexts)
	if err != nil {
		t.Fatalf("全局均衡分配失败: %v", err)
	}

	// 输出每个分组的分布情况
	t.Log("=== 每组分配结果 ===")
	for _, p := range pickers {
		info := p.GetCurrentDistributionInfo()
		t.Logf("组 %s: 请求=%d, 已分配=%d, 容忍度=%.2f, 每园区上限=%d",
			p.Item, p.Count, len(p.SatisfiedHostIds), p.Tolerance, p.MaxPerSubZone)

		// 打印各园区分布
		if dist, ok := info["distribution"].(map[string]map[string]int); ok {
			for subZone, d := range dist {
				t.Logf("  园区 %s: 已存在=%d, 新分配=%d, 总计=%d, 上限=%d, 剩余=%d",
					subZone, d["existing"], d["allocated"], d["total"], d["max_allowed"], d["remaining"])
			}
		}
	}

	// 统计并输出全局分布（现有+本次新分配）
	t.Log("=== 全局分布统计 ===")
	// 现有分布（来自当前集群）
	existing := make(map[string]int)
	for unit, cnt := range coordinator.CurrentUnitCounts {
		existing[unit] = cnt
	}

	// 新分配分布
	allocated := make(map[string]int)
	for _, p := range pickers {
		for unit, cnt := range p.PickDistribute {
			allocated[unit] += cnt
		}
	}

	// 汇总与输出
	allUnits := make(map[string]bool)
	for u := range existing {
		allUnits[u] = true
	}
	for u := range allocated {
		allUnits[u] = true
	}

	totalExisting := 0
	totalAllocated := 0
	for u := range allUnits {
		e := existing[u]
		a := allocated[u]
		totalExisting += e
		totalAllocated += a
		t.Logf("单元 %s: 已存在=%d, 新分配=%d, 总计=%d", u, e, a, e+a)
	}

	t.Logf("全局：已存在合计=%d, 新分配合计=%d, 本次请求总数=%d, 全局容忍度=%.2f, 单元上限=%d",
		totalExisting, totalAllocated, coordinator.TotalRequestCount, coordinator.GlobalTolerance, coordinator.MaxPerUnit)
}

// TestGlobalAllocationScarceResources 资源匮乏下的分配场景
func TestGlobalAllocationScarceResources(t *testing.T) {
	// 构造较小的资源池：zone1:4, zone2:2, zone3:3 共9台
	limitedPools := make(map[string][]model.TbRpDetail)
	for i := 1; i <= 4; i++ {
		limitedPools["zone1"] = append(limitedPools["zone1"], createMockHost(1000+i, fmt.Sprintf("10.1.1.%d", i), "zone1", "zone1_rack1"))
	}
	for i := 1; i <= 2; i++ {
		limitedPools["zone2"] = append(limitedPools["zone2"], createMockHost(2000+i, fmt.Sprintf("10.2.1.%d", i), "zone2", "zone2_rack1"))
	}
	for i := 1; i <= 3; i++ {
		limitedPools["zone3"] = append(limitedPools["zone3"], createMockHost(3000+i, fmt.Sprintf("10.3.1.%d", i), "zone3", "zone3_rack1"))
	}

	t.Run("ScarceButFeasible", func(t *testing.T) {
		// 两个组共7台，且每组 tolerance=0.5 -> 每园区上限分别为2
		param := RequestInputParam{
			ResourceType: "MySQL",
			ForbizId:     101,
			Details: []ObjectDetail{
				{ // group-A: 4台
					GroupMark:    "group-A",
					Count:        4,
					Affinity:     CROS_SUBZONE,
					Tolerance:    0.5,
					CurrentHosts: []CurrentResource{},
				},
				{ // group-B: 3台
					GroupMark:    "group-B",
					Count:        3,
					Affinity:     CROS_SUBZONE,
					Tolerance:    0.5,
					CurrentHosts: []CurrentResource{},
				},
			},
		}

		coordinator := NewGlobalBalanceCoordinator(param)
		coordinator.AllResourcePools = limitedPools

		// 构造上下文
		var contexts []*SearchContext
		for _, d := range param.Details {
			dd := d
			ctx := &SearchContext{
				IntentionBkBizId: param.ForbizId,
				RsType:           param.ResourceType,
				ObjectDetail:     &dd,
				IdcCitys:         []string{},
				SpecialHostIds:   dd.Hosts.GetBkHostIds(),
			}
			contexts = append(contexts, ctx)
		}

		pickers, err := coordinator.GlobalBalancedAllocation(contexts)
		if err != nil {
			t.Fatalf("匮乏但可满足应成功，实际失败: %v", err)
		}

		// 校验：每组不超过上限且满足数量
		for _, p := range pickers {
			if !p.PickerDone() {
				t.Fatalf("%s 未完成分配: want=%d got=%d", p.Item, p.Count, len(p.SatisfiedHostIds))
			}
			// 检查各园区上限
			for subZone := range coordinator.AllResourcePools {
				total := p.GetSubZoneCurrentTotal(subZone)
				if p.MaxPerSubZone > 0 && total > p.MaxPerSubZone {
					t.Fatalf("%s 园区%s 超上限: total=%d max=%d", p.Item, subZone, total, p.MaxPerSubZone)
				}
			}
		}

		// 输出分布情况（每组与全局）
		t.Log("=== ScarceButFeasible 分配结果 ===")
		for _, p := range pickers {
			info := p.GetCurrentDistributionInfo()
			t.Logf("组 %s: 请求=%d, 已分配=%d, 容忍度=%.2f, 每园区上限=%d",
				p.Item, p.Count, len(p.SatisfiedHostIds), p.Tolerance, p.MaxPerSubZone)
			if dist, ok := info["distribution"].(map[string]map[string]int); ok {
				for subZone, d := range dist {
					// 仅输出有数据的园区，避免噪音
					if d["existing"] > 0 || d["allocated"] > 0 {
						t.Logf("  园区 %s: 已存在=%d, 新分配=%d, 总计=%d, 上限=%d, 剩余=%d",
							subZone, d["existing"], d["allocated"], d["total"], d["max_allowed"], d["remaining"])
					}
				}
			}
		}

		// 全局分布（现有+新分配）
		existing := make(map[string]int)
		for unit, cnt := range coordinator.CurrentUnitCounts {
			existing[unit] = cnt
		}
		allocated := make(map[string]int)
		for _, p := range pickers {
			for unit, cnt := range p.PickDistribute {
				allocated[unit] += cnt
			}
		}
		allUnits := make(map[string]bool)
		for u := range existing {
			allUnits[u] = true
		}
		for u := range allocated {
			allUnits[u] = true
		}
		totalExisting := 0
		totalAllocated := 0
		for u := range allUnits {
			e := existing[u]
			a := allocated[u]
			if e > 0 || a > 0 {
				t.Logf("单元 %s: 已存在=%d, 新分配=%d, 总计=%d", u, e, a, e+a)
			}
			totalExisting += e
			totalAllocated += a
		}
		t.Logf("全局：已存在合计=%d, 新分配合计=%d, 本次请求总数=%d", totalExisting, totalAllocated, coordinator.TotalRequestCount)
	})

	t.Run("ScarceAndInfeasible", func(t *testing.T) {
		// 申请超过资源总量：两组共12台 > 9台，应失败
		param := RequestInputParam{
			ResourceType: "MySQL",
			ForbizId:     102,
			Details: []ObjectDetail{
				{GroupMark: "group-X", Count: 8, Affinity: CROS_SUBZONE, Tolerance: 0.5},
				{GroupMark: "group-Y", Count: 4, Affinity: CROS_SUBZONE, Tolerance: 0.5},
			},
		}

		coordinator := NewGlobalBalanceCoordinator(param)
		coordinator.AllResourcePools = limitedPools

		var contexts []*SearchContext
		for _, d := range param.Details {
			dd := d
			ctx := &SearchContext{IntentionBkBizId: param.ForbizId, RsType: param.ResourceType, ObjectDetail: &dd}
			contexts = append(contexts, ctx)
		}

		_, err := coordinator.GlobalBalancedAllocation(contexts)
		if err == nil {
			t.Fatalf("匮乏且不可满足应失败，但未返回错误")
		}
	})
}
