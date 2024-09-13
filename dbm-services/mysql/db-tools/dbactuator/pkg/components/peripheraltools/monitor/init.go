package monitor

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/internal"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
)

type MySQLMonitorComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       *MySQLMonitorParam       `json:"extend"`
	tools        *tools.ToolSet
}

func (c *MySQLMonitorComp) Init() (err error) {
	c.tools = tools.NewToolSetWithPickNoValidate(tools.ToolMySQLMonitor)

	err = c.Params.Medium.Check()
	if err != nil {
		logger.Error(err.Error())
		return err
	}
	return nil
}

type MySQLMonitorParam struct {
	components.Medium
	SystemDbs     []string                       `json:"system_dbs"`
	ExecUser      string                         `json:"exec_user"`
	ApiUrl        string                         `json:"api_url"`
	InstancesInfo []*internal.InstanceInfo       `json:"instances_info"`
	MachineType   string                         `json:"machine_type"`
	BkCloudId     int                            `json:"bk_cloud_id"`
	ItemsConfig   map[string]*config.MonitorItem `json:"items_config" yaml:"items_config"`
}
