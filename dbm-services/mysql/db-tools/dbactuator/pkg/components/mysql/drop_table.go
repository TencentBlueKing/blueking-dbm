package mysql

import (
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil/identifiertrans"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
	"golang.org/x/exp/slices"
)

// DropTableComp 删表
type DropTableComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       *DropTableParam          `json:"extend"`
	DropTableContext
}

// DropTableParam 删表参数
/*
Init->PreCheck->FindDatafiles->MakeHardLink->DropTable->FindLegacyHardlink->DeleteHardlink
代替 mysql 的 drop table
当 LimitSpeed == True 时
DeleteHardlink 会按 BWLimitMB 的速度限制删除文件
*/
type DropTableParam struct {
	Database   string   `json:"database" validate:"required"`
	Tables     []string `json:"tables" validate:"required"`
	LimitSpeed bool     `json:"limit_speed"`
	BWLimitMB  int      `json:"bw_limit_mb"`
	Host       string   `json:"host"`
	Port       int      `json:"port"`
}

type tableInfo struct {
	tableName   string
	tableSchema string
	engine      string
	tableIds    []int
	spaces      []int
	datafiles   []string // 带库表路径的文件名，完整路径还需要加上 $datadir
	linkfiles   []string // 带库表路径的文件名，完整路径还需要加上 $datadir
}

type DropTableContext struct {
	db                 *sqlx.DB
	dataDir            string
	tableInfos         map[string]*tableInfo
	innodbSysTables    string
	innodbSysDatafiles string
}

func (d *DropTableComp) Init() (err error) {
	d.tableInfos = make(map[string]*tableInfo)

	instObj := &native.InsObject{
		Host: d.Params.Host,
		Port: d.Params.Port,
		User: d.GeneralParam.RuntimeAccountParam.AdminUser,
		Pwd:  d.GeneralParam.RuntimeAccountParam.AdminPwd,
	}
	dbWorker, err := instObj.Conn()
	if err != nil {
		return err
	}
	d.db = dbWorker.GetSqlxDb()

	err = d.db.Get(&d.dataDir, `SELECT @@datadir`)
	if err != nil {
		return err
	}

	var versionStr string
	err = d.db.Get(&versionStr, `SELECT @@VERSION`)
	if err != nil {
		return err
	}

	mysqlVersion := cmutil.MySQLVersionParse(versionStr)
	if mysqlVersion < 5007000 {
		return fmt.Errorf("%s not support", versionStr)
	}

	if mysqlVersion < 8000000 {
		d.innodbSysTables = `INNODB_SYS_TABLES`
		d.innodbSysDatafiles = `INNODB_SYS_DATAFILES`
	} else {
		d.innodbSysTables = `INNODB_TABLES`
		d.innodbSysDatafiles = `INNODB_DATAFILES`
	}

	q, args, err := sqlx.In(
		`SELECT TABLE_SCHEMA, TABLE_NAME, ENGINE
                     FROM INFORMATION_SCHEMA.TABLES
                     WHERE TABLE_SCHEMA=? AND TABLE_NAME IN (?)`,
		d.Params.Database,
		d.Params.Tables)
	if err != nil {
		return err
	}

	/*
		不存在的表不会写入 tableInfos
		所以整个过程是幂等的
	*/
	var res []struct {
		TableSchema string `db:"TABLE_SCHEMA"`
		TableName   string `db:"TABLE_NAME"`
		Engine      string `db:"ENGINE"`
	}
	err = d.db.Select(&res, d.db.Rebind(q), args...)
	if err != nil {
		return err
	}

	for _, ele := range res {
		innerName := fmt.Sprintf("%s/%s", ele.TableSchema, ele.TableName)
		engine := strings.ToLower(ele.Engine)
		d.tableInfos[innerName] = &tableInfo{
			tableName:   ele.TableName,
			tableSchema: ele.TableSchema,
			engine:      engine,
			tableIds:    []int{},
			spaces:      []int{},
			datafiles:   []string{},
			linkfiles:   []string{},
		}
	}
	return nil
}

