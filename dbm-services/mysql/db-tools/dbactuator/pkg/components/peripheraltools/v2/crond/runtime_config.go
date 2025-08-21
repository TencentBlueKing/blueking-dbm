package crond

import (
	"bytes"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"fmt"
	"os/exec"
	"strings"

	"github.com/pkg/errors"
)

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
