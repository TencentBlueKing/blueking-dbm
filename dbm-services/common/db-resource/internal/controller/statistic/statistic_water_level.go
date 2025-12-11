package statistic

import (
	"sort"
	"strconv"
	"sync"

	"github.com/gin-gonic/gin"
	"github.com/samber/lo"

	"dbm-services/common/db-resource/internal/config"
	"dbm-services/common/db-resource/internal/controller"
	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/dbmapi"
	"dbm-services/common/db-resource/internal/svr/meta"
	"dbm-services/common/go-pubpkg/logger"
)

var (
	dbmClient *dbmapi.DbmClient
	once      sync.Once
)

// initDbmClient 使用 sync.Once 确保 DBM 客户端只初始化一次
func initDbmClient() {
	once.Do(func() {
		dbmClient = dbmapi.NewDbmClient()
	})
}

// GetDbmClient 获取 DBM 客户端实例，确保只初始化一次
func GetDbmClient() *dbmapi.DbmClient {
	initDbmClient()
	return dbmClient
}

// WaterLevelHandler 水位统计处理器
type WaterLevelHandler struct {
	controller.BaseHandler
}

// RegisterRouter 注册路由
func (h *WaterLevelHandler) RegisterRouter(engine *gin.Engine) {
	engine.POST("/statistic/water_level/old", h.WaterLevelStatistic)
}

// getSpecParam 获取规格参数
// 只获取enable的规格
func (h *WaterLevelHandler) getSpecParam() map[string]string {
	return map[string]string{
		"enable": "true",
	}
}

// WaterLevelStatisticItem 水位统计项
type WaterLevelStatisticItem struct {
	SpecId          int    `json:"spec_id"`
	SpecName        string `json:"spec_name"`
	SpecMachineType string `json:"spec_machine_type"`
	SpecClusterType string `json:"spec_cluster_type"`
	City            string `json:"city"`
	SubZoneId       string `json:"sub_zone_id"`
	SubZoneName     string `json:"sub_zone_name"`
	OsName          string `json:"os_name"`
	OsNameOrigin    string `json:"os_name_origin"`
	Count           int    `json:"count"`
}

// generateMockSpecData 生成基于真实数据库的 mock 规格数据
func generateMockSpecData() []dbmapi.DbmSpec {
	return []dbmapi.DbmSpec{
		// Redis 规格
		createMockSpec(48, "2核_4G_50G", "redis", "twemproxy",
			[]string{"S5.MEDIUM4"}, 0, 0, []dbmapi.RealDiskSpec{}),
	}
}

// createMockSpec 创建单个 mock 规格数据
func createMockSpec(specId int, specName, clusterType, machineType string, deviceClass []string,
	cpu, mem int, storageSpecs []dbmapi.RealDiskSpec) dbmapi.DbmSpec {
	if len(deviceClass) > 0 {
		return dbmapi.DbmSpec{
			SpecId:          specId,
			SpecName:        specName,
			SpecMachineType: machineType,
			SpecClusterType: clusterType,
			DeviceClass:     deviceClass,
			StorageSpecs:    storageSpecs,
		}
	}
	return dbmapi.DbmSpec{
		SpecId:          specId,
		SpecName:        specName,
		SpecMachineType: machineType,
		SpecClusterType: clusterType,
		Mem: meta.FloatMeasureRange{
			Min: float32(mem),
			Max: float32(mem),
		},
		Cpu: meta.MeasureRange{
			Min: cpu,
			Max: cpu,
		},
		StorageSpecs: storageSpecs,
	}

}

// getMockSpecList 获取开发环境的 mock 规格数据
func (h *WaterLevelHandler) getMockSpecList() []dbmapi.DbmSpec {
	return generateMockSpecData()
}

// WaterLevelStatistic 水位统计接口
func (h *WaterLevelHandler) WaterLevelStatistic(c *gin.Context) {
	specList, err := h.getSpecList()
	if err != nil {
		h.SendResponse(c, err, "Failed to get DBM specifications")
		return
	}
	specMap := make(map[int]dbmapi.DbmSpec)
	for _, spec := range specList {
		specMap[spec.SpecId] = spec
	}
	machines, err := h.getUnusedMachines()
	if err != nil {
		h.SendResponse(c, err, "Failed to get machines")
		return
	}

	items, noSpecIpList, osNameMap, subZoneMap := rebuildGroupBySpecItem(machines, specList)
	logger.Info("noSpecIpList: %+v", noSpecIpList)

	groupResult, err := h.executeGroupBy(items)
	if err != nil {
		h.SendResponse(c, err, "Failed to execute group by")
		return
	}

	// 对分组结果进行排序
	sortedGroups := sortGroupResults(groupResult.Groups)

	var result []WaterLevelStatisticResponse
	for _, group := range sortedGroups {
		logger.Info("group: %v, count: %v", group.Keys, group.Count)

		// 安全地获取 OsName，避免类型断言错误
		var osName string
		if osNameVal, exists := group.Keys["os_name"]; exists && osNameVal != nil {
			if osNameStr, ok := osNameVal.(string); ok {
				osName = osNameStr
			}
		}

		// 从映射中获取 OsNameOrigin
		osNameOrigin := ""
		if osName != "" {
			if origin, ok := osNameMap[osName]; ok {
				osNameOrigin = origin
			}
		}

		// 从映射中获取 SubZone
		subZone := ""
		if subZoneId, ok := group.Keys["sub_zone_id"].(string); ok && subZoneId != "" {
			if name, exists := subZoneMap[subZoneId]; exists {
				subZone = name
			}
		}

		specId, ok := group.Keys["spec_id"].(string)
		if !ok {
			specId = ""
		}
		specIdInt, err := strconv.Atoi(specId)
		if err != nil {
			specIdInt = 0
		}

		result = append(result, WaterLevelStatisticResponse{
			City:            group.Keys["city"],
			SubZoneId:       group.Keys["sub_zone_id"],
			SubZone:         subZone,
			SpecId:          specIdInt,
			OsName:          group.Keys["os_name"],
			OsNameOrigin:    osNameOrigin,
			SpecName:        specMap[specIdInt].SpecName,
			SpecClusterType: specMap[specIdInt].SpecClusterType,
			Count:           group.Count,
		})
	}
	logger.Info("sortedGroups: %+v", groupResult.Meta)
	logger.Info("sortedGroups: %+v", groupResult.Total)
	h.SendResponse(c, nil, map[string]interface{}{
		"data":  result,
		"meta":  groupResult.Meta,
		"total": groupResult.Total,
	})
}

