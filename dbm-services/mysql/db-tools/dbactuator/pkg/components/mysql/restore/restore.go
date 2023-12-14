// Package restore TODO
package restore

import (
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/dbbackup"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"

	"github.com/pkg/errors"
)

// Restore 备份恢复类的接口定义
type Restore interface {
	Init() error
	PreCheck() error
	Start() error
	WaitDone() error
	PostCheck() error
	ReturnChangeMaster() (*mysqlutil.ChangeMaster, error)
}

// RestoreParam 恢复用到的参数，不区分恢复类型的公共参数
type RestoreParam struct {
	BackupInfo
	// 恢复用到的客户端工具，不提供时会有默认值
	Tools tools.ToolSet `json:"tools"`
	// 恢复本地的目标实例
	TgtInstance native.InsObject `json:"tgt_instance"`
	// 备份实例的 ip port，用于生产 change master 语句。如果 host 为空，表示不检查、不生成change master，恢复spider节点时使用
	SrcInstance native.Instance `json:"src_instance"`
	// 恢复完成后是否执行 change master，会 change master 到 src_instance
	ChangeMaster bool `json:"change_master"`
	// work_id 标识本次恢复，若为0则为当前时间戳
	WorkID string `json:"work_id"`
	// 恢复选项，比如恢复库表、是否导入binlog等。目前只对逻辑恢复有效
	RestoreOpt *RestoreOpt `json:"restore_opts"`
}

// RestoreOpt TODO
type RestoreOpt struct {
	// 恢复哪些 db，当前只对 逻辑恢复有效
	Databases       []string `json:"databases"`
	Tables          []string `json:"tables"`
	IgnoreDatabases []string `json:"ignore_databases"`
	IgnoreTables    []string `json:"ignore_tables"`

	RecoverPrivs bool `json:"recover_privs"`
	// 在指定时间点回档场景才需要，是否恢复 binlog。在 doSlave 场景，是不需要 recover_binlog。这个选项是控制下一步恢复binlog的行为
	// 当 recover_binlog 时，要确保实例的所有库表结构都恢复。在逻辑回档场景，只回档部分库表数据时，依然要恢复所有表结构
	WillRecoverBinlog bool `json:"recover_binlog"`
	// EnableBinlog 导入数据时是否写binlog，默认不启用
	EnableBinlog bool `json:"enable_binlog"`
	// 在库表级定点回档时有用，如果是 statement/mixed 格式，导入数据时需要全部导入；
	// 如果是 row，可只导入指定库表数据, 在 recover-binlog 时可指定 quick_mode=true 也恢复指定库表 binlog
	SourceBinlogFormat string `json:"source_binlog_format" enums:",ROW,STATEMENT,MIXED"`
}

// FilterOpt TODO
type FilterOpt struct {
	Databases       []string `json:"databases"`        // 未使用
	Tables          []string `json:"tables"`           // 未使用
	IgnoreDatabases []string `json:"ignore_databases"` // 添加内置 mysql infodba_schema 库
	IgnoreTables    []string `json:"ignore_tables"`    // 未使用
}

// RestoreDRComp TODO
// 封装 Restore 接口
type RestoreDRComp struct {
	GeneralParam *components.GeneralParam `json:"general"` // 通用参数
	// 恢复参数，会复制给具体的 Restore 实现. 见 ChooseType 方法
	Params       RestoreParam            `json:"extend"`
	restore      Restore                 // 接口
	changeMaster *mysqlutil.ChangeMaster // 存放恢复完的 change master 信息
	// 是否是中断后继续执行
	Resume bool `json:"resume"`
}

// Init TODO
func (r *RestoreDRComp) Init() error {
	return r.restore.Init()
}

// PreCheck TODO
func (r *RestoreDRComp) PreCheck() error {
	if r.Resume && r.Params.WorkID == "" {
		return errors.New("recover恢复执行模式需要 work_id 参数")
	}
	if r.Params.ChangeMaster && components.GetAccountRepl(r.GeneralParam).ReplUser == "" {
		return errors.New("enable change_master should have repl_user given")
	}
	if r.Params.RestoreOpt != nil && r.Params.BackupInfo.backupType == cst.TypeXTRA {
		logger.Warn("xtrabackup recover does not support databases/table filter, recover all")
		// return errors.New("物理备份暂不支持指定库表恢复")
	}
	return r.restore.PreCheck()
}

// Start TODO
func (r *RestoreDRComp) Start() error {
	return r.restore.Start()
}

// WaitDone TODO
func (r *RestoreDRComp) WaitDone() error {
	return r.restore.WaitDone()
}

// PostCheck TODO
func (r *RestoreDRComp) PostCheck() error {
	return r.restore.PostCheck()
}

