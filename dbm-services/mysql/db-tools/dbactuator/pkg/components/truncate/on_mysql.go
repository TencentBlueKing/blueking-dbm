package truncate

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"time"

	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	rpkg "dbm-services/mysql/db-tools/dbactuator/pkg/components/rename_dbs/pkg"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/truncate/pkg"

	"dbm-services/common/go-pubpkg/logger"

	_ "github.com/go-sql-driver/mysql" // mysql 驱动

	"github.com/jmoiron/sqlx"
)

type OnMySQLParam struct {
	Host             string      `json:"host" validate:"required,ip"`
	PortShardIdMap   map[int]int `json:"port_shard_id_map" validate:"required"` // 如果是TenDBHA, 这个 map 只有一个元素
	FlowTimeStr      string      `json:"flow_timestr" validate:"required"`
	StageDBHeader    string      `json:"stage_db_header" validate:"required"`
	RollbackDBTail   string      `json:"rollback_db_tail" validate:"required"`
	DBPatterns       []string    `json:"db_patterns" validate:"required"`
	IgnoreDBs        []string    `json:"ignore_dbs" validate:"required"`
	TablePatterns    []string    `json:"table_patterns" validate:"required"`
	IgnoreTables     []string    `json:"ignore_tables" validate:"required"`
	SystemDBs        []string    `json:"system_dbs" validate:"required"`
	HasShard         *bool       `json:"has_shard" validate:"required"` // 如果是TenDBHA, 这个值为 false
	TruncateDataType string      `json:"truncate_data_type" validate:"required" enums:"truncate_table,drop_database,drop_table"`
}

type OnMySQLComponent struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Param        *OnMySQLParam            `json:"extend"`
	onMySQLCtx   `json:"-"`
}

type onMySQLCtx struct {
	dbTablesMap map[string][]string
	dbConn      *sqlx.Conn
	uid         string
}

func (c *OnMySQLComponent) Init(uid string) error {
	c.uid = uid
	return nil
}

func (c *OnMySQLComponent) Truncate() error {
	for port := range c.Param.PortShardIdMap {
		err := c.oneInstance(port)
		if err != nil {
			logger.Error("truncate %s:%d failed: ", c.Param.Host, port, err.Error())
			return err
		}
		logger.Info("truncate %s:%d finished", c.Param.Host, port)
	}

	logger.Info("truncate on %s finished", c.Param.Host)
	return nil
}

func (c *OnMySQLComponent) oneInstance(port int) error {
	err := c.instanceInit(port)
	if err != nil {
		logger.Error("init instance %d truncate failed: %s", port, err.Error())
		return err
	}
	logger.Info("init truncate on instance %d finished", port)

	err = c.instanceGetTarget(port)
	if err != nil {
		logger.Error("get target on instance %d truncate failed: %s", port, err.Error())
		return err
	}
	logger.Info("get target on instance %d finished", port)

	err = c.instanceCreateStageDBs(port)
	if err != nil {
		logger.Error("create stage dbs on instance %d failed: %s", port, err.Error())
		return err
	}
	logger.Info("create stage dbs on instance %d finished", port)

	// 清档不考虑备份非表对象
	//err = c.instanceRenameOthers(port)
	//if err != nil {
	//	logger.Error("rename others to stage on instance %d failed: %s", port, err.Error())
	//	return err
	//}
	//logger.Info("rename others to stage on instance %d finished", port)

	dbTriggers, err := c.instanceRenameTables(port)
	if err != nil {
		logger.Error("rename tables to stage on instance %d failed: %s", port, err.Error())
		return err
	}
	logger.Info("rename tables to stage on instance %d finished", port)

	if c.Param.TruncateDataType == "truncate_table" {
		// 表已经 rename 走了, 需要重建
		err = c.instanceRecreateSourceTables(port)
		if err != nil {
			logger.Error("truncate source table on instance %d failed: %s", port, err.Error())
			return err
		}
		logger.Info("truncate source table on instance %d finished", port)

		for db, triggers := range dbTriggers {
			for _, trigger := range triggers {
				_, err = c.dbConn.ExecContext(context.Background(), fmt.Sprintf("USE `%s`", db))
				if err != nil {
					logger.Error("change db to %s failed: %s", db, err.Error())
					return err
				}
				_, err = c.dbConn.ExecContext(context.Background(), trigger)
				if err != nil {
					logger.Error("create trigger %s in %s on instance %d failed: %s",
						trigger, db, port, err.Error())
					return err
				}
				logger.Info("create trigger %s in %s on instance %d success",
					trigger, db, port)
			}
		}
	} else if c.Param.TruncateDataType == "drop_database" {
		err = c.instanceDropSourceDBs(port)
		if err != nil {
			logger.Error("drop source dbs on instance %d failed: %s", port, err.Error())
			return err
		}
		logger.Info("drop source dbs on instance %d finished", port)
	} else if c.Param.TruncateDataType == "drop_table" {
		//表是rename走的, 所以啥都不用做
	}

	logger.Info("truncate on instance %d finished", c.Param.Host)
	return nil
}