// WaterLevelStatisticResponse 水位统计响应结构
type WaterLevelStatisticResponse struct {
	City            interface{} `json:"city"`
	SubZoneId       interface{} `json:"sub_zone_id"`
	SubZone         interface{} `json:"sub_zone"`
	SpecId          interface{} `json:"spec_id"`
	SpecName        string      `json:"spec_name"`
	SpecClusterType string      `json:"spec_cluster_type"`
	OsName          interface{} `json:"os_name"`
	OsNameOrigin    interface{} `json:"os_name_origin"`
	Count           int         `json:"count"`
}

// getSpecList 获取规格列表
func (h *WaterLevelHandler) getSpecList() ([]dbmapi.DbmSpec, error) {
	if config.AppConfig.RunMode == "local" {
		return h.getMockSpecList(), nil
	}
	client := GetDbmClient()
	return client.GetDbmSpec(h.getSpecParam())
}

// getUnusedMachines 获取未使用的机器
func (h *WaterLevelHandler) getUnusedMachines() ([]model.TbRpDetail, error) {
	var machines []model.TbRpDetail
	db := model.DB.Self.Table(model.TbRpDetailName())
	err := db.Find(&machines, "dedicated_biz = 0 and status = ? ", model.Unused).Error
	return machines, err
}

// executeGroupBy 执行分组统计
func (h *WaterLevelHandler) executeGroupBy(items []GroupBySpecItem) (*MultiDimensionGroupByResult, error) {
	groupBy := NewMultiDimensionGroupBy().AddGroupField("city", StringKeyExtractor("City")).
		AddGroupField("sub_zone_id", StringKeyExtractor("SubZoneId")).
		AddGroupField("spec_id", StringKeyExtractor("SpecId")).
		AddGroupField("os_name", StringKeyExtractor("OsName")).
		AddAggregation("count", Count)
	items2 := lo.Map(items, func(item GroupBySpecItem, _ int) interface{} {
		return item
	})
	return groupBy.Execute(items2)
}

// GroupBySpecItem 按规格分组的项
type GroupBySpecItem struct {
	SpecId          int    `json:"spec_id"`
	SpecName        string `json:"spec_name"`
	SpecMachineType string `json:"spec_machine_type"`
	SpecClusterType string `json:"spec_cluster_type"`
	BkHostID        int    `json:"bk_host_id"`
	City            string `json:"city"`
	SubZoneId       string `json:"sub_zone_id"`
	SubZoneName     string `json:"sub_zone_name"`
	OsName          string `json:"os_name"`
}

func rebuildGroupBySpecItem(rsList []model.TbRpDetail, specList []dbmapi.DbmSpec) (
	items []GroupBySpecItem, noSpecIpList []string, osNameMap map[string]string, subZoneMap map[string]string) {
	ctrlChan := make(chan struct{}, 10)
	wg := sync.WaitGroup{}
	lc := sync.Mutex{}
	osNameMap = make(map[string]string)
	subZoneMap = make(map[string]string)
	for _, rs := range rsList {
		osNameMap[rs.OsName] = rs.OsNameOrigin
		subZoneMap[rs.SubZoneID] = rs.SubZone
		for _, spec := range specList {
			wg.Add(1)
			go func(xrs model.TbRpDetail, xspec dbmapi.DbmSpec) {
				ctrlChan <- struct{}{}
				defer func() {
					<-ctrlChan
					wg.Done()
				}()
				if xrs.MatchDbmSpec(xspec) {
					lc.Lock()
					items = append(items, GroupBySpecItem{
						SpecId:          xspec.SpecId,
						SpecName:        xspec.SpecName,
						SpecMachineType: xspec.SpecMachineType,
						SpecClusterType: xspec.SpecClusterType,
						BkHostID:        xrs.BkHostID,
						City:            xrs.City,
						SubZoneId:       xrs.SubZoneID,
						SubZoneName:     xrs.SubZone,
						OsName:          xrs.OsName,
					})
					lc.Unlock()
				}
			}(rs, spec)
		}
	}
	wg.Wait()
	return items, noSpecIpList, osNameMap, subZoneMap
}

// sortGroupResults 对分组结果按 count 降序排序
func sortGroupResults(groups []GroupResult) []GroupResult {
	// 创建副本避免修改原始数据
	sorted := make([]GroupResult, len(groups))
	copy(sorted, groups)

	// 按 count 降序排序
	sort.Slice(sorted, func(i, j int) bool {
		return sorted[i].Count > sorted[j].Count
	})

	return sorted
}