func (d *DropTableComp) PreCheck() (err error) {
	for innerName, info := range d.tableInfos {
		switch info.engine {
		case "innodb":
			err = d.preCheckInnodb(innerName, info)
			if err != nil {
				return err
			}
		case "myisam":
			err = d.preCheckMyIsam(innerName, info)
			if err != nil {
				return err
			}
		default:
			return fmt.Errorf("engine %s not support", info.engine)
		}
	}

	return nil
}

func (d *DropTableComp) preCheckInnodb(innerName string, info *tableInfo) (err error) {
	var res []*struct {
		TableId        int    `db:"TABLE_ID"`
		Name           string `db:"NAME"`
		Space          int    `db:"SPACE"`
		SpaceType      string `db:"SPACE_TYPE"`
		IdentifierName string
		/*
			Name 是 filename set 格式，比如库表 `db-a.tb-b` 的 Name 是 db@002da/tb@002db
			IdentifierName 是还原成 `db-a/tb-a`
		*/
	}
	err = d.db.Select(
		&res,
		fmt.Sprintf(
			`SELECT TABLE_ID, NAME, SPACE, SPACE_TYPE FROM INFORMATION_SCHEMA.%s WHERE NAME LIKE ?`,
			d.innodbSysTables),
		fmt.Sprintf("%s/%s%%",
			identifiertrans.TablenameToFilename(info.tableSchema),
			identifiertrans.TablenameToFilename(info.tableName)),
	)
	if err != nil {
		return err
	}

	for _, row := range res {
		s := strings.Split(row.Name, "/")
		d0, err := identifiertrans.FilenameToTableName(s[0])
		if err != nil {
			return err
		}

		var d1 string
		// 分区表的 #p.. 部分要去掉才能合法转换
		partitionPattern := regexp.MustCompile(`^(.*)(#[pP]#.*)$`)
		match := partitionPattern.FindStringSubmatch(s[1])
		if match != nil {
			d1, err = identifiertrans.FilenameToTableName(match[1])
			if err != nil {
				return err
			}
			d1 = fmt.Sprintf("%s%s", d1, match[2])
		} else {
			d1, err = identifiertrans.FilenameToTableName(s[1])
			if err != nil {
				return err
			}
		}

		row.IdentifierName = fmt.Sprintf("%s/%s", d0, d1)
	}

	if len(res) == 1 && res[0].IdentifierName == innerName {
		/*
			普通的 innodb 表
		*/
		row := res[0]
		if row.Space == 0 || strings.ToLower(row.SpaceType) == "system" {
			return fmt.Errorf("%s not in single table space", innerName)
		}

		info.tableIds = append(info.tableIds, row.TableId)
		info.spaces = append(info.spaces, row.Space)
	} else if (len(res) > 1) || (len(res) == 1 && res[0].IdentifierName != innerName) {
		/*
		   innodb 分区表
		*/
		partitionPattern := regexp.MustCompile(fmt.Sprintf(`^%s#[pP]#.*$`, innerName))
		for _, row := range res {
			if partitionPattern.MatchString(row.IdentifierName) {
				info.tableIds = append(info.tableIds, row.TableId)
				info.spaces = append(info.spaces, row.Space)
			}
		}
	} else {
		return fmt.Errorf("%s table detail not found", innerName)
	}

	if len(info.spaces) == 0 || len(info.tableIds) == 0 {
		return fmt.Errorf("%s table detail not found", innerName)
	}

	return nil
}

// 不知道需要检查些什么
func (d *DropTableComp) preCheckMyIsam(innerName string, info *tableInfo) (err error) {
	return nil
}

