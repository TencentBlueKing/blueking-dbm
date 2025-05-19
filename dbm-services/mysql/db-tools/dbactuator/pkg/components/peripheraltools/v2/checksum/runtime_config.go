package checksum

import (
	"bytes"
	"dbm-services/common/reverseapi"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"fmt"
	"os/exec"
	"path/filepath"
	"strings"

	"dbm-services/common/go-pubpkg/logger"

	"github.com/pkg/errors"
)

func (c *MySQLChecksumComp) GenerateRuntimeConfig() (err error) {
	nginxAddrs, err := reverseapi.ReadNginxProxyAddrs(
		filepath.Join(reverseapi.DefaultCommonConfigDir, reverseapi.DefaultNginxProxyAddrsFileName),
	)
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	return GenConfig(c.Params.BkCloudId, nginxAddrs, c.Params.Ports)
}

func GenConfig(bkCloudId int64, nginxAddrs []string, ports []int) error {
	t, err := tools.NewToolSetWithPick(tools.ToolMysqlTableChecksum)
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	genCmdStr := fmt.Sprintf(
		"%s gen-config --bk-cloud-id %d --nginx-address %s",
		t.MustGet(tools.ToolMysqlTableChecksum),
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
