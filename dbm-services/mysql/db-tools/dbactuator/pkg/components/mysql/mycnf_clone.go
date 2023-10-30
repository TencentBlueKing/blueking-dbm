package mysql

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/pkg/errors"
)

// MycnfCloneComp TODO
type MycnfCloneComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       MycnfCloneParam          `json:"extend"`
}

// Example TODO
func (c *MycnfCloneComp) Example() interface{} {
	comp := MycnfCloneComp{
		Params: MycnfCloneParam{
			SrcInstance: common.InstanceObjExample,
			Persistent:  1,
			Restart:     2,
			TgtInstance: common.InstanceObjExample,
			// Items:       []string{"time_zone", "binlog_format", "character_set_server"},
		},
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.MySQLAdminReplExample,
			},
		},
	}
	return comp
}

// MycnfCloneItemsDefault TODO
var MycnfCloneItemsDefault = []string{
	"max_allowed_packet",
	"time_zone",
	"binlog_format",
	"binlog_row_image",
	"lower_case_table_names",
	"character_set_server",
	"collation_server",
	"max_binlog_size",
	"log_bin_compress",
	"net_buffer_length",
	"interactive_timeout",
	"wait_timeout",
	"relay_log_uncompress",

	"slave_parallel_workers",
	"slave_parallel_type",
	"replica_parallel_workers",
	"replica_parallel_type",
}

// MycnfCloneParam godoc
// mycnf-clone 建议 persistent=1, restart=2 选项，表示会持久化到文件，并根据需要重启
type MycnfCloneParam struct {
	// 参数克隆，获取源实例，可以提供 repl 账号权限
	SrcInstance native.InsObject `json:"src_instance" validate:"required"`
	// 应用到本地目标实例，需要有 ADMIN 权限
	TgtInstance native.InsObject `json:"tgt_instance" validate:"required"`

	// 是否持久化到 my.cnf 文件，0: 不持久化，1: 持久化, 2: 仅持久化但不修改运行时
	Persistent int `json:"persistent" validate:"required" enums:"0,1,2" example:"1"`
	// 指定是否 允许重启, 0:不重启, 1: 重启, 2:根据 items need_restart 自动判断是否重启
	Restart int `json:"restart" validate:"required" enums:"0,1,2" example:"2"`
	// 需要克隆哪些变量, 考虑到不同版本参数不一样，这里不要求指定一定存在; 只修改 mysqld 区。即失败忽略
	// 有些参数是 readonly 的，只会保存到 my.cnf 中，如果与运行值不一样需要用户重启
	// 默认值见 MycnfCloneItemsDefault
	Items []string `json:"items"`

	mycnfChange *MycnfChangeParam
}

// Init TODO
func (c *MycnfCloneParam) Init() error {
	// 如果是克隆用户指定的配置，配置名在源不存在则报错
	// 如果用户未指定，即内置配置项同步，考虑到多版本可能存在不同变量需要同步，使用一份配置名列表，于是忽略错误
	ignoreUnknownVars := false
	if len(c.Items) == 0 {
		c.Items = MycnfCloneItemsDefault
		ignoreUnknownVars = true
	}
	c.mycnfChange = &MycnfChangeParam{
		Restart:     c.Restart,
		Persistent:  c.Persistent,
		Items:       map[string]*ConfItemOp{},
		TgtInstance: c.TgtInstance,
	}
	srcDB, err := c.SrcInstance.Conn()
	if err != nil {
		return errors.WithMessage(err, "连接源实例失败")
	}
	for _, varName := range c.Items {
		if val, err := srcDB.GetSingleGlobalVar(varName); err != nil {
			// todo
			errStr := fmt.Sprintf("get variable %s failed: %s", varName, err.Error())
			logger.Error(errStr)
			if !ignoreUnknownVars {
				return errors.New(errStr)
			}
			// continue
		} else {
			varFullName := util.MysqldSec + "." + varName
			c.mycnfChange.Items[varFullName] = &ConfItemOp{
				ConfValue:   val,
				OPType:      OPTypeUpsert,
				NeedRestart: false,
			}
		}
	}

	if err := c.mycnfChange.Init(); err != nil {
		return err
	}
	return nil
}

// PreCheck TODO
func (c *MycnfCloneParam) PreCheck() error {

	if err := c.mycnfChange.PreCheck(); err != nil {
		return err
	}
	logger.Info(" MycnfCloneParam.PreCheck %v", c)
	return nil
}

// Start TODO
func (c *MycnfCloneParam) Start() error {
	if err := c.mycnfChange.Start(); err != nil {
		return err
	}
	return nil
}
