package peripheraltools

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/v2/checksum"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/v2/crond"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/v2/dbbackup"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/v2/exporter"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/v2/monitor"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/v2/rotatebinlog"

	"github.com/pkg/errors"
)

type GenConfig struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Param        *GenConfigParam          `json:"extend"`
}

type GenConfigParam struct {
	BKCloudId  int64    `json:"bk_cloud_id"`
	IP         string   `json:"ip"`
	Ports      []int    `json:"ports"`
	Departs    []string `json:"departs"`
	NginxAddrs []string `json:"nginx_addrs"`
}

func (c *GenConfig) Run() (err error) {
	for _, depart := range c.Param.Departs {
		err = c.genOne(depart)
		if err != nil {
			logger.Error(err.Error())
			return err
		}
	}
	return nil
}

func (c *GenConfig) genOne(depart string) (err error) {
	if depart == DepartExporter {
		return exporter.GenConfig(c.Param.BKCloudId, c.Param.NginxAddrs, c.Param.Ports...)
	}

	switch depart {
	case DepartMySQLCrond:
		return crond.GenConfig(c.Param.BKCloudId, c.Param.NginxAddrs)
	case DepartMySQLMonitor:
		return monitor.GenConfig(c.Param.BKCloudId, c.Param.NginxAddrs, c.Param.Ports)
	case DepartMySQLDBBackup:
		return dbbackup.GenConfig(c.Param.BKCloudId, c.Param.NginxAddrs, c.Param.Ports)
	case DepartMySQLRotateBinlog:
		return rotatebinlog.GenConfig(c.Param.BKCloudId, c.Param.NginxAddrs, c.Param.Ports)
	case DepartMySQLTableChecksum:
		return checksum.GenConfig(c.Param.BKCloudId, c.Param.NginxAddrs, c.Param.Ports)
	default:
		err = errors.New("unknown depart " + depart)
		logger.Error(err.Error())
		return nil
	}
}

func (c *GenConfig) Example() interface{} {
	return GenConfig{
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountMonitorExample,
			},
		},
		Param: &GenConfigParam{
			BKCloudId:  0,
			IP:         "1.1.1.1",
			Ports:      []int{3306},
			Departs:    []string{DepartExporter, DepartMySQLCrond},
			NginxAddrs: []string{"2.2.2.2:88"},
		}}
}
