package restore

import (
	"strings"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/dbbackup"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/restore/dbbackup_loader"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
)

// RestoreDRAfterParam restore-dr-after 子命令的参数
// 因为这一步跟上一步的 restore-dr 是分离的，taskDir/targetDir/untarDir 是在 restore-dr 里面确定的，现在没法传递到这一步
// 所以关于涉及到这 3 个目录的操作都在 restore-dr 里完成，不在 restore-dr-after 这里
type RestoreDRAfterParam struct {
	// 恢复本地的目标实例
	TgtInstance native.InsObject `json:"tgt_instance" validate:"required"`

	// BackupDir 备份文件所在本地目录
	BackupDir string `json:"backup_dir" validate:"required"`
	// BackupFiles 备份文件名列表，key 是 info|full|priv|index
	BackupFiles   map[string][]string `json:"backup_files"`
	RecoverGrants bool                `json:"recover_grants"`
}

// RestoreDRAfterComp restore-dr-after 子命令组件
// 独立执行恢复后的 PostLoad 操作（物理备份执行 repairAndStart，逻辑备份为空操作）
type RestoreDRAfterComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       RestoreDRAfterParam      `json:"extend"`

	// 从 index 文件解析出来的信息
	backupInfo *BackupInfo
	myCnf      *util.CnfFile
	// dbLoader 通过接口调用 PostLoad
	dbLoader dbbackup_loader.DBBackupLoader
}

// Init 初始化：解析 index 文件，加载 my.cnf，选择 loader
func (r *RestoreDRAfterComp) Init() error {
	// 解析 index 文件，获取 BackupHost、StorageEngine、MysqlVersion 等信息
	r.backupInfo = &BackupInfo{
		BackupDir:   r.Params.BackupDir,
		BackupFiles: r.Params.BackupFiles,
	}
	if err := r.backupInfo.GetBackupMetaFile(dbbackup.BACKUP_INDEX_FILE, false); err != nil {
		return errors.WithMessage(err, "解析 index 文件失败")
	}

	// 加载本地实例的 my.cnf
	cnfFileName := util.GetMyCnfFileName(r.Params.TgtInstance.Port)
	cnfFile := &util.CnfFile{FileName: cnfFileName}
	if err := cnfFile.Load(); err != nil {
		return errors.WithMessagef(err, "加载 my.cnf 失败: %s", cnfFileName)
	}
	r.myCnf = cnfFile

	// 补充 socket
	if r.Params.TgtInstance.Socket == "" {
		sock := r.myCnf.GetMyCnfByKeyWithDefault(util.MysqldSec, "socket", "/tmp/mysql.sock")
		r.Params.TgtInstance.Socket = sock
	}

	// 根据 backupType 选择 loader
	if err := r.chooseLoader(); err != nil {
		return err
	}
	return nil
}

// chooseLoader 根据备份类型选择 PhysicalLoader 或 LogicalLoader
func (r *RestoreDRAfterComp) chooseLoader() error {
	indexObj := r.backupInfo.indexObj
	backupType := strings.ToLower(r.backupInfo.backupType)

	loaderUtil := &dbbackup_loader.LoaderUtil{
		TgtInstance:   r.Params.TgtInstance,
		IndexObj:      indexObj,
		BackupDir:     r.Params.BackupDir,
		RecoverGrants: r.Params.RecoverGrants,
	}
	if backupType == cst.BackupTypePhysical {
		xtra := &dbbackup_loader.Xtrabackup{
			TgtInstance:   r.Params.TgtInstance,
			SrcBackupHost: indexObj.BackupHost,
			StorageType:   strings.ToLower(indexObj.StorageEngine),
			MySQLVersion:  indexObj.MysqlVersion,
		}
		xtra.SetMyCnf(r.myCnf)
		r.dbLoader = &dbbackup_loader.PhysicalLoader{
			Xtrabackup: xtra,
			LoaderUtil: loaderUtil,
		}
	} else if backupType == cst.BackupTypeLogical {
		r.dbLoader = &dbbackup_loader.LogicalLoader{
			LoaderUtil: loaderUtil,
		}
	} else {
		return errors.Errorf("unknown backupType: %s", backupType)
	}
	logger.Info("restore-dr-after: chose loader for backup_type=%s", backupType)
	return nil
}

// Start 通过 DBBackupLoader 接口执行 PostLoad
func (r *RestoreDRAfterComp) Start() error {
	logger.Info("restore-dr-after: start PostLoad for port %d", r.Params.TgtInstance.Port)
	if err := r.dbLoader.PostLoad(); err != nil {
		return errors.WithMessage(err, "PostLoad 失败")
	}
	return nil
}

// Example 示例
func (r *RestoreDRAfterComp) Example() interface{} {
	return RestoreDRAfterComp{
		Params: RestoreDRAfterParam{
			TgtInstance: native.InsObject{
				Host: "x.x.x.x",
				Port: 20000,
				User: "xx",
				Pwd:  "yy",
			},
			BackupDir: "/data/dbbak/xxxx/3306/",
			BackupFiles: map[string][]string{
				"index": {"10_123_x.x.x.x_3306_20241030030300_physical.index"},
			},
		},
		GeneralParam: &components.GeneralParam{},
	}
}
