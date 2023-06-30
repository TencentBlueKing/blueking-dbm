package mysql

import (
	"encoding/json"
	"fmt"
	"net/url"
	"path"
	"reflect"
	"regexp"
	"strings"

	"dbm-services/common/go-pubpkg/bkrepo"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/computil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

// SemanticDumpSchemaComp TODO
type SemanticDumpSchemaComp struct {
	GeneralParam         *components.GeneralParam `json:"general"`
	Params               DumpSchemaParam          `json:"extend"`
	DumpSchemaRunTimeCtx `json:"-"`
}

// DumpSchemaParam TODO
type DumpSchemaParam struct {
	Host           string     `json:"host"  validate:"required,ip"`                // 当前实例的主机地址
	Port           int        `json:"port"  validate:"required,lt=65536,gte=3306"` // 当前实例的端口
	CharSet        string     `json:"charset" validate:"required,checkCharset"`    // 字符集参数
	BackupFileName string     `json:"backup_file_name"`
	BackupDir      string     `json:"backup_dir"`
	BkCloudId      int        `json:"bk_cloud_id"`    // 所在的云区域
	DBCloudToken   string     `json:"db_cloud_token"` // 云区域token
	FileServer     FileServer `json:"fileserver"`
}

// FileServer TODO
type FileServer struct {
	URL        string `json:"url"`         // 制品库地址
	Bucket     string `json:"bucket"`      // 目标bucket
	Password   string `json:"password"`    // 制品库 password
	Username   string `json:"username"`    // 制品库 username
	Project    string `json:"project"`     // 制品库 project
	UploadPath string `json:"upload_path"` // 上传路径
}

// DumpSchemaRunTimeCtx TODO
type DumpSchemaRunTimeCtx struct {
	dbs      []string // 需要备份的表结构的数据库名称集合
	charset  string   // 当前实例的字符集
	dumpCmd  string
	isSpider bool // 是否spider中控
}

// Example godoc
func (c *SemanticDumpSchemaComp) Example() interface{} {
	comp := SemanticDumpSchemaComp{
		Params: DumpSchemaParam{
			Host:           "1.1.1.1",
			Port:           3306,
			CharSet:        "default",
			BackupFileName: "xx_schema.sql",
			BackupDir:      "/data/path1/path2",
		},
	}
	return comp
}

// Init init
//
//	@receiver c
//	@return err
func (c *SemanticDumpSchemaComp) Init() (err error) {
	conn, err := native.InsObject{
		Host: c.Params.Host,
		Port: c.Params.Port,
		User: c.GeneralParam.RuntimeAccountParam.AdminUser,
		Pwd:  c.GeneralParam.RuntimeAccountParam.AdminPwd,
	}.Conn()
	if err != nil {
		logger.Error("Connect %d failed:%s", c.Params.Port, err.Error())
		return err
	}
	alldbs, err := conn.ShowDatabases()
	if err != nil {
		logger.Error("show all databases failed:%s", err.Error())
		return err
	}

	version, err := conn.SelectVersion()
	if err != nil {
		logger.Error("获取version failed %s", err.Error())
		return err
	}
	c.isSpider = strings.Contains(version, "tdbctl")
	finaldbs := []string{}
	reg := regexp.MustCompile(`^bak_cbs`)
	for _, db := range util.FilterOutStringSlice(alldbs, computil.GetGcsSystemDatabasesIgnoreTest(version)) {
		if reg.MatchString(db) {
			continue
		}
		finaldbs = append(finaldbs, db)
	}
	if len(finaldbs) == 0 {
		return fmt.Errorf("变更实例排除系统库后，再也没有可以变更的库")
	}
	c.dbs = finaldbs
	c.charset = c.Params.CharSet
	if c.Params.CharSet == "default" {
		if c.charset, err = conn.ShowServerCharset(); err != nil {
			logger.Error("获取实例的字符集失败：%s", err.Error())
			return err
		}
	}
	return err
}

// Precheck 预检查
//
//	@receiver c
//	@return err
func (c *SemanticDumpSchemaComp) Precheck() (err error) {
	c.dumpCmd = path.Join(cst.MysqldInstallPath, "bin", "mysqldump")
	// to export the table structure from the central control
	// you need to use the mysqldump that comes with the central control
	if c.isSpider {
		c.dumpCmd = path.Join(cst.TdbctlInstallPath, "bin", "mysqldump")
	}
	if !osutil.FileExist(c.dumpCmd) {
		return fmt.Errorf("dumpCmd: %s文件不存在", c.dumpCmd)
	}
	if !osutil.FileExist(c.Params.BackupDir) {
		return fmt.Errorf("backupdir: %s不存在", c.Params.BackupDir)
	}
	return
}

// DumpSchema 运行备份表结构
//
//	@receiver c
//	@return err
func (c *SemanticDumpSchemaComp) DumpSchema() (err error) {
	var dumper mysqlutil.Dumper
	dumper = &mysqlutil.MySQLDumperTogether{
		MySQLDumper: mysqlutil.MySQLDumper{
			DumpDir:      c.Params.BackupDir,
			Ip:           c.Params.Host,
			Port:         c.Params.Port,
			DbBackupUser: c.GeneralParam.RuntimeAccountParam.AdminUser,
			DbBackupPwd:  c.GeneralParam.RuntimeAccountParam.AdminPwd,
			DbNames:      c.dbs,
			DumpCmdFile:  c.dumpCmd,
			Charset:      c.charset,
			MySQLDumpOption: mysqlutil.MySQLDumpOption{
				NoData:       true,
				AddDropTable: true,
				NeedUseDb:    true,
				DumpRoutine:  true,
				DumpTrigger:  false,
			},
		},
		OutputfileName: c.Params.BackupFileName,
	}
	if err := dumper.Dump(); err != nil {
		logger.Error("dump failed: ", err.Error())
		return err
	}
	return nil
}

// Upload TODO
func (c *SemanticDumpSchemaComp) Upload() (err error) {
	if reflect.DeepEqual(c.Params.FileServer, FileServer{}) {
		logger.Info("the fileserver parameter is empty no upload is required ~")
		return nil
	}
	schemafile := path.Join(c.Params.BackupDir, c.Params.BackupFileName)
	r := path.Join("generic", c.Params.FileServer.Project, c.Params.FileServer.Bucket, c.Params.FileServer.UploadPath)
	uploadUrl, err := url.JoinPath(c.Params.FileServer.URL, r, "/")
	if err != nil {
		logger.Error("call url joinPath failed %s ", err.Error())
		return err
	}
	if c.Params.BkCloudId == 0 {
		uploadUrl, err = url.JoinPath(
			c.Params.FileServer.URL, path.Join(
				"/generic", c.Params.FileServer.Project,
				c.Params.FileServer.Bucket, c.Params.FileServer.UploadPath, c.Params.BackupFileName,
			),
		)
		if err != nil {
			logger.Error("call url joinPath failed %s ", err.Error())
			return err
		}
	}
	logger.Info("bk_cloud_id:%d,upload url:%s", c.Params.BkCloudId, uploadUrl)
	resp, err := bkrepo.UploadFile(
		schemafile, uploadUrl, c.Params.FileServer.Username, c.Params.FileServer.Password,
		c.Params.BkCloudId, c.Params.DBCloudToken,
	)
	if err != nil {
		logger.Error("upload sqlfile error %s", err.Error())
		return err
	}
	if resp.Code != 0 {
		errMsg := fmt.Sprintf(
			"upload respone code is %d,respone msg:%s,traceId:%s",
			resp.Code,
			resp.Message,
			resp.RequestId,
		)
		logger.Error(errMsg)
		return fmt.Errorf(errMsg)
	}
	logger.Info("Resp: code:%d,msg:%s,traceid:%s", resp.Code, resp.Message, resp.RequestId)
	var uploadRespdata bkrepo.UploadRespData
	if err := json.Unmarshal(resp.Data, &uploadRespdata); err != nil {
		logger.Error("unmarshal upload respone data failed %s", err.Error())
		return err
	}
	logger.Info("%v", uploadRespdata)
	return nil
}
