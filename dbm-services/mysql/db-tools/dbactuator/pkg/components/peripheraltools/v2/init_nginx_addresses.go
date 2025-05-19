package peripheraltools

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/common/reverseapi"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
	"os"
	"os/user"
	"path/filepath"
)

type InitNginxAddresses struct {
	Param *InitNginxAddressesParam `json:"extend"`
}

type InitNginxAddressesParam struct {
	NginxAddrs []string `json:"nginx_addrs"`
}

func (c *InitNginxAddresses) Run() (err error) {
	if len(c.Param.NginxAddrs) == 0 {
		err = fmt.Errorf("no nginx addresses specified")
		logger.Error(err.Error())
		return err
	}

	err = os.MkdirAll(reverseapi.DefaultCommonConfigDir, 0777)
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	fp := filepath.Join(reverseapi.DefaultCommonConfigDir, reverseapi.DefaultNginxProxyAddrsFileName)
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

	cu, err := user.Current()
	if err != nil {
		logger.Error(err.Error())
		return err
	}
	if cu.Uid == "0" {
		_, err = osutil.ExecShellCommand(
			false,
			fmt.Sprintf(`chown -R mysql %s`, reverseapi.DefaultCommonConfigDir),
		)
		if err != nil {
			logger.Error(err.Error())
			return err
		}
	}

	return nil
}

func (c *InitNginxAddresses) Example() interface{} {
	return InitNginxAddresses{
		Param: &InitNginxAddressesParam{
			NginxAddrs: []string{"fake_ip1:13333", "fake_ip2:13333"},
		},
	}
}
