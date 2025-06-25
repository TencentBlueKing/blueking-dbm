package monitor

import (
	"bytes"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/common/reverseapi/define"
	"dbm-services/common/reverseapi/pkg"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"fmt"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/pkg/errors"
)

func (c *MySQLMonitorComp) GenConfig() error {
	nginxAddrs, err := pkg.ReadNginxProxyAddrs(
		filepath.Join(define.DefaultCommonConfigDir, define.DefaultNginxProxyAddrsFileName),
	)
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	var ports []int
	for _, ele := range c.Params.PortBkInstanceList {
		ports = append(ports, ele.Port)
	}
	return GenConfig(int64(c.Params.BkCloudId), nginxAddrs, ports)
}

func GenConfig(bkCloudId int64, nginxAddrs []string, ports []int) error {
	t, err := tools.NewToolSetWithPick(tools.ToolMySQLMonitor)
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	genCmdStr := fmt.Sprintf(
		"%s gen-config --bk-cloud-id %d --nginx-address %s",
		t.MustGet(tools.ToolMySQLMonitor),
		bkCloudId,
		strings.Join(nginxAddrs, ","),
	)
	for _, port := range ports {
		genCmdStr += fmt.Sprintf(" --port %d", port)
	}
	logger.Info(genCmdStr)

	cmd := exec.Command("sh", "-c", genCmdStr)
	logger.Info(cmd.String())

	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	err = cmd.Run()
	if err != nil {
		logger.Error("%s: %s", err, stderr.String())
		return errors.Wrap(err, stderr.String())
	}

	return nil
}
