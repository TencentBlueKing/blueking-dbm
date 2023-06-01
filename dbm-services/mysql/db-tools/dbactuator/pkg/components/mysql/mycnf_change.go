package mysql

import (
	"fmt"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/computil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/pkg/errors"
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
			Persistent:  2,
			Restart:     2,
			TgtInstance: common.InstanceObjExample,
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
	// 是否持久化到 my.cnf 文件，-1: 不持久化，1: 持久化, 2: 仅持久化但不修改运行时
	Persistent int `json:"persistent" validate:"required" enums:"-1,1,2"`
	// 指定是否 允许重启, -1:不重启, 1: 重启, 2:根据 items need_restart 自动判断是否重启
	Restart     int              `json:"restart" validate:"required" enums:"-1,1,2"`
	TgtInstance native.InsObject `json:"tgt_instance" validate:"required"`

	// 自动判断的是否 需要重启
	needRestart bool
	myCnf       *util.CnfFile
	dbworker    *native.DbWorker
}

// ConfItemOp TODO
type ConfItemOp struct {
	// ConfName  string `json:"conf_name" validate:"required"`
	ConfValue string `json:"conf_value"`
	// 配置项修改动作，允许值 `upsert`,`remove`
	OPType      string `json:"op_type" form:"op_type" validate:"required,enums" enums:"upsert,remove"`
	NeedRestart bool   `json:"need_restart,omitempty"`

	confValueOld string
}

// Init TODO
func (c *MycnfChangeParam) Init() (err error) {
	f := util.GetMyCnfFileName(c.TgtInstance.Port)
	c.myCnf = &util.CnfFile{FileName: f}
	if err = c.myCnf.Load(); err != nil {
		return err
	}
	if c.TgtInstance.Socket == "" {
		if c.TgtInstance.Socket, err = c.myCnf.GetMySQLSocket(); err != nil {
			return err
		}
	}
	/*
		if c.Persistent == 2 && c.Restart >= 1 {
			return errors.New("only persistent to file should not work with restart")
		}
	*/
	return nil
}

// PreCheck 前置检查
// 会初始化 needRestart
func (c *MycnfChangeParam) PreCheck() error {
	var errList []error
	var err error
	// persistent == 2 时表示不修改运行时，所以不检查连接性。修改配置只能操作 my.cnf 已有项
	// 即关机状态下不允许写入新的配置项，因为没法判断配置项是否合法。但可以 remove
	if c.Persistent == 2 {
		for k, v := range c.Items {
			sk := util.GetSectionFromKey(k, true)
			if v.OPType != OPTypeRemove {
				if v.confValueOld, err = c.myCnf.GetMySQLCnfByKey(sk.Section, sk.Key); err != nil {
					errList = append(errList, err)
				} else {
					logger.Warn("change [%s]%s new: %s. old: %s", sk.Section, sk.Key, v.ConfValue, v.confValueOld)
				}
			}
			// 仅写到文件，也判断是否需要重启。但如果进程没在运行，则不启动
			if v.NeedRestart && computil.IsInstanceRunning(c.TgtInstance) {
				c.needRestart = true
			}
		}
	} else if c.Persistent <= 1 {
		// 判断连接性
		if dbw, err := c.TgtInstance.Conn(); err != nil {
			return err
		} else {
			c.dbworker = dbw
		}
		for k, v := range c.Items {
			if v.OPType == OPTypeRemove { // 不校验 key 是否存在
				if v.NeedRestart {
					c.needRestart = true
				}
				continue
			}
			sk := util.GetSectionFromKey(k, true)
			if sk.Section != util.MysqldSec {
				continue
			}
			v.confValueOld, err = c.dbworker.GetSingleGlobalVar(sk.Key) // valRuntime
			logger.Warn("change cnf: [%s]%s new: %s. old: %s", sk.Section, sk.Key, v.ConfValue, v.confValueOld)
			if err != nil {
				errList = append(errList, err)
			} else if v.ConfValue != v.confValueOld {
				if v.NeedRestart {
					c.needRestart = true
				}
			} else {
				// 运行值与修改值相同，不必重启. 但不妨碍多修改一次
			}
		}
	} else {
		return errors.Errorf("unknown persistent %d", c.Persistent)
	}
	if len(errList) > 0 {
		return util.SliceErrorsToError(errList)
	}
	return nil
}

// Start TODO
func (c *MycnfChangeParam) Start() error {
	for k, v := range c.Items {
		sk := util.GetSectionFromKey(k, true)
		if v.OPType == OPTypeUpsert {
			if sk.Section == util.MysqldSec && c.Persistent <= 1 { // 只有 mysqld 才需要 set global
				setVar := fmt.Sprintf("set global %s = %s", sk.Key, v.ConfValue)
				if _, err := c.dbworker.Exec(setVar); err != nil {
					// Error 1238: Variable 'lower_case_table_names' is a read only variable
					if !strings.Contains(err.Error(), "Error 1238:") {
						return err
					} else {
						logger.Warn("needRestart %s", err.Error())
						c.Items[k].NeedRestart = true
						c.needRestart = true
					}
				}
			}
			if c.Persistent >= 1 {
				c.myCnf.ReplaceValue(sk.Section, common.MapNameVarToConf(sk.Key), false, v.ConfValue)
			}
		} else if v.OPType == OPTypeRemove {
			// 直接从文件移除，然后判断是否需要重启
			// 移除配置项，不校验配置项名字是否合法、是否在文件存在，因为有可能就是要移除一个非法名字
			// 移除配置项，只操作 file，不影响 runtime，移除后的具体效果，取决于改配置项自己的默认值。而是否回归默认值取决于 need_restart
			// 这个 need_restart 与该配置项是否需要重启属性无关，而是指定是否进行重启。
			//  举个例子,slave_exec_mode 本身 need_restart 属性是 0(false)，但现在把它从 my.cnf 移除时不代表它 runtime 马上回归默认（因为没法知道 slave_exec_mode 在 mysqld 的默认值，哪怕在配置中心 plat 里面的配置也只是人为定义的默认值）
			c.myCnf.ReplaceValue(sk.Section, common.MapNameVarToConf(sk.Key), false, v.ConfValue)
		} else {
			return errors.Errorf("unknown op_type %s", v.OPType)
		}
	}
	logger.Info("change_cnf param: %+v", c)
	if c.Persistent >= 1 {
		if err := c.myCnf.SafeSaveFile(false); err != nil {
			return err
		}
	}
	if c.Restart == 1 {
		if err := computil.RestartMysqlInstanceNormal(c.TgtInstance); err != nil {
			return err
		}
	} else if c.needRestart {
		if c.Restart >= 1 {
			if err := computil.RestartMysqlInstanceNormal(c.TgtInstance); err != nil {
				return err
			}
		} else if c.Persistent < 1 { // 需要重启，但是却不允许重启
			logger.Error("need to restart mysqld but not run restart")
			// return errors.New("need to restart mysqld but not run restart")
		} else {
			logger.Warn("need to restart mysqld but not run restart")
		}
	}
	// else 即使 restart=
	return nil
}
