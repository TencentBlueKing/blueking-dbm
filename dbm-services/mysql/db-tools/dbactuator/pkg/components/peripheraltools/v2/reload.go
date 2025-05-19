package peripheraltools

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/v2/checksum"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/v2/crond"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/v2/dbbackup"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/v2/monitor"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/v2/rotatebinlog"
	"fmt"
)

type Reload struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Param        *ReloadParam             `json:"extend"`
}

type ReloadParam struct {
	IP      string   `json:"ip"`
	Ports   []int    `json:"ports"`
	Departs []string `json:"departs"`
}

func (c *Reload) Run() (err error) {
	for _, depart := range c.Param.Departs {
		err = c.reloadDepart(depart)
		if err != nil {
			logger.Error(err.Error())
			return err
		}
	}
	return nil
}

func (c *Reload) reloadDepart(depart string) (err error) {
	switch depart {
	case DepartMySQLCrond:
		err = crond.Stop()
		if err != nil {
			logger.Error(err.Error())
			return err
		}
		err = crond.Start()
		if err != nil {
			logger.Error(err.Error())
			return err
		}
		return nil
	case DepartMySQLRotateBinlog:
		err = rotatebinlog.AddCrond()
		if err != nil {
			logger.Error(err.Error())
			return err
		}
		return nil
	case DepartMySQLTableChecksum:
		err = checksum.AddCrond(c.Param.Ports)
		if err != nil {
			logger.Error(err.Error())
			return err
		}
		return nil
	case DepartMySQLDBBackup:
		err = dbbackup.AddCrond(c.Param.Ports)
		if err != nil {
			logger.Error(err.Error())
			return err
		}
		return nil
	case DepartMySQLMonitor:
		err = monitor.AddCrond(c.Param.Ports)
		if err != nil {
			logger.Error(err.Error())
			return err
		}
		return nil
	default:
		err = fmt.Errorf("unknown depart %s", depart)
		logger.Error(err.Error())
		return nil
	}
}

func (c *Reload) Example() interface{} {
	return Reload{
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountMonitorExample,
			},
		},
		Param: &ReloadParam{
			IP:      "127.0.0.1",
			Ports:   []int{20000},
			Departs: []string{DepartExporter},
		},
	}
}
