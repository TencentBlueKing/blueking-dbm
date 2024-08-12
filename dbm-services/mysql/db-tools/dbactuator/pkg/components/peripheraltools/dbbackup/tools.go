package dbbackup

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"text/template"

	"github.com/pkg/errors"
)

func saveTplConfigfile(configs map[string]map[string]string, tmpl string) (err error) {
	f, err := os.OpenFile(tmpl, os.O_CREATE|os.O_RDWR|os.O_TRUNC, 0755)
	if err != nil {
		return errors.WithMessage(err, "新建文件失败")
	}
	defer func() {
		_ = f.Close()
	}()

	var encryptOpt = make(map[string]string)
	var encryptOptPrefix = "EncryptOpt"
	for key, val := range configs {
		_, err := fmt.Fprintf(f, "[%s]\n", key)
		if err != nil {
			return errors.WithMessagef(err, "写配置模版 %s 失败", key)
		}
		for k, v := range val {
			if strings.HasPrefix(k, encryptOptPrefix+".") {
				encryptOpt[strings.TrimPrefix(k, encryptOptPrefix+".")] = v
				continue
			}
			_, err := fmt.Fprintf(f, "%s\t=\t%s\n", k, v)
			if err != nil {
				return errors.WithMessagef(err, "写配置模版 %s, %s 失败", k, v)
			}
		}
		_, _ = fmt.Fprintf(f, "\n")
	}
	if len(encryptOpt) > 0 {
		_, _ = fmt.Fprintf(f, "[%s]\n", encryptOptPrefix)
		for k, v := range encryptOpt {
			_, _ = fmt.Fprintf(f, "%s\t=\t%s\n", k, v)
		}
	}
	return
}

func writeCnf(port int, installPath string, renderCnf map[int]config.BackupConfig, tpl *template.Template) (cnfPath string, err error) {
	cnfPath = filepath.Join(installPath, cst.GetNewConfigByPort(port))
	cnfFile, err := os.OpenFile(cnfPath, os.O_CREATE|os.O_RDWR|os.O_TRUNC, 0755) // os.Create(cnfPath)
	if err != nil {
		return "", errors.WithMessage(err, fmt.Sprintf("create %s failed", cnfPath))
	}
	defer func() {
		_ = cnfFile.Close()
	}()

	if data, ok := renderCnf[port]; ok {
		if err = tpl.Execute(cnfFile, data); err != nil {
			return "", errors.WithMessage(err, "渲染%d的备份配置文件失败")
		}
	} else {
		return "", fmt.Errorf("not found %d render data", port)
	}

	return cnfPath, nil
}
