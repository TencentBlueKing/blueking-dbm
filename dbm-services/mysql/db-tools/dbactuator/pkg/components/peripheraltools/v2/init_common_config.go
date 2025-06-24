package peripheraltools

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/common/reverseapi"
	reversemysqlapi "dbm-services/common/reverseapi/apis/mysql"
	"dbm-services/common/reverseapi/define"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
	"os"
	"os/user"
	"path/filepath"
)

type InitCommonConfig struct {
	Param *InitCommonConfigParam `json:"extend"`
}

type InitCommonConfigParam struct {
	NginxAddrs []string `json:"nginx_addrs"`
	BkCloudId  int64    `json:"bk_cloud_id"`
}

func (c *InitCommonConfig) Run() (err error) {
	if len(c.Param.NginxAddrs) == 0 {
		err = fmt.Errorf("no nginx addresses specified")
		logger.Error(err.Error())
		return err
	}

	err = os.MkdirAll(define.DefaultCommonConfigDir, 0777)
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	err = c.initNginx()
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	err = c.initInstanceInfo()
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	cu, err := user.Current()
	if err != nil {
		logger.Error(err.Error())
		return err
	}
	if cu.Uid == "0" {
		_, err = osutil.ExecShellCommand(
			false,
			fmt.Sprintf(`chown -R mysql %s`, define.DefaultCommonConfigDir),
		)
		if err != nil {
			logger.Error(err.Error())
			return err
		}
	}

	return nil
}

func (c *InitCommonConfig) initNginx() (err error) {
	fp := filepath.Join(define.DefaultCommonConfigDir, define.DefaultNginxProxyAddrsFileName)
	f, err := os.OpenFile(fp, os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0777)
	if err != nil {
		logger.Error(err.Error())
		return err
	}
	defer func() {
		_ = f.Close()
	}()

	for _, nginxAddr := range c.Param.NginxAddrs {
		_, err = f.WriteString(nginxAddr + "\n")
		if err != nil {
			logger.Error(err.Error())
			return err
		}
	}

	return nil
}

func (c *InitCommonConfig) initInstanceInfo() (err error) {
	fp := filepath.Join(define.DefaultCommonConfigDir, define.DefaultInstanceInfoFileName)
	f, err := os.OpenFile(fp, os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0777)
	if err != nil {
		logger.Error(err.Error())
		return err
	}
	defer func() {
		_ = f.Close()
	}()

	apiCore, err := reverseapi.NewCoreWithAddr(c.Param.BkCloudId, c.Param.NginxAddrs...)
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	data, _, err := reversemysqlapi.ListInstanceInfo(apiCore)
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	_, err = f.WriteString(string(data))
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	return nil
}

func (c *InitCommonConfig) Example() interface{} {
	return InitCommonConfig{
		Param: &InitCommonConfigParam{
			NginxAddrs: []string{"fake_ip1:13333", "fake_ip2:13333"},
		},
	}
}
