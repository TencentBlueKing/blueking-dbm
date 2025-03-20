package exporter

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"
	"os"
	"path/filepath"
)

type PushCnfComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       *PushCnfParams           `json:"extend"`
}

type PushCnfParams struct {
	IP          string `json:"ip"`
	PortList    []int  `json:"port_list"`
	MachineType string `json:"machine_type"`
}

func (c *PushCnfComp) Run() (err error) {
	if c.Params.MachineType == "proxy" {
		for _, port := range c.Params.PortList {
			err = c.generateProxyExporterCnf(c.Params.IP, port)
			if err != nil {
				return err
			}
		}
		return nil
	}

	for _, port := range c.Params.PortList {
		err = c.generateMySQLExporterCnf(c.Params.IP, port)
		if err != nil {
			return err
		}
	}
	return nil
}

func (c *PushCnfComp) generateProxyExporterCnf(ip string, port int) (err error) {
	f, err := makeCnfFile(port)
	if err != nil {
		return err
	}
	defer func() {
		_ = f.Close()
	}()

	content := fmt.Sprintf(
		`%s:%d,,,%s:%d,%s,%s`,
		ip, port,
		ip, native.GetProxyAdminPort(port),
		c.GeneralParam.RuntimeAccountParam.ProxyAdminUser, c.GeneralParam.RuntimeAccountParam.ProxyAdminPwd,
	)

	_, err = f.WriteString(content)
	if err != nil {
		logger.Error(err.Error())
		return err
	}
	return nil
}

func (c *PushCnfComp) generateMySQLExporterCnf(ip string, port int) (err error) {
	err = util.CreateExporterConf(
		makeCnfFilePath(port),
		ip, port,
		c.GeneralParam.RuntimeAccountParam.MonitorUser,
		c.GeneralParam.RuntimeAccountParam.MonitorPwd)
	if err != nil {
		logger.Error(err.Error())
		return err
	}
	return nil
}

func makeCnfFile(port int) (*os.File, error) {
	f, err := os.OpenFile(makeCnfFilePath(port), os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0644)
	if err != nil {
		logger.Error(err.Error())
		return nil, err
	}
	return f, nil
}

func makeCnfFilePath(port int) string {
	return filepath.Join(
		"/etc/",
		fmt.Sprintf("exporter_%d.cnf", port),
	)
}

func (c *PushCnfComp) Example() interface{} {
	return PushCnfComp{
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountMonitorExample,
			},
		},
		Params: &PushCnfParams{
			IP:          "1.2.3.4",
			PortList:    []int{1, 2, 3},
			MachineType: "proxy",
		},
	}
}
