package monitor

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
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

	return nil
}

type portBkInstancePair struct {
	Port         int   `json:"port"`
	BkInstanceId int64 `json:"bk_instance_id"`
}

type MySQLMonitorParam struct {
	SystemDbs          []string                       `json:"system_dbs"`
	ExecUser           string                         `json:"exec_user"`
	ApiUrl             string                         `json:"api_url"`
	MachineType        string                         `json:"machine_type"`
	BkCloudId          int                            `json:"bk_cloud_id"`
	BKBizId            int                            `json:"bk_biz_id"`
	PortBkInstanceList []portBkInstancePair           `json:"port_bk_instance_list"`
	IP                 string                         `json:"ip"`
	Role               string                         `json:"role"`
	ImmuteDomain       string                         `json:"immute_domain"`
	ClusterId          int                            `json:"cluster_id"`
	ItemsConfig        map[string]*config.MonitorItem `json:"items_config" yaml:"items_config"`
	DBModuleId         int                            `json:"db_module_id"`
}
