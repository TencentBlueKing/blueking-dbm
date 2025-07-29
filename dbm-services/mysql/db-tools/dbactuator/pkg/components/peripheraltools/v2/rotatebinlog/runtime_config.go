package rotatebinlog

import (
	"bytes"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"fmt"
	"os/exec"
	"strings"

	"github.com/pkg/errors"
)

func GenConfig(bkCloudId int64, nginxAddrs []string, ports []int) error {
	t, err := tools.NewToolSetWithPick(tools.ToolMysqlRotatebinlog)
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	genCmdStr := fmt.Sprintf(
		"%s gen-config --bk-cloud-id %d --nginx-address %s",
		t.MustGet(tools.ToolMysqlRotatebinlog),
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