func (d *DropTableComp) FindDatafiles() (err error) {
	for innerName, info := range d.tableInfos {
		switch info.engine {
		case "innodb":
			err = d.innodbFindDatafiles(innerName, info)
			if err != nil {
				return err
			}
		case "myisam":
			err = d.myisamFindDatafiles(innerName, info)
			if err != nil {
				return err
			}
		default:
			return fmt.Errorf("engine %s not support", info.engine)
		}
	}

	return nil
}

func (d *DropTableComp) innodbFindDatafiles(innerName string, info *tableInfo) (err error) {
	q, args, err := sqlx.In(
		fmt.Sprintf(
			`SELECT SPACE, PATH FROM INFORMATION_SCHEMA.%s WHERE SPACE IN (?)`,
			d.innodbSysDatafiles,
		),
		info.spaces)
	if err != nil {
		return err
	}

	var res []struct {
		Space int    `db:"SPACE"`
		Path  string `db:"PATH"`
	}
	err = d.db.Select(&res, d.db.Rebind(q), args...)
	if err != nil {
		return err
	}

	if len(res) != len(info.spaces) {
		var missingSpaces []int
		for _, space := range info.spaces {
			i := slices.IndexFunc(res, func(s struct {
				Space int    `db:"SPACE"`
				Path  string `db:"PATH"`
			}) bool {
				return s.Space == space
			})
			if i < 0 {
				missingSpaces = append(missingSpaces, space)
			}
		}

		return fmt.Errorf("%v space not found", missingSpaces)
	}

	for _, row := range res {
		info.datafiles = append(info.datafiles, row.Path)
	}

	return nil
}

func (d *DropTableComp) myisamFindDatafiles(innerName string, info *tableInfo) (err error) {
	dbDiskName := identifiertrans.TablenameToFilename(info.tableSchema)
	tableDiskName := identifiertrans.TablenameToFilename(info.tableName)

	partitionPattern := regexp.MustCompile(fmt.Sprintf(`^%s#P#.*$`, tableDiskName))

	err = filepath.WalkDir(
		filepath.Join(d.dataDir, dbDiskName),
		func(path string, de fs.DirEntry, err error) error {
			if err != nil {
				return fs.SkipDir
			}

			/*
				myisam 表有 MYD 和 MYI 两个文件
				这里只遍历 MYD 找到后再去看 MYI，可以避免重复文件
			*/
			if !de.IsDir() && filepath.Ext(de.Name()) == ".MYD" {
				diskfilePrefix := strings.TrimSuffix(de.Name(), ".MYD")

				// 普通表或者分区表
				if diskfilePrefix == tableDiskName || partitionPattern.MatchString(diskfilePrefix) {
					myiDiskfileName := fmt.Sprintf("%s.MYI", diskfilePrefix)

					// 获取 MYI 信息的任何错误都不能容忍
					if _, err := os.Stat(filepath.Join(d.dataDir, dbDiskName, myiDiskfileName)); err != nil {
						return err
					}

					info.datafiles = append(info.datafiles,
						filepath.Join(dbDiskName, de.Name()),
						filepath.Join(dbDiskName, myiDiskfileName))
				}
			}
			return nil
		})

	if err != nil {
		return err
	}

	return nil
}

func (d *DropTableComp) MakeHardlink() (err error) {
	for _, info := range d.tableInfos {

		for _, datafile := range info.datafiles {
			datafilePath := filepath.Join(d.dataDir, datafile)
			linkfile := fmt.Sprintf("%s.__HARDLINK__", datafile)
			linkpath := filepath.Join(d.dataDir, linkfile)

			_, err := os.Stat(linkpath)
			if err != nil {
				if errors.Is(err, os.ErrNotExist) {
					err = os.Link(datafilePath, linkpath)
					if err != nil {
						return err
					}
				} else {
					return err
				}
			}
			info.linkfiles = append(info.linkfiles, linkfile)
		}
	}
	return nil
}

func (d *DropTableComp) DropTable() (err error) {
	for _, info := range d.tableInfos {
		_, err := d.db.Exec(fmt.Sprintf("DROP TABLE IF EXISTS `%s`.`%s`", info.tableSchema, info.tableName))
		if err != nil {
			return err
		}
	}

	return nil
}

