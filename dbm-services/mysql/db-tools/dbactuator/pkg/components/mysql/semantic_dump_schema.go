/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

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
	"dbm-services/common/go-pubpkg/cmutil"
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
	Host            string `json:"host"  validate:"required,ip"`                // 当前实例的主机地址
	Port            int    `json:"port"  validate:"required,lt=65536,gte=3306"` // 当前实例的端口
	CharSet         string `json:"charset" validate:"required,checkCharset"`    // 字符集参数
	CompressPkgName string `json:"com"`
	UploadBkRepoParam
}

// UploadBkRepoParam upload to bk repo param
type UploadBkRepoParam struct {
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
	dbs           []string // 需要备份的表结构的数据库名称集合
	charset       string   // 当前实例的字符集
	dumpCmd       string
	useTmysqldump bool     // 使用自研的mysqldump 并发导出
	isSpider      bool     // 是否spider中控
	ignoreTables  []string // 忽略的表集合
}

// Example godoc
func (c *SemanticDumpSchemaComp) Example() interface{} {
	comp := SemanticDumpSchemaComp{
		Params: DumpSchemaParam{
			Host:              "1.1.1.1",
			Port:              3306,
			CharSet:           "default",
			UploadBkRepoParam: UploadBkRepoParam{},
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
	defer func() {
		if conn != nil {
			conn.Close()
		}
	}()
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
	// 临时方案
	if cmutil.FileExists("/home/mysql/dbbackup/mysqldump_x86_64") {
		c.dumpCmd = "/home/mysql/dbbackup/mysqldump_x86_64"
		c.useTmysqldump = true
	} else {
		c.dumpCmd = path.Join(cst.MysqldInstallPath, "bin", "mysqldump")
	}
	// to export the table structure from the central control
	// you need to use the mysqldump that comes with the central control
	if c.isSpider {
		c.dumpCmd = path.Join(cst.TdbctlInstallPath, "bin", "mysqldump")
	}
	finaldbs := []string{}
	reg := regexp.MustCompile(`^bak_cbs`)
	ignoreDBs := computil.GetGcsSystemDatabasesIgnoreTest(version)
	if c.isSpider {
		// test 库里面的这些表没有主键，导入中控会失败
		c.ignoreTables = []string{"test.conn_log", "test.free_space"}
	}
	for _, db := range util.FilterOutStringSlice(alldbs, ignoreDBs) {
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
	if !osutil.FileExist(c.dumpCmd) {
		return fmt.Errorf("dumpCmd: %s文件不存在", c.dumpCmd)
	}
	if !osutil.FileExist(c.Params.BackupDir) {
		return fmt.Errorf("backupdir: %s不存在", c.Params.BackupDir)
	}
	return
}

// DumpSchema 运行备份表结构

// DumpSchema TODO
// @receiver c
// @return err
func (c *SemanticDumpSchemaComp) DumpSchema() (err error) {
	var dumper mysqlutil.Dumper
	dumpOption := mysqlutil.MySQLDumpOption{
		DumpSchema:   true,
		AddDropTable: true,
		DumpRoutine:  true,
		DumpTrigger:  false,
		DumpEvent:    true,
		Quick:        true,
	}
	if c.isSpider {
		dumpOption.GtidPurgedOff = true
		c.useTmysqldump = false
	}
	dumper = &mysqlutil.MySQLDumperTogether{
		MySQLDumper: mysqlutil.MySQLDumper{
			DumpDir:         c.Params.BackupDir,
			Ip:              c.Params.Host,
			Port:            c.Params.Port,
			DbBackupUser:    c.GeneralParam.RuntimeAccountParam.AdminUser,
			DbBackupPwd:     c.GeneralParam.RuntimeAccountParam.AdminPwd,
			DbNames:         c.dbs,
			IgnoreTables:    c.ignoreTables,
			DumpCmdFile:     c.dumpCmd,
			Charset:         c.charset,
			MySQLDumpOption: dumpOption,
		},
		UseTMySQLDump:  c.useTmysqldump,
		OutputfileName: c.Params.BackupFileName,
	}
	if err := dumper.Dump(); err != nil {
		logger.Error("dump failed: %s", err.Error())
		return err
	}
	return nil
}

// Upload do upload
func (c *SemanticDumpSchemaComp) Upload() (err error) {
	return c.Params.Upload()
}

// Upload do upload comp
func (c UploadBkRepoParam) Upload() (err error) {
	if reflect.DeepEqual(c.FileServer, FileServer{}) {
		logger.Info("the fileserver parameter is empty no upload is required ~")
		return nil
	}
	schemafile := path.Join(c.BackupDir, c.BackupFileName)
	r := path.Join("generic", c.FileServer.Project, c.FileServer.Bucket, c.FileServer.UploadPath)
	uploadUrl, err := url.JoinPath(c.FileServer.URL, r, "/")
	if err != nil {
		logger.Error("call url joinPath failed %s ", err.Error())
		return err
	}
	if c.BkCloudId == 0 {
		uploadUrl, err = url.JoinPath(
			c.FileServer.URL, path.Join(
				"/generic", c.FileServer.Project,
				c.FileServer.Bucket, c.FileServer.UploadPath, c.BackupFileName,
			),
		)
		if err != nil {
			logger.Error("call url joinPath failed %s ", err.Error())
			return err
		}
	}
	logger.Info("bk_cloud_id:%d,upload url:%s", c.BkCloudId, uploadUrl)
	resp, err := bkrepo.UploadFile(
		schemafile, uploadUrl, c.FileServer.Username, c.FileServer.Password,
		c.BkCloudId, c.DBCloudToken,
	)
	if err != nil {
		logger.Error("upload sqlfile error %s", err.Error())
		return err
	}
	if resp.Code != 0 {
		errMsg := fmt.Sprintf(
			"upload response code is %d,response msg:%s,traceId:%s",
			resp.Code,
			resp.Message,
			resp.RequestId,
		)
		logger.Error(errMsg)
		return fmt.Errorf("%s", errMsg)
	}
	logger.Info("resp: code:%d,msg:%s,traceid:%s", resp.Code, resp.Message, resp.RequestId)
	var uploadRespdata bkrepo.UploadRespData
	if err := json.Unmarshal(resp.Data, &uploadRespdata); err != nil {
		logger.Error("unmarshal upload response data failed %s", err.Error())
		return err
	}
	logger.Info("%v", uploadRespdata)
	return nil
}
