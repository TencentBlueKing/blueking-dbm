package checksum

import (
	"fmt"
	"path/filepath"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/internal"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/config"
)

type MySQLChecksumComp struct {
	GeneralParam *components.GeneralParam
	Params       *MySQLChecksumParam
	tools        *tools.ToolSet
}

func (c *MySQLChecksumComp) Init() (err error) {
	c.tools = tools.NewToolSetWithPickNoValidate(tools.ToolMysqlTableChecksum, tools.ToolPtTableChecksum)

	logger.Info("install checksum init success")
	return nil
}

type MySQLChecksumParam struct {
	//components.Medium
	BkBizId      int      `json:"bk_biz_id"`
	IP           string   `json:"ip"`
	Ports        []int    `json:"port_list"`
	Role         string   `json:"role"`
	ClusterId    int      `json:"cluster_id"`
	ImmuteDomain string   `json:"immute_domain"`
	DBModuleId   int      `json:"db_module_id"`
	Schedule     string   `json:"schedule"`
	SystemDbs    []string `json:"system_dbs"`
	ExecUser     string   `json:"exec_user"`
	ApiUrl       string   `json:"api_url"`
	//InstancesInfo  []*instanceInfo `json:"instances_info"`
	StageDBHeader  string `json:"stage_db_header"`
	RollbackDBTail string `json:"rollback_db_tail"`
}

type instanceInfo struct {
	internal.InstanceInfo
	Schedule string `yaml:"schedule"`
}

func NewRuntimeConfig(
	bkBizId, clusterId, port int,
	role, schedule, immuteDomain, ip, user, password, apiUrl, logDir string,
	runtimeHour int,
	tl *tools.ToolSet) *config.Config {
	cfg := config.Config{
		BkBizId: bkBizId,
		Cluster: config.Cluster{
			Id:           clusterId,
			ImmuteDomain: immuteDomain,
		},
		Host: config.Host{
			Ip:       ip,
			Port:     port,
			User:     user,
			Password: password,
		},
		InnerRole:  config.InnerRoleEnum(role),
		ReportPath: filepath.Join(cst.DBAReportBase, "checksum"),
		Slaves:     nil,
		Filter:     config.Filter{},
		PtChecksum: config.PtChecksum{
			Path:     tl.MustGet(tools.ToolPtTableChecksum),
			Switches: []string{},
			Args: []map[string]interface{}{
				{
					"name":  "run-time",
					"value": fmt.Sprintf("%dh", runtimeHour),
				},
			},
			Replicate: fmt.Sprintf("%s.checksum", native.INFODBA_SCHEMA),
		},
		Log: &config.LogConfig{
			Console:    false,
			LogFileDir: &logDir,
			Debug:      false,
			Source:     true,
			Json:       true,
		},
		Schedule: schedule,
		ApiUrl:   apiUrl,
	}

	return &cfg
}
