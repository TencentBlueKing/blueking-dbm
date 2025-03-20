package backupexe

import (
	"fmt"
	"strings"

	"dbm-services/common/go-pubpkg/validate"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

// Loader interface
type Loader interface {
	initConfig(indexContent *dbareport.IndexContent) error
	Execute() error
}

// BuildLoader TODO
func BuildLoader(cnf *config.BackupConfig, backupType string, backupTool string, storageEngine string) (loader Loader, err error) {

	if strings.ToLower(backupType) == cst.BackupLogical {
		if backupTool == cst.ToolMysqldump {
			// mysqldump 共用 LogicalLoad 参数
			if err := validate.GoValidateStructTag(cnf.LogicalLoad, "ini"); err != nil {
				return nil, err
			}
			if err := validate.GoValidateStructTag(cnf.LogicalLoadMysqldump, "ini"); err != nil {
				return nil, err
			}
			loader = &LogicalLoaderMysqldump{
				cnf: &config.LogicalLoaderConfig{
					LogicalLoad:          cnf.LogicalLoad,
					LogicalLoadMysqldump: cnf.LogicalLoadMysqldump,
				},
			}
			// validate
		} else {
			if err := validate.GoValidateStructTag(cnf.LogicalLoad, "ini"); err != nil {
				return nil, err
			}
			loader = &LogicalLoader{
				cnf: &cnf.LogicalLoad,
			}
		}
		if err := cnf.LogicalLoad.ValidateFilter(); err != nil {
			return nil, err
		}
	} else if strings.ToLower(backupType) == cst.BackupPhysical {
		if err := validate.GoValidateStructTag(cnf.PhysicalLoad, "ini"); err != nil {
			return nil, err
		}
		if cst.StorageEngineRocksdb == storageEngine {
			loader = &PhysicalRocksdbLoader{
				cfg: &config.PhysicalLoaderConfig{
					Public:       cnf.Public,
					PhysicalLoad: cnf.PhysicalLoad,
				},
			}
		} else if storageEngine == cst.StorageEngineTokudb || backupTool == "tokudb_back.pl" {
			loader = &PhysicalTokudbLoader{
				cnf: &config.PhysicalLoaderConfig{
					Public:       cnf.Public,
					PhysicalLoad: cnf.PhysicalLoad,
				},
			}
		} else {
			loader = &PhysicalLoader{
				cnf: &cnf.PhysicalLoad,
			}
			// validate
		}
	} else {
		logger.Log.Error(fmt.Sprintf("Unknown BackupType: %s", backupType))
		err := fmt.Errorf("unknown BackupType: %s", backupType)
		return nil, err
	}

	return loader, nil
}
