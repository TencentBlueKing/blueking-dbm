package mysql

import (
	"errors"
	"fmt"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/computil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

const (
	// OPTypeUpsert TODO
	OPTypeUpsert = "upsert"
	// OPTypeRemove TODO
	OPTypeRemove = "remove"
)

// MycnfChangeComp 需要将 BaseInputParam 转换成 Comp 参数
type MycnfChangeComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       MycnfChangeParam         `json:"extend"`

	// 自动判断的是否 需要重启
	needRestart bool
	ConnMap     map[Port]*native.DbWorker `json:"-"`
	CnfMap      map[Port]*util.CnfFile    `json:"-"`
	socketMap   map[Port]string
	adminUser   string
	adminPwd    string
}

// Example TODO
func (c *MycnfChangeComp) Example() interface{} {
	comp := MycnfChangeComp{
		Params: MycnfChangeParam{
			Items: map[string]*ConfItemOp{
				"mysqld.binlog_format": {
					ConfValue:   "ROW",
					OPType:      "upsert",
					NeedRestart: false,
				},
				"mysqld.innodb_buffer_pool_size": {
					ConfValue:   "4096M",
					OPType:      "upsert",
					NeedRestart: true,
				},
			},
			Persistent: 2,
			Restart:    2,
			// TgtInstance: common.InstanceObjExample,
		},
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountAdminExample,
			},
		},
	}
	return comp
}

// 偷个懒：目前只支持修改 mysqld
// 注释说明：
//   runtime: 配置当前运行值，set global 生效
//   file: my.cnf 里面的持久化值

// MycnfChangeParam 修改 my.cnf 参数
// 注意, op_type=remove 时，会直接操作文件持久化该配置项改动，不受 persistent 影响
// 移除一个配置项时，代表要回归系统的默认值（不是配置中心plat或者其它地方定义的默认值），因为我们不知道这个值所以不修改 runtime
type MycnfChangeParam struct {
	Items map[string]*ConfItemOp `json:"items" validate:"required"`
	// 是否持久化到 my.cnf 文件，
	// -1: set global var，但不持久化到文件
	// 1: set global var，且持久化到文件
	// 2: 仅持久化，针对部分变量不支持 set global (read only)
	Persistent int `json:"persistent" validate:"required" enums:"-1,1,2"`
	// 指定是否 允许重启, -1:不重启, 1: 重启, 2:根据 items need_restart 自动判断是否重启
	Restart int    `json:"restart" validate:"required" enums:"-1,1,2"`
	Host    string `json:"host"`
	Ports   []int  `json:"ports"`
}

func (m MycnfChangeParam) justModiftMyCnfCannotRestart() bool {
	return m.Persistent == 2
}

func (m MycnfChangeParam) persistentCnf() bool {
	return m.Persistent == 1
}

// ConfItemOp TODO`
type ConfItemOp struct {
	// ConfName  string `json:"conf_name" validate:"required"`
	ConfValue string `json:"conf_value"`
	// 配置项修改动作，允许值 `upsert`,`remove`
	OPType      string `json:"op_type" form:"op_type" validate:"required,enums" enums:"upsert,remove"`
	NeedRestart bool   `json:"need_restart,omitempty"`

	confValueOld string
}

// Init init
func (c *MycnfChangeComp) Init() (err error) {
	c.ConnMap = make(map[Port]*native.DbWorker)
	c.socketMap = make(map[Port]string)
	c.CnfMap = make(map[int]*util.CnfFile)
	c.adminUser = c.GeneralParam.RuntimeAccountParam.AdminUser
	c.adminPwd = c.GeneralParam.RuntimeAccountParam.AdminPwd
	for _, port := range c.Params.Ports {
		dbConn, err := native.InsObject{
			Host: c.Params.Host,
			Port: port,
			User: c.adminUser,
			Pwd:  c.adminPwd,
		}.Conn()
		if err != nil {
			logger.Error("Connect %d failed:%s", port, err.Error())
			return err
		}
		// 备份原配置文件
		bakFile := util.GetMyCnfFileName(port) + time.Now().Format(".20060102150405")
		stderr, errx := osutil.StandardShellCommand(false, fmt.Sprintf("cp %s %s", util.GetMyCnfFileName(port), bakFile))
		if errx != nil {
			logger.Warn("backup origin my.cnf failed %s,stderr:%s", errx, stderr)
		}
		c.ConnMap[port] = dbConn
		cnf := &util.CnfFile{FileName: util.GetMyCnfFileName(port)}
		if err := cnf.Load(); err != nil {
			return err
		}
		socket, err := cnf.GetMySQLSocket()
		if err != nil {
			return err
		}
		c.socketMap[port] = socket
		c.CnfMap[port] = cnf
	}
	return nil
}

