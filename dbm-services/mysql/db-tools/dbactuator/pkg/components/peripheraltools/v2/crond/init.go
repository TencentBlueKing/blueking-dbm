package crond

import (
	"dbm-services/common/go-pubpkg/logger"
	rcnf "dbm-services/common/reverse-api/config"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
	"os"
	"path/filepath"
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

	// 这里不 return err
	// 就是没下发nginx ip只打印一行日志, 不影响crond部署过程
	if c.Params.NginxAddrs == nil || len(c.Params.NginxAddrs) <= 0 {
		err := fmt.Errorf("nginx addresses are required")
		logger.Error(err.Error())
		return nil
	}

	// 初始化 nginx addrs 配置文件
	err = os.MkdirAll(rcnf.CommonConfigDir, 0777)
	if err != nil {
		logger.Error("mkdir failed", "err", err)
		return err
	}

	f, err := os.OpenFile(
		filepath.Join(
			rcnf.CommonConfigDir,
			rcnf.NginxProxyAddrsFileName),
		os.O_CREATE|os.O_TRUNC|os.O_WRONLY,
		0777,
	)
	if err != nil {
		logger.Error("open file failed", "err", err)
		return err
	}
	defer func() {
		_ = f.Close()
	}()

	for _, addr := range c.Params.NginxAddrs {
		if _, err := f.Write([]byte(addr + "\n")); err != nil {
			logger.Error("write addr failed", "err", err)
			return err
		}
	}

	chownCmd := fmt.Sprintf(`chown -R mysql %s`, rcnf.CommonConfigDir)
	_, err = osutil.ExecShellCommand(false, chownCmd)
	if err != nil {
		logger.Error("exec command failed", "err", err)
		return err
	}

	return nil
}

type MySQLCrondParam struct {
	components.Medium
	Ip               string   `json:"ip"`
	BkCloudId        int      `json:"bk_cloud_id"`
	EventDataId      int      `json:"event_data_id"`
	EventDataToken   string   `json:"event_data_token"`
	MetricsDataId    int      `json:"metrics_data_id"`
	MetricsDataToken string   `json:"metrics_data_token"`
	BeatPath         string   `json:"beat_path"`
	AgentAddress     string   `json:"agent_address"`
	BkBizId          int      `json:"bk_biz_id"`
	NginxAddrs       []string `json:"nginx_addrs"`
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
