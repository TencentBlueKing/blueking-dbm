package crond

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

func (c *MySQLCrondComp) GenerateRuntimeConfig() (err error) {
	nginxAddrs, err := pkg.ReadNginxProxyAddrs(
		filepath.Join(define.DefaultCommonConfigDir, define.DefaultNginxProxyAddrsFileName),
	)
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	return GenConfig(int64(c.Params.BkCloudId), nginxAddrs)
}

func GenConfig(bkCloudId int64, nginxAddrs []string) error {
	t, err := tools.NewToolSetWithPick(tools.ToolMySQLCrond)
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	genCmdStr := fmt.Sprintf(
		"%s gen-config --bk-cloud-id %d --nginx-address %s",
		t.MustGet(tools.ToolMySQLCrond),
		bkCloudId,
		strings.Join(nginxAddrs, ","),
	)

	cmd := exec.Command("sh", "-c", genCmdStr)
	logger.Info(genCmdStr)

	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	err = cmd.Run()
	if err != nil {
		logger.Error("%s: %s", err, stderr.String())
		return errors.Wrap(err, stderr.String())
	}

	return nil
}
