// Package mysql TODO
//
//		package
//	 ignore_dbnames: 变更时候需要忽略的dbname,支持正则匹配 [db1,db2,db3%]
//		dbnames: 变更时候 需要指定的变更的库
package mysql

import (
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/computil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
	"path"
	"regexp"
	"strings"
)

// ExcuteSQLFileComp TODO
type ExcuteSQLFileComp struct {
	GeneralParam            *components.GeneralParam `json:"general"`
	Params                  *ExcuteSQLFileParam      `json:"extend"`
	ExcuteSQLFileRunTimeCtx `json:"-"`
}

// ExcuteSQLFileParam TODO
type ExcuteSQLFileParam struct {
	Host          string             `json:"host"  validate:"required,ip"`             // 当前实例的主机地址
	Ports         []int              `json:"ports"`                                    // 被监控机器的上所有需要监控的端口
	CharSet       string             `json:"charset" validate:"required,checkCharset"` // 字符集参数
	FilePath      string             `json:"file_path"`                                // 文件路径
	ExcuteObjects []ExcuteSQLFileObj `json:"execute_objects"`
	Force         bool               `json:"force"`     // 是否强制执行 执行出错后，是否继续往下执行
	IsSpider      bool               `json:"is_spider"` // 是否是spider集群
}

// ExcuteSQLFileObj 单个文件的执行对象
// 一次可以多个文件操作不同的数据库
type ExcuteSQLFileObj struct {
	SQLFile       string   `json:"sql_file"`       // 变更文件名称
	IgnoreDbNames []string `json:"ignore_dbnames"` // 忽略的,需要排除变更的dbName,支持模糊匹配
	DbNames       []string `json:"dbnames"`        // 需要变更的DBNames,支持模糊匹配
}

// ExcuteSQLFileRunTimeCtx 运行时上下文
type ExcuteSQLFileRunTimeCtx struct {
	ports                []int
	dbConns              map[Port]*native.DbWorker
	vermap               map[Port]string // 当前实例的数据版本
	charsetmap           map[Port]string // 当前实例的字符集
	socketmap            map[Port]string // 当前实例的socket value
	taskdir              string
	RegularIgnoreDbNames []string
	RegularDbNames       []string
}

// Example TODO
func (e *ExcuteSQLFileComp) Example() interface{} {
	return ExcuteSQLFileComp{
		GeneralParam: &components.GeneralParam{},
		Params: &ExcuteSQLFileParam{
			Host:     "127.0.0.1",
			Ports:    []int{3306, 3307},
			CharSet:  "utf8",
			FilePath: "/data/workspace",
			ExcuteObjects: []ExcuteSQLFileObj{
				{
					SQLFile:       "111.sql",
					IgnoreDbNames: []string{"a%"},
					DbNames:       []string{"db1", "db2"},
				},
			},
			Force:    false,
			IsSpider: false,
		},
	}
}

// Init TODO
func (e *ExcuteSQLFileComp) Init() (err error) {
	e.ports = make([]int, len(e.Params.Ports))
	e.dbConns = make(map[int]*native.DbWorker)
	e.vermap = make(map[int]string)
	e.socketmap = make(map[int]string)
	e.charsetmap = make(map[int]string)

	copy(e.ports, e.Params.Ports)
	for _, port := range e.ports {
		var ver, charset, socket string
		dbConn, err := native.InsObject{
			Host: e.Params.Host,
			Port: port,
			User: e.GeneralParam.RuntimeAccountParam.AdminUser,
			Pwd:  e.GeneralParam.RuntimeAccountParam.AdminPwd,
		}.Conn()
		if err != nil {
			logger.Error("Connect %d failed:%s", port, err.Error())
			return err
		}
		if ver, err = dbConn.SelectVersion(); err != nil {
			logger.Error("获取实例版本失败:%s", err.Error())
			return err
		}

		charset = e.Params.CharSet
		if e.Params.CharSet == "default" {
			if charset, err = dbConn.ShowServerCharset(); err != nil {
				logger.Error("获取实例的字符集失败：%s", err.Error())
				return err
			}
		}
		if socket, err = dbConn.ShowSocket(); err != nil {
			logger.Error("获取socket value 失败:%s", err.Error())
			return err
		}
		if !cmutil.FileExists(socket) {
			socket = ""
		}

		e.dbConns[port] = dbConn
		e.vermap[port] = ver
		e.socketmap[port] = socket
		e.charsetmap[port] = charset
		e.taskdir = strings.TrimSpace(e.Params.FilePath)
		if e.taskdir == "" {
			e.taskdir = cst.BK_PKG_INSTALL_PATH
		}
	}
	return nil
}