func (d *DropTableComp) FindLegacyHardlink() (err error) {
	/*
		在某些未知的情况下可能存在
		表已经没了，但是残留了没删除的硬连接
		所以需要找出来保证幂等
		在 tableInfos 中不存在的表需要扫描
	*/
	for _, tableName := range d.Params.Tables {
		innerName := fmt.Sprintf("%s/%s", d.Params.Database, tableName)
		if _, ok := d.tableInfos[innerName]; ok {
			continue
		}

		// 在 Param.Tables, 但是不在 tableInfos 的表会走到这里
		dbDiskName := identifiertrans.TablenameToFilename(d.Params.Database)
		tableDiskName := identifiertrans.TablenameToFilename(tableName)

		partitionPattern := regexp.MustCompile(fmt.Sprintf(`^%s#P#.*$`, tableDiskName))

		linkFilepaths, err := filepath.Glob(
			filepath.Join(
				d.dataDir,
				dbDiskName,
				fmt.Sprintf(`%s*.*.__HARDLINK__`, tableDiskName)))
		if err != nil {
			return err
		}

		/*
			只有 linkfiles 是重要的
			tableName 和 tableSchema 也就拿来打日志
		*/
		legacyInfo := tableInfo{
			tableName:   tableName,
			tableSchema: d.Params.Database,
			engine:      "",
			tableIds:    nil,
			spaces:      nil,
			datafiles:   []string{},
			linkfiles:   []string{},
		}
		for _, linkFilepath := range linkFilepaths {
			linkFilename := filepath.Base(linkFilepath)

			originalName := strings.TrimSuffix(linkFilename, ".__HARDLINK__")

			ext := filepath.Ext(originalName)
			originalPrefix := strings.TrimSuffix(originalName, ext)

			// 确定是 tableName 的硬连接文件了
			if originalPrefix == tableDiskName || partitionPattern.MatchString(originalPrefix) {

				_, err := os.Stat(
					filepath.Join(
						d.dataDir,
						dbDiskName,
						originalName))

				// 如果是获得文件状态的其他错误
				if err != nil && !errors.Is(err, os.ErrNotExist) {
					return err
				}
				if err == nil {
					/*
						表不存在
						有硬连接文件
						表的数据文件还存在
						这应该是不正常的
					*/
					return fmt.Errorf(
						"table %s.%s: %s original file %s still exists",
						d.Params.Database, tableName, linkFilename, originalName)
				}

				legacyInfo.linkfiles = append(legacyInfo.linkfiles, filepath.Join(dbDiskName, linkFilename))
			}
		}
		d.tableInfos[innerName] = &legacyInfo
	}
	return nil
}

func (d *DropTableComp) DeleteHardlink() (err error) {
	/*
		该做的检查前面都做了
		这里只需要无脑删除文件
	*/
	for _, info := range d.tableInfos {
		for _, filename := range info.linkfiles {
			if d.Params.LimitSpeed {
				done := make(chan int, 1)
				go func(chan int) {
					osutil.PrintFileSizeIncr(
						filepath.Join(d.dataDir, filename),
						1,
						10,
						logger.Info,
						done)
				}(done)

				err = cmutil.TruncateFile(
					filepath.Join(d.dataDir, filename),
					d.Params.BWLimitMB)

				close(done)
			} else {
				err = os.Remove(filepath.Join(d.dataDir, filename))
			}
			if err != nil {
				return err
			}
		}
	}
	return nil
}

func (d *DropTableComp) Example() interface{} {
	comp := DropTableComp{
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountAdminExample,
			}},
		Params: &DropTableParam{
			Database:   "test",
			Tables:     []string{"table1", "table2"},
			LimitSpeed: false,
			BWLimitMB:  0,
			Host:       "x.x.x.x",
			Port:       12345,
		},
	}
	return comp
}
