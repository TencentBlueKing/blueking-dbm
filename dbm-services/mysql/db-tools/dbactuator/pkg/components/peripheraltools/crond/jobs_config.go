package crond

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"os"
	"path"

	"github.com/pkg/errors"
	"gopkg.in/yaml.v2"
)

func (c *MySQLCrondComp) TouchJobsConfig() (err error) {
	jobsConfigFilePath := path.Join(cst.MySQLCrondInstallPath, "jobs-config.yaml")
	if _, err = os.Stat(jobsConfigFilePath); errors.Is(err, os.ErrNotExist) {
		jc := struct {
			Jobs    []int `yaml:"jobs"` // 实际这里不是 int, 但是这不重要, 反正是空的, 占位而已
			BkBizId int   `yaml:"bk_biz_id"`
		}{
			Jobs:    nil,
			BkBizId: c.Params.BkBizId,
		}
		content, err := yaml.Marshal(jc)
		if err != nil {
			logger.Error("marshal init jobs config file failed: %s", err.Error())
			return err
		}

		f, err := os.OpenFile(
			jobsConfigFilePath,
			os.O_CREATE|os.O_TRUNC|os.O_WRONLY,
			0644,
		)
		if err != nil {
			logger.Error("create jobs config failed: %s", err.Error())
			return err
		}

		_, err = f.Write(content)
		if err != nil {
			logger.Error("write jobs config failed: %s", err.Error())
			return err
		}
	}
	return nil
}
