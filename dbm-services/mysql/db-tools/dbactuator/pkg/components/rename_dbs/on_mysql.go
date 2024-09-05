package rename_dbs

import (
	"bufio"
	"bytes"
	"context"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/rename_dbs/pkg"
	"fmt"
	"os"
	"os/exec"
	"strings"

	_ "github.com/go-sql-driver/mysql"
	"github.com/jmoiron/sqlx"
)

type renameRequest struct {
	FromDatabase string `json:"from_database"`
	ToDatabase   string `json:"to_database"`
}

type OnMySQLParam struct {
	Host           string          `json:"host" validate:"required,ip"`
	PortShardIdMap map[int]int     `json:"port_shard_id_map" validate:"required"` // 如果是TenDBHA, 这个 map 只有一个元素
	HasShard       *bool           `json:"has_shard" validate:"required"`         // 如果是TenDBHA, 这个值为 false
	Requests       []renameRequest `json:"requests" validate:"required"`
}

type OnMySQLComponent struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Param        *OnMySQLParam            `json:"extend"`
	onMySQLCtx
}

type onMySQLCtx struct {
	dbConn          *sqlx.Conn
	dbTablesMap     map[string][]string
	backupCharset   string
	backupDir       string
	uid             string
	dbOtherFilePath string
}

func (c *OnMySQLComponent) Init(uid string) error {
	c.uid = uid
	return nil
}

func (c *OnMySQLComponent) Do() error {
	for port := range c.Param.PortShardIdMap {
		err := c.oneInstance(port)
		if err != nil {
			return err
		}
	}

	return nil
}

func (c *OnMySQLComponent) oneInstance(port int) error {
	err := c.instanceInit(port)
	if err != nil {
		return err
	}
	logger.Info("init instance %d success", port)

	err = c.instanceListTables(port)
	if err != nil {
		return err
	}
	logger.Info("list instance %d tables success", port)

	err = c.instanceCreateToDBs(port)
	if err != nil {
		return err
	}
	logger.Info("create to db on instance %d success", port)

	err = c.instanceRenameOthers(port)
	if err != nil {
		return err
	}
	logger.Info("rename others on instance %d success", port)

	err = c.instanceRenameTables(port)
	if err != nil {
		return err
	}
	logger.Info("rename tables on instance %d success", port)

	err = c.instanceDropFromDBs(port)
	if err != nil {
		return err
	}
	logger.Info("drop from db on instance %d success", port)

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
		return err
	}

	conn, err := db.Connx(context.Background())
	if err != nil {
		return err
	}
	c.dbConn = conn

	return nil
}

func (c *OnMySQLComponent) instanceListTables(port int) error {
	for _, req := range c.Param.Requests {
		fromDB := req.FromDatabase
		if *c.Param.HasShard {
			fromDB = fmt.Sprintf("%s_%d", fromDB, c.Param.PortShardIdMap[port])
		}
		tables, err := pkg.ListDBTables(c.dbConn, fromDB)
		if err != nil {
			return err
		}
		c.dbTablesMap[fromDB] = tables

		logger.Info("list instance %s tables on instance %d: %v", req.FromDatabase, port, tables)
	}
	return nil
}

func (c *OnMySQLComponent) instanceCreateToDBs(port int) error {
	for _, req := range c.Param.Requests {
		toDB := req.ToDatabase
		if *c.Param.HasShard {
			toDB = fmt.Sprintf("%s_%d", toDB, c.Param.PortShardIdMap[port])
		}
		err := pkg.CreateDB(c.dbConn, toDB)
		if err != nil {
			return err
		}
	}
	return nil
}

func (c *OnMySQLComponent) instanceRenameTables(port int) error {
	for _, req := range c.Param.Requests {
		fromDB := req.FromDatabase
		toDB := req.ToDatabase
		if *c.Param.HasShard {
			fromDB = fmt.Sprintf("%s_%d", fromDB, c.Param.PortShardIdMap[port])
			toDB = fmt.Sprintf("%s_%d", toDB, c.Param.PortShardIdMap[port])
		}
		createTriggers, err := pkg.TransDBTables(c.dbConn, fromDB, toDB, c.dbTablesMap[fromDB])
		if err != nil {
			return err
		}

		// 源的触发器已经没了
		// 这里要在目的把触发器恢复
		for _, trigger := range createTriggers {
			_, err = c.dbConn.ExecContext(context.Background(), fmt.Sprintf("USE `%s`", toDB))
			if err != nil {
				logger.Error("change db to %s failed: %v", toDB, err)
				return err
			}
			_, err = c.dbConn.ExecContext(context.Background(), trigger)
			if err != nil {
				logger.Error("create trigger %s in %s failed: %v", trigger, toDB, err)
				return err
			}
			logger.Info("create trigger %s in %s success", trigger, toDB)
		}
	}
	return nil
}

func (c *OnMySQLComponent) instanceRenameOthers(port int) error {
	for _, req := range c.Param.Requests {
		fromDB := req.FromDatabase
		toDB := req.ToDatabase
		if *c.Param.HasShard {
			fromDB = fmt.Sprintf("%s_%d", fromDB, c.Param.PortShardIdMap[port])
			toDB = fmt.Sprintf("%s_%d", toDB, c.Param.PortShardIdMap[port])
		}

		backupFilePath, err := pkg.DumpDBSchema(
			c.Param.Host, port,
			c.GeneralParam.RuntimeAccountParam.AdminUser, c.GeneralParam.RuntimeAccountParam.AdminPwd,
			fromDB, c.uid,
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

		err = pkg.ImportDBSchema(
			c.Param.Host, port,
			c.GeneralParam.RuntimeAccountParam.AdminUser, c.GeneralParam.RuntimeAccountParam.AdminPwd,
			toDB, backupFilePath,
		)
		if err != nil {
			return err
		}

		// 为了幂等重试, 忽略导入的 already exists 错误
		importErrFilePath := fmt.Sprintf("%s.%s.err", backupFilePath, toDB)
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

func (c *OnMySQLComponent) instanceDropFromDBs(port int) error {
	for _, req := range c.Param.Requests {
		fromDB := req.FromDatabase
		toDB := req.ToDatabase
		if *c.Param.HasShard {
			fromDB = fmt.Sprintf("%s_%d", fromDB, c.Param.PortShardIdMap[port])
			toDB = fmt.Sprintf("%s_%d", toDB, c.Param.PortShardIdMap[port])
		}
		err := pkg.DropDB(c.dbConn, fromDB, toDB, false)
		if err != nil {
			return err
		}
	}
	return nil
}

func (c *OnMySQLComponent) Example() interface{} {
	f := false
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
			HasShard: &f,
			Requests: []renameRequest{
				{
					FromDatabase: "old_db1",
					ToDatabase:   "new_db1",
				},
				{
					FromDatabase: "old_db2",
					ToDatabase:   "new_db2",
				},
			},
		},
	}
}