// MvFile2TaskDir  将gse的文件move 到taskdir
//
//	@receiver e
//	@receiver err
// func (e *ExcuteSQLFileComp) MvFile2TaskDir(taskdir string) (err error) {
// 	e.taskdir = path.Join(cst.BK_PKG_INSTALL_PATH, taskdir)
// 	if err = os.MkdirAll(e.taskdir, os.ModePerm); err != nil {
// 		logger.Error("初始化任务目录失败%s:%s", e.taskdir, err.Error())
// 		return
// 	}
// 	for _, o := range e.Params.ExcuteObjects {
// 		if err = os.Rename(path.Join(cst.BK_PKG_INSTALL_PATH, o.SQLFile), path.Join(e.taskdir, o.SQLFile)); err != nil {
// 			logger.Error("将SQL文件%s移动到%s 错误:%s", o.SQLFile, e.taskdir, err.Error())
// 			return
// 		}
// 	}
// 	return err
// }

// Excute TODO
func (e *ExcuteSQLFileComp) Excute() (err error) {
	for _, port := range e.ports {
		if err = e.excuteOne(port); err != nil {
			logger.Error("execute at %d failed: %s", port, err.Error())
			return err
		}
	}
	return nil
}

// OpenDdlExecuteByCtl TODO
// sed 之前考虑是否需要保留源文件
// 此方法仅用于spider集群变更
func (e *ExcuteSQLFileComp) OpenDdlExecuteByCtl() (err error) {
	for _, f := range e.Params.ExcuteObjects {
		stdout, err := osutil.StandardShellCommand(
			false,
			fmt.Sprintf(`sed -i '1 i\/*!50600 SET ddl_execute_by_ctl=1*/;' %s`, path.Join(e.taskdir, f.SQLFile)),
		)
		if err != nil {
			logger.Error("sed insert ddl_execute_by_ctl failed %s,stdout:%s", err.Error(), stdout)
			return err
		}
		logger.Info("sed at %s,stdout:%s", f.SQLFile, stdout)
	}
	return
}

// excuteOne 执行导入SQL文件
//
//	@receiver e
//	@return err
func (e *ExcuteSQLFileComp) excuteOne(port int) (err error) {
	alldbs, err := e.dbConns[port].ShowDatabases()
	if err != nil {
		logger.Error("获取实例db list失败:%s", err.Error())
		return err
	}
	dbsExcluesysdbs := util.FilterOutStringSlice(alldbs, computil.GetGcsSystemDatabasesIgnoreTest(e.vermap[port]))
	for _, f := range e.Params.ExcuteObjects {
		var realexcutedbs []string
		// 获得目标库 因为是通配符 所以需要获取完整名称
		intentionDbs, err := e.match(dbsExcluesysdbs, f.parseDbParamRe())
		if err != nil {
			return err
		}
		// 获得忽略库
		ignoreDbs, err := e.match(dbsExcluesysdbs, f.parseIgnoreDbParamRe())
		if err != nil {
			return err
		}
		// 获取最终需要执行的库
		realexcutedbs = util.FilterOutStringSlice(intentionDbs, ignoreDbs)
		if len(realexcutedbs) <= 0 {
			return fmt.Errorf("没有适配到任何db")
		}
		logger.Info("will real excute on %v", realexcutedbs)
		err = mysqlutil.ExecuteSqlAtLocal{
			IsForce:          e.Params.Force,
			Charset:          e.charsetmap[port],
			NeedShowWarnings: false,
			Host:             e.Params.Host,
			Port:             port,
			Socket:           e.socketmap[port],
			WorkDir:          e.taskdir,
			User:             e.GeneralParam.RuntimeAccountParam.AdminUser,
			Password:         e.GeneralParam.RuntimeAccountParam.AdminPwd,
		}.ExcuteSqlByMySQLClient(f.SQLFile, realexcutedbs)
		if err != nil {
			logger.Error("执行%s文件失败", f.SQLFile)
			return err
		}
	}
	return err
}

// match 根据show databases 返回的实际db,匹配出dbname
//
//	@receiver e
//	@receiver regularDbNames
//	@return matched
func (e *ExcuteSQLFileComp) match(dbsExculeSysdb, regularDbNames []string) (matched []string, err error) {
	for _, regexpStr := range regularDbNames {
		re, err := regexp.Compile(regexpStr)
		if err != nil {
			logger.Error(" regexp.Compile(%s) failed:%s", regexpStr, err.Error())
			return nil, err
		}
		for _, db := range dbsExculeSysdb {
			if re.MatchString(db) {
				matched = append(matched, db)
			}
		}
	}
	return
}

// parseDbParamRe TODO
// ConvertDbParamToRegular 解析DbNames参数成正则参数
//
//	@receiver e
func (e *ExcuteSQLFileObj) parseDbParamRe() (s []string) {
	return changeToMatch(e.DbNames)
}

// parseIgnoreDbParamRe  解析IgnoreDbNames参数成正则参数
//
//	@receiver e
//	@return []string
func (e *ExcuteSQLFileObj) parseIgnoreDbParamRe() (s []string) {
	return changeToMatch(e.IgnoreDbNames)
}

// changeToMatch 将输入的参数转成正则匹配的格式
//
//	@receiver input
//	@return []string
func changeToMatch(input []string) []string {
	var result []string
	for _, str := range input {
		str = strings.Replace(str, "?", ".", -1)
		str = strings.Replace(str, "%", ".*", -1)
		str = `^` + str + `$`
		result = append(result, str)
	}
	return result
}
