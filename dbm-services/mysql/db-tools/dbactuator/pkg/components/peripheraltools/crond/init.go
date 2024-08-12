package crond

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
)

type MySQLCrondComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       *MySQLCrondParam         `json:"extend"`
	tools        *tools.ToolSet
}

func (c *MySQLCrondComp) Init() error {
	c.tools = tools.NewToolSetWithPickNoValidate(tools.ToolMySQLCrond)
	err := c.Params.Check()
	if err != nil {
		return err
	}
	return nil
}

type MySQLCrondParam struct {
	components.Medium
	Ip               string `json:"ip"`
	BkCloudId        int    `json:"bk_cloud_id"`
	EventDataId      int    `json:"event_data_id"`
	EventDataToken   string `json:"event_data_token"`
	MetricsDataId    int    `json:"metrics_data_id"`
	MetricsDataToken string `json:"metrics_data_token"`
	BeatPath         string `json:"beat_path"`
	AgentAddress     string `json:"agent_address"`
	BkBizId          int    `json:"bk_biz_id"`
}

type runtimeConfig struct {
	IP               string
	BkCloudId        int
	EventDataId      int
	EventDataToken   string
	MetricsDataId    int
	MetricsDataToken string
	LogPath          string
	PidPath          string
	InstallPath      string
	BeatPath         string
	AgentAddress     string
}