func (c *OnMySQLComponent) instanceInit(port int) error {
	c.onMySQLCtx = onMySQLCtx{}

	c.dbTablesMap = make(map[string][]string)

	db, err := sqlx.Connect(
		"mysql",
		fmt.Sprintf(
			"%s:%s@tcp(%s:%d)/",
			c.GeneralParam.RuntimeAccountParam.AdminUser,
			c.GeneralParam.RuntimeAccountParam.AdminPwd,
			c.Param.Host,
			port,
		),
	)
	if err != nil {
		logger.Error("connect MySQL instance %s:%d failed: %s", c.Param.Host, port, err.Error())
		return err
	}
	logger.Info("connecting mysql db %s:%d success", c.Param.Host, port)
	conn, err := db.Connx(context.Background())
	if err != nil {
		logger.Error("get connection from mysql db failed: %s", err.Error())
		return err
	}
	c.dbConn = conn

	logger.Info("init truncate on %s:%d success", c.Param.Host, port)
	return nil
}

func (c *OnMySQLComponent) instanceGetTarget(port int) error {
	target, err := pkg.GetTarget(
		c.dbConn,
		c.Param.DBPatterns, c.Param.IgnoreDBs, c.Param.TablePatterns, c.Param.IgnoreTables, c.Param.SystemDBs,
		c.Param.StageDBHeader, c.Param.RollbackDBTail,
		c.Param.PortShardIdMap[port], *c.Param.HasShard,
	)
	if err != nil {
		logger.Error("get instance %d db-tables failed: %s", port, err.Error())
		return err
	}
	logger.Info("get instance %d db-tables success: %v", port, target)
	if target == nil || len(target) == 0 {
		err = fmt.Errorf("got empty db-tables target")
		logger.Error("get instance %d db-tables failed: %s", port, err.Error())
		return err
	}
	c.dbTablesMap = target
	return nil
}

func (c *OnMySQLComponent) instanceCreateStageDBs(port int) error {
	for db := range c.dbTablesMap {
		stageDBName := generateStageDBName(c.Param.StageDBHeader, c.Param.FlowTimeStr, db)
		err := rpkg.CreateDB(c.dbConn, stageDBName) //c.instanceCreateStageDB(port, stageDBName)
		if err != nil {
			logger.Error("create stage db %s on instance %d failed: %s", stageDBName, port, err.Error())
			return err
		}
		logger.Info("create stage db %s on instance %d success", stageDBName, port)
	}
	logger.Info("create stage dbs on instance %d success", port)
	return nil
}

func (c *OnMySQLComponent) instanceRenameTables(port int) (map[string][]string, error) {
	res := map[string][]string{}
	for db := range c.dbTablesMap {
		stageDBName := generateStageDBName(c.Param.StageDBHeader, c.Param.FlowTimeStr, db)
		triggers, err := rpkg.TransDBTables(c.dbConn, db, stageDBName, c.dbTablesMap[db])
		if err != nil {
			logger.Error("rename tables to stage on instance %d failed: %s", port, err.Error())
			return nil, err
		}
		res[db] = triggers
	}
	logger.Info("rename table on instance %d success", port)
	return res, nil
}

func (c *OnMySQLComponent) instanceRenameOthers(port int) error {
	for db := range c.dbTablesMap {
		stageDBName := generateStageDBName(c.Param.StageDBHeader, c.Param.FlowTimeStr, db)

		backupFilePath, err := rpkg.DumpDBSchema(
			c.Param.Host, port,
			c.GeneralParam.RuntimeAccountParam.AdminUser, c.GeneralParam.RuntimeAccountParam.AdminPwd,
			db, c.uid,
			false,
		)
		if err != nil {
			return err
		}

		// dump 出来的 sql 文件有 USE ${DB}, 需要删除
		sedCmd := exec.Command("sed", "-i", `/^USE.*;/d`, backupFilePath)
		var stderr bytes.Buffer
		sedCmd.Stderr = &stderr
		err = sedCmd.Run()
		if err != nil {
			logger.Error("sed backup file %s failed: %s: %s", backupFilePath, err, stderr.String())
			return err
		}
		logger.Info("sed backup file %s success", backupFilePath)

		err = rpkg.ImportDBSchema(
			c.Param.Host, port,
			c.GeneralParam.RuntimeAccountParam.AdminUser, c.GeneralParam.RuntimeAccountParam.AdminPwd,
			stageDBName, backupFilePath,
		)
		if err != nil {
			return err
		}

		// 为了幂等重试, 忽略导入的 already exists 错误
		importErrFilePath := fmt.Sprintf("%s.%s.err", backupFilePath, stageDBName)
		ief, err := os.Open(importErrFilePath)
		if err != nil {
			return err
		}
		logger.Info("open %s success", importErrFilePath)

		var importErrors []string
		scanner := bufio.NewScanner(ief)
		for scanner.Scan() {
			line := scanner.Text()
			if !strings.HasPrefix(line, "ERROR 1050") /*table view*/ &&
				!strings.HasPrefix(line, "ERROR 1304") /*procedure function*/ &&
				!strings.HasPrefix(line, "ERROR 1537") /*event*/ &&
				!strings.HasPrefix(line, "ERROR 1359") /*trigger*/ &&
				!strings.HasPrefix(line, "ERROR 1840") {
				importErrors = append(importErrors, line)
			}
		}
		if err := scanner.Err(); err != nil {
			return err
		}

		if len(importErrors) > 0 {
			errStr := strings.Join(importErrors, "\n")
			return fmt.Errorf(errStr)
		}
	}
	return nil
}