// PreCheck pre run pre check
func (c *MycnfChangeComp) PreCheck() (err error) {
	var errList []error
	for _, port := range c.Params.Ports {
		for k, v := range c.Params.Items {
			sk := util.GetSectionFromKey(k, true)
			switch {
			case v.OPType == OPTypeUpsert:
				// 如果是持久化配置文件，就检查配置文件里面的变量
				if c.Params.justModiftMyCnfCannotRestart() {
					/*
						myCnf := &util.CnfFile{FileName: util.GetMyCnfFileName(port)}
						if v.confValueOld, err = myCnf.GetMySQLCnfByKey(sk.Section, sk.Key); err != nil {
							errList = append(errList, err)
							continue
						}
					*/
					if v.confValueOld, err = c.CnfMap[port].GetMySQLCnfByKey(sk.Section, sk.Key); err != nil {
						errList = append(errList, err)
						continue
					}
					logger.Warn("change [%s]%s new: %s. old: %s", sk.Section, sk.Key, v.ConfValue, v.confValueOld)
				}
				// 如果只修改mysql runtime set global
				if c.Params.persistentCnf() {
					if sk.Section != util.MysqldSec {
						continue
					}
					conn, ok := c.ConnMap[port]
					if !ok {
						return fmt.Errorf("get %d conn failed", port)
					}
					v.confValueOld, err = conn.GetSingleGlobalVar(sk.Key) // valRuntime
					logger.Warn("change cnf: [%s]%s new: %s. old: %s", sk.Section, sk.Key, v.ConfValue, v.confValueOld)
					if err != nil {
						errList = append(errList, err)
						continue
					}
					if v.ConfValue != v.confValueOld {
						if v.NeedRestart {
							c.needRestart = true
						}
					}
				}
			case v.OPType == OPTypeRemove:
				c.needRestart = v.NeedRestart
				continue
			default:
				return fmt.Errorf("unknown op_type %s", v.OPType)
			}
		}
	}
	if len(errList) > 0 {
		return errors.Join(errList...)
	}
	return nil
}

func (c *MycnfChangeComp) DoInstance(port int, myCnf *util.CnfFile) (err error) {
	conn, ok := c.ConnMap[port]
	if !ok {
		return fmt.Errorf("get %d conn failed", port)
	}
	for k, v := range c.Params.Items {
		sk := util.GetSectionFromKey(k, true)
		switch v.OPType {
		case OPTypeUpsert:
			switch {
			case c.Params.Persistent < 1:
				if sk.Section == util.MysqldSec {
					setVar := fmt.Sprintf("set global %s = %s", sk.Key, v.ConfValue)
					if _, err := conn.Exec(setVar); err != nil {
						// Error 1238: Variable 'lower_case_table_names' is a read only variable
						if !strings.Contains(err.Error(), "Error 1238:") {
							return err
						}
						logger.Warn("needRestart %s", err.Error())
						c.Params.Items[k].NeedRestart = true
						c.needRestart = true
					}
				}
			case c.Params.Persistent >= 1:
				myCnf.ReplaceValue(sk.Section, common.MapNameVarToConf(sk.Key), false, v.ConfValue)
			}
		case OPTypeRemove:
			myCnf.ReplaceValue(sk.Section, common.MapNameVarToConf(sk.Key), false, v.ConfValue)
		}
	}
	logger.Info("change_cnf param: %+v", c)
	if c.Params.Persistent >= 1 {
		if err := myCnf.SafeSaveFile(false); err != nil {
			return err
		}
	}
	if c.Params.justModiftMyCnfCannotRestart() && c.needRestart {
		logger.Error("need to restart mysqld but not run restart")
	}
	if c.needRestart || c.Params.Restart >= 1 {
		if err := computil.RestartMysqlInstanceNormal(native.InsObject{
			Host:   c.Params.Host,
			Port:   port,
			User:   c.adminUser,
			Pwd:    c.adminPwd,
			Socket: c.socketMap[port],
		}); err != nil {
			return err
		}
	}
	return
}

// Start  change my.cnf
func (c *MycnfChangeComp) Start() error {
	for _, port := range c.Params.Ports {
		logger.Info("start change  %d's my.cnf ", port)
		if err := c.DoInstance(port, c.CnfMap[port]); err != nil {
			logger.Error("change %d my.cnf failed %v", port, err)
			return err
		}
	}
	return nil
}
