package dbbackup

import (
	"fmt"
	"path/filepath"
	"text/template"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/common/go-pubpkg/mysqlcomm"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"

	"github.com/pkg/errors"
	"gopkg.in/ini.v1"
)

func (c *NewDbBackupComp) GenerateRuntimeConfig() (err error) {
	if c.Params.UntarOnly {
		logger.Info("untar_only=true do not need GenerateDbbackupConfig")
		return nil
	}
	// 先渲染模版配置文件
	templatePath := filepath.Join(c.installPath, fmt.Sprintf("%s.tpl", cst.BackupFile))
	if err := saveTplConfigfile(c.Params.Configs, templatePath); err != nil {
		return err
	}

	cnfTemp, err := template.ParseFiles(templatePath)
	if err != nil {
		return errors.WithMessage(err, "template ParseFiles failed")
	}

	for _, port := range c.Params.Ports {
		_, err := writeCnf(port, c.installPath, c.renderCnf, cnfTemp)
		if err != nil {
			return err
		}
		if c.Params.Role == cst.BackupRoleSpiderMaster {
			cnfPath, err := writeCnf(mysqlcomm.GetTdbctlPortBySpider(port), c.installPath, c.renderCnf, cnfTemp)
			if err != nil {
				return err
			}

			tdbCtlCnfIni, err := ini.Load(cnfPath)
			if err != nil {
				return err
			}

			var tdbCtlCnf config.BackupConfig
			err = tdbCtlCnfIni.MapTo(&tdbCtlCnf)
			if err != nil {
				return err
			}

			tdbCtlCnf.LogicalBackup.DefaultsFile = filepath.Join(c.installPath, "mydumper_for_tdbctl.cnf")
			err = tdbCtlCnfIni.ReflectFrom(&tdbCtlCnf)
			if err != nil {
				return err
			}
			err = tdbCtlCnfIni.SaveTo(cnfPath)
			if err != nil {
				return err
			}
		}
	}
	return nil
}