func (c *OnMySQLComponent) instanceDropSourceDBs(port int) error {
	for db := range c.dbTablesMap {
		stageDBName := generateStageDBName(c.Param.StageDBHeader, c.Param.FlowTimeStr, db)
		err := rpkg.DropDB(c.dbConn, db, stageDBName, true)
		if err != nil {
			logger.Error("drop source db %s on instance %d failed: %s", stageDBName, port, err.Error())
			return err
		}
	}
	logger.Info("drop db on instance %d success", port)
	return nil
}

func (c *OnMySQLComponent) instanceRecreateSourceTables(port int) error {
	for db := range c.dbTablesMap {
		stageDBName := generateStageDBName(c.Param.StageDBHeader, c.Param.FlowTimeStr, db)
		stageTables, err := rpkg.ListDBTables(c.dbConn, stageDBName)
		if err != nil {
			logger.Error("list stage db tables on instance %d from %s failed: %s", port, stageDBName, err.Error())
			return err
		}

		// 这里改成从 stage 库拿表列表, 在重试的时候才能幂等
		for _, table := range stageTables {
			err := c.instanceRecreateSourceTable(port, db, stageDBName, table)
			if err != nil {
				logger.Error(
					"re create table %s from %s on instance %d failed: %s",
					table, db, port, err.Error(),
				)
				return err
			}
			logger.Info(
				"re create table %s from %s on instance %d success", table, db, port,
			)
		}
	}
	logger.Info("re create table on instance %d success", port)
	return nil
}

func (c *OnMySQLComponent) instanceRecreateSourceTable(port int, dbName, stageDBName, tableName string) error {
	//yes, err := rpkg.IsTableExistsIn(c.dbConn, tableName, stageDBName)
	//if err != nil {
	//	logger.Error("check table %s exists in %s failed: %s", tableName, stageDBName, err.Error())
	//	return err
	//}
	//
	//if !yes {
	//	err := fmt.Errorf("%s.%s not found", stageDBName, tableName)
	//	logger.Error("re create source table on instance %d failed: ", port, err.Error())
	//	return err
	//}
	//logger.Info("source table found in stage db on instance %d, try to truncate", port)
	defer func() {
		c.flushTable(dbName, tableName)
		c.flushTable(stageDBName, tableName)
	}()

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	_, err := c.dbConn.ExecContext(
		ctx,
		fmt.Sprintf(
			"CREATE TABLE IF NOT EXISTS `%s`.`%s` LIKE `%s`.`%s`",
			dbName, tableName, stageDBName, tableName,
		),
	)
	if err != nil {
		logger.Error(
			"re create source table %s.%s on instance %d failed: ",
			dbName, tableName, port, err.Error(),
		)
		return err
	}

	return nil
}

func (c *OnMySQLComponent) flushTable(dbName, tableName string) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	_, err := c.dbConn.ExecContext(
		ctx,
		fmt.Sprintf("FLUSH TABLE `%s`.`%s`", dbName, tableName),
	)
	if err != nil {
		logger.Error("flush table %s.%s  failed: %s", dbName, tableName, err.Error())
	}
}

func (c *OnMySQLComponent) GenerateDropStageSQL() error {
	var dropSQLs []string
	for dbName := range c.dbTablesMap {
		stageDBName := generateStageDBName(c.Param.StageDBHeader, c.Param.FlowTimeStr, dbName)
		dropSQL := fmt.Sprintf("DROP DATABASE IF EXISTS `%s`", stageDBName)
		dropSQLs = append(dropSQLs, dropSQL)
	}

	b, err := json.Marshal(dropSQLs)
	if err != nil {
		return err
	}

	logger.Info(string(b))
	fmt.Println(components.WrapperOutputString(strings.TrimSpace(string(b))))
	return nil
}

func (c *OnMySQLComponent) Example() interface{} {
	hs := false
	return OnMySQLComponent{
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountAdminExample,
			},
		},
		Param: &OnMySQLParam{
			Host: "127.0.0.1",
			PortShardIdMap: map[int]int{
				20000: 0,
				20001: 1,
			},
			FlowTimeStr:      "19700102040506",
			StageDBHeader:    "stage_truncate",
			RollbackDBTail:   "rollback",
			DBPatterns:       []string{"db%"},
			IgnoreDBs:        []string{"db1"},
			TablePatterns:    []string{"*"},
			IgnoreTables:     []string{"*"},
			SystemDBs:        []string{"mysql", "test"},
			HasShard:         &hs,
			TruncateDataType: "truncate_table",
		},
	}
}
