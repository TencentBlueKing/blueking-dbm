package internal

import (
	"bytes"
	"dbm-services/common/go-pubpkg/logger"
	"fmt"
	"os/exec"
)

func RegisterCrond(toolPath, configPath, user string) error {
	command := exec.Command(
		"su", []string{
			"-", "mysql", "-c",
			fmt.Sprintf("%s reschedule --staff %s --config %s", toolPath, user, configPath),
		}...,
	)
	logger.Info(command.String())

	var stderr bytes.Buffer
	command.Stderr = &stderr

	err := command.Run()
	if err != nil {
		logger.Error("%s: %s", err.Error(), stderr.String())
		return err
	}
	return nil
}
