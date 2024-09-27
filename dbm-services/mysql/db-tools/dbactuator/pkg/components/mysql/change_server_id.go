package mysql

import (
	"os"
	"path/filepath"
	"strconv"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
)

// ChangeServerIdComp 需要将 BaseInputParam 转换成 Comp 参数
type ChangeServerIdComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       []ChangeServerId         `json:"extend"`

	//mycnfChange  MycnfChangeParam
	mycnfChange map[int]*MycnfChangeComp
	// autoCnfFilePath auto.cnf in datadir
	autoCnfFilePath map[int]string
}

// Example TODO
func (c *ChangeServerIdComp) Example() interface{} {
	comp := ChangeServerIdComp{
		Params: []ChangeServerId{},
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountAdminExample,
			},
		},
	}
	return comp
}

// ChangeServerId 修改 server_id，会重启
type ChangeServerId struct {
	// NewServerId if new_server_id is 0, will auto-generate one
	NewServerId map[int]uint32 `json:"new_server_id"`
	// NewServerUUID if new_server_uuid is empty, will regenerate auto.cnf
	NewServerUUID map[int]string `json:"new_server_uuid"`
	Host          string         `json:"host"`
	Port          int            `json:"port"`
}

// Init init
func (c *ChangeServerIdComp) Init() (err error) {
	c.mycnfChange = make(map[int]*MycnfChangeComp)
	for _, change := range c.Params {
		serverId := mysqlutil.GenMysqlServerIdByRandom()
		mycnfChange := MycnfChangeComp{
			GeneralParam: c.GeneralParam,
			Params: MycnfChangeParam{
				Items: map[string]*ConfItemOp{
					"mysqld.server_id": {
						ConfValue:   strconv.FormatUint(serverId, 10),
						OPType:      "upsert",
						NeedRestart: true,
					},
				},
				Persistent: 2,
				Restart:    2,
				Host:       change.Host,
				Ports:      []int{change.Port},
			},
		}
		if err = mycnfChange.Init(); err != nil {
			return err
		} else {
			c.mycnfChange[change.Port] = &mycnfChange
		}
	}
	return nil
}

// PreCheck pre run pre check
func (c *ChangeServerIdComp) PreCheck() (err error) {
	c.autoCnfFilePath = make(map[int]string)

	for port, mycnfChange := range c.mycnfChange {
		if err = mycnfChange.PreCheck(); err != nil {
			return err
		}

		cnf := mycnfChange.CnfMap[port]
		datadir, err := cnf.GetMySQLDataDir()
		if datadir == "" {
			return errors.Errorf("fail to get datadir for %d from %s", port, cnf.FileName)
		} else if err != nil {
			return err
		}
		c.autoCnfFilePath[port] = filepath.Join(datadir, "data/auto.cnf") // check if exists when actually doing
	}
	return nil
}

// Start  change my.cnf
func (c *ChangeServerIdComp) Start() error {
	for port, change := range c.mycnfChange {
		if cmutil.FileExists(c.autoCnfFilePath[port]) {
			logger.Info("remove server_uuid %s ", c.autoCnfFilePath[port])
			if err := os.Remove(c.autoCnfFilePath[port]); err != nil {
				return errors.WithMessage(err, "remove server_uuid")
			}
		}

		logger.Info("start change my.cnf for %d", port)
		if err := change.DoInstance(port, change.CnfMap[port]); err != nil {
			logger.Error("change %d my.cnf failed %v", port, err)
			return err
		}
	}
	return nil
}
