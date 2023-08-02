package dbloader

import (
	"fmt"
	"os"
	"path/filepath"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/computil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/pkg/errors"
)

// Xtrabackup TODO
type Xtrabackup struct {
	TgtInstance   native.InsObject `json:"tgt_instance"`
	SrcBackupHost string           `json:"src_backup_host" validate:"required"`
	QpressTool    string           `json:"qpress_tool" validate:"required,file"`

	LoaderDir string // 备份解压后的目录，${taskDir}/backupBaseName/
	// 在 PostRun 中会择机初始化
	dbWorker *native.DbWorker // TgtInstance
	// 在 PreRun 时初始化，本地实例的配置文件
	myCnf *util.CnfFile
}

// PreRun 以下所有步骤必须可重试
func (x *Xtrabackup) PreRun() error {
	logger.Info("run xtrabackup preRun")

	// 关闭本地mysql
	inst := x.TgtInstance

	logger.Info("stop local mysqld")
	if err := computil.ShutdownMySQLBySocket2(inst.User, inst.Pwd, inst.Socket); err != nil {
		logger.Error("shutdown mysqld failed %s", inst.Socket)
		return err
	}

	logger.Info("decompress xtrabackup meta files")
	if err := x.DecompressMetaFile(); err != nil {
		return err
	}

	logger.Info("clean local mysqld data dirs")
	// 清理本地目录
	if err := x.cleanXtraEnv(); err != nil {
		return err
	}

	logger.Info("replace local mysqld my.cnf variables")
	// 调整my.cnf文件
	if err := x.doReplaceCnf(); err != nil {
		return err
	}
	return nil
}

// PostRun TODO
func (x *Xtrabackup) PostRun() (err error) {
	logger.Info("change datadir owner user and group")
	// 调整目录属主
	if err = x.changeDirOwner(); err != nil {
		return err
	}

	logger.Info("start local mysqld with skip-grant-tables")
	// 启动mysql-修复权限
	startParam := computil.StartMySQLParam{
		MediaDir:        cst.MysqldInstallPath,
		MyCnfName:       x.myCnf.FileName,
		MySQLUser:       x.TgtInstance.User, // 用ADMIN
		MySQLPwd:        x.TgtInstance.Pwd,
		Socket:          x.TgtInstance.Socket,
		SkipGrantTables: true, // 以 skip-grant-tables 启动来修复 ADMIN
	}
	if _, err = startParam.StartMysqlInstance(); err != nil {
		return errors.WithMessage(err, "start mysqld after xtrabackup")
	}
	if x.dbWorker, err = x.TgtInstance.Conn(); err != nil {
		return err
	}

	logger.Info("repair ADMIN user host and password")
	// 物理备份，ADMIN密码与 backup instance(cluster?) 相同，修复成
	// 修复ADMIN用户
	if err := x.RepairUserAdmin(native.DBUserAdmin, x.TgtInstance.Pwd); err != nil {
		return err
	}

	logger.Info("repair other user privileges")
	// 修复权限
	if err := x.RepairPrivileges(); err != nil {
		return err
	}
	x.dbWorker.Stop()

	logger.Info("restart local mysqld")
	// 重启mysql（去掉 skip-grant-tables）
	startParam.SkipGrantTables = false
	if _, err := startParam.RestartMysqlInstance(); err != nil {
		return err
	}
	// reconnect
	if x.dbWorker, err = x.TgtInstance.Conn(); err != nil {
		return err
	} else {
		defer x.dbWorker.Stop()
	}

	logger.Info("repair myisam tables")
	// 修复MyIsam表
	if err := x.RepairAndTruncateMyIsamTables(); err != nil {
		return err
	}
	return nil
}

func (x *Xtrabackup) cleanXtraEnv() error {
	dirs := []string{
		"datadir",
		"innodb_log_group_home_dir",
		"innodb_data_home_dir",
		"relay-log",
		"log_bin",
		"tmpdir",
	}
	return x.CleanEnv(dirs)
}

// doReplaceCnf godoc
// todo 考虑使用 mycnf-change 模块来修改
// mysql 8.0.30 之后 redo_log 变成 innodb_redo_log_capacity 来控制
func (x *Xtrabackup) doReplaceCnf() error {
	items := []string{
		"innodb_data_file_path",
		"innodb_log_files_in_group",
		"innodb_log_file_size",
		"innodb_page_size",
		"tokudb_cache_size",
		"lower_case_table_names",

		// mysql 8.0 xtrabackup
		"innodb_checksum_algorithm",
		"innodb_log_checksums",
		"innodb_undo_directory",
		"innodb_undo_tablespaces",
		"innodb_redo_log_encrypt",
		"innodb_undo_log_encrypt",
		//"master_key_id",
	}
	return x.ReplaceMycnf(items)
}

func (x *Xtrabackup) importData() error {
	return nil
}

func (x *Xtrabackup) changeDirOwner() error {
	dirs := []string{
		"datadir",
		"innodb_log_group_home_dir",
		"innodb_data_home_dir",
		"relay_log",
		"tmpdir",
		"log_bin",
		"slow_query_log_file",
	}
	return x.ChangeDirOwner(dirs)
}

// DecompressMetaFile decompress .pq file and output same file name without suffix
// ex: /home/mysql/dbbackup/xtrabackup/qpress -do xtrabackup_info.qp > xtrabackup_info
func (x *Xtrabackup) DecompressMetaFile() error {
	files := []string{
		"xtrabackup_timestamp_info",
		"backup-my.cnf",
		"xtrabackup_binlog_info",
		"xtrabackup_info",
		"xtrabackup_slave_info",
		"xtrabackup_galera_info",
	}

	for _, file := range files {
		compressedFile := filepath.Join(x.LoaderDir, file+".qp")
		if _, err := os.Stat(compressedFile); os.IsNotExist(err) {
			continue
		}
		script := fmt.Sprintf(`cd %s && %s -do %s.qp > %s`, x.LoaderDir, x.QpressTool, file, file)
		stdErr, err := cmutil.ExecShellCommand(false, script)
		if err != nil {
			return errors.Wrapf(err, "decompress file %s failed, error:%s, stderr:%s",
				compressedFile, err.Error(), stdErr)
		}
	}
	return nil
}