// OutputCtx TODO
func (r *RestoreDRComp) OutputCtx() error {
	m := r.Params
	logger.Warn("restore-dr comp params: %+v", m)
	if !(m.backupHost == m.SrcInstance.Host && m.backupPort == m.SrcInstance.Port) {
		logger.Warn(
			"backup instance[%s:%d] is not src_instance[%s:%d]",
			m.backupHost, m.backupPort, m.SrcInstance.Host, m.SrcInstance.Port,
		)
	}
	if cm, err := r.restore.ReturnChangeMaster(); err != nil {
		return err
	} else {
		logger.Warn("ReturnChangeMaster %+v. sql: %s", cm, cm.GetSQL())
		r.changeMaster = cm
		return components.PrintOutputCtx(cm)
	}
}

// BuildChangeMaster 生成 change master，给下一个 act 使用
func (r *RestoreDRComp) BuildChangeMaster() *mysql.BuildMSRelationComp {
	cm := r.changeMaster
	if !r.Params.ChangeMaster {
		return nil
	} else if r.Params.ChangeMaster {
		cm.MasterUser = r.GeneralParam.RuntimeAccountParam.ReplUser
		cm.MasterPassword = r.GeneralParam.RuntimeAccountParam.ReplPwd
	}
	comp := mysql.BuildMSRelationComp{
		GeneralParam: r.GeneralParam,
		Params: &mysql.BuildMSRelationParam{
			Host:        r.Params.TgtInstance.Host,
			Port:        r.Params.TgtInstance.Port,
			MasterHost:  cm.MasterHost,
			MasterPort:  cm.MasterPort,
			BinFile:     cm.MasterLogFile,
			BinPosition: cm.MasterLogPos,
		},
	}
	comp.GeneralParam.RuntimeAccountParam.AdminPwd = r.Params.TgtInstance.Pwd
	if r.Params.BackupInfo.backupType == cst.BackupTypePhysical {
		// 物理恢复修复 ADMIN 时
		comp.GeneralParam.RuntimeAccountParam.AdminUser = native.DBUserAdmin
	} else {
		comp.GeneralParam.RuntimeAccountParam.AdminUser = r.Params.TgtInstance.User
	}
	return &comp
}

// ChooseType 选择恢复类型
// 在 Init 之前运行
func (r *RestoreDRComp) ChooseType() error {
	b := &r.Params.BackupInfo
	if err := b.GetBackupMetaFile(dbbackup.BACKUP_INDEX_FILE); err != nil {
		logger.Warn("get index file failed: %s, try to get info file", err.Error())
		// return err
		if err := b.GetBackupMetaFile(dbbackup.MYSQL_INFO_FILE); err != nil {
			return err
		}
	}
	b.backupType = strings.ToLower(b.backupType) // 一律转成小写来判断
	if b.backupType == cst.TypeXTRA {
		xload := XLoad{
			RestoreParam: &r.Params,
		}
		r.restore = &xload
	} else if b.backupType == cst.TypeGZTAB {
		mload := MLoad{
			RestoreParam: &r.Params,
		}
		r.restore = &mload
	} else if b.backupType == cst.BackupTypeLogical || b.backupType == cst.BackupTypePhysical {
		dbloader := DBLoader{
			RestoreParam: &r.Params,
		}
		r.restore = &dbloader
	} else {
		return errors.Errorf("unknown backup_type [%s]", b.backupType)
	}
	logger.Info("choose recover type [%s], indexObj.BackupType=%s", b.backupType, b.indexObj.BackupType)
	return nil
}

// Example TODO
func (r *RestoreDRComp) Example() interface{} {
	comp := RestoreDRComp{
		Params: RestoreParam{
			BackupInfo: BackupInfo{
				WorkDir:   "/data1/dbbak/",
				BackupDir: "/data/dbbak/",
				BackupFiles: map[string][]string{
					"info": {"DBHA_VM-71-150-centos_x_20000_20220831_200425.info"},
				},
			},
			Tools:       *tools.NewToolSetWithPickNoValidate(tools.ToolMload, tools.ToolXLoad, tools.ToolMysqlclient),
			TgtInstance: common.InstanceObjExample,
			SrcInstance: common.InstanceExample,
			WorkID:      "",
			RestoreOpt: &RestoreOpt{
				Databases: []string{"db1"},
				Tables:    []string{"tb1"},
			},
		},
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountReplExample,
			},
		},
	}
	return comp
}

// ExampleOutput TODO
func (r *RestoreDRComp) ExampleOutput() interface{} {
	return &mysqlutil.ChangeMaster{
		MasterHost:     "1.1.1.1",
		MasterPort:     3306,
		MasterUser:     "xx",
		MasterPassword: "yy",
		MasterLogFile:  "binlog.000001",
		MasterLogPos:   4,
		ChangeSQL:      "change master to xxxx",
	}
}
