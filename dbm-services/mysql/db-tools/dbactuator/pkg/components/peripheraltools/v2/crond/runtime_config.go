package crond

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"os"
	"path"
	"path/filepath"
	"text/template"
)

func (c *MySQLCrondComp) GenerateRuntimeConfig() (err error) {
	t, err := template.ParseFiles(path.Join(cst.MySQLCrondInstallPath, "mysql-crond.conf.go.tpl"))
	if err != nil {
		logger.Error("read mysql-crond runtime config template failed: %s", err.Error())
		return err
	}

	f, err := os.OpenFile(
		filepath.Join(cst.MySQLCrondInstallPath, "runtime.yaml"),
		os.O_CREATE|os.O_TRUNC|os.O_WRONLY,
		0644,
	)
	if err != nil {
		logger.Error("create mysql-crond runtime.yaml failed: %s", err.Error())
		return err
	}
	defer func() {
		_ = f.Close()
	}()

	cfg := runtimeConfig{
		IP:               c.Params.Ip,
		BkCloudId:        c.Params.BkCloudId,
		EventDataId:      c.Params.EventDataId,
		EventDataToken:   c.Params.EventDataToken,
		MetricsDataId:    c.Params.MetricsDataId,
		MetricsDataToken: c.Params.MetricsDataToken,
		LogPath:          path.Join(cst.MySQLCrondInstallPath, "logs"),
		PidPath:          cst.MySQLCrondInstallPath,
		InstallPath:      cst.MySQLCrondInstallPath,
		BeatPath:         c.Params.BeatPath,
		AgentAddress:     c.Params.AgentAddress,
	}

	err = t.Execute(f, cfg)
	if err != nil {
		logger.Error("execute template for mysql-crond failed: %s", err.Error())
		return err
	}
	return nil
}
