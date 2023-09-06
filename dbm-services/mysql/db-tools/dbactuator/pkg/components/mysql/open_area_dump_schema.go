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
	"os"
	"path"
	"reflect"
	"strings"

	"dbm-services/common/go-pubpkg/bkrepo"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

// OpenAreaDumpSchemaComp TODO
type OpenAreaDumpSchemaComp struct {
	GeneralParam                 *components.GeneralParam `json:"general"`
	Params                       OpenAreaDumpSchemaParam  `json:"extend"`
	OpenAreaDumpSchemaRunTimeCtx `json:"-"`
}

// OpenAreaDumpSchemaParam TODO
type OpenAreaDumpSchemaParam struct {
	Host          string              `json:"host"  validate:"required,ip"`                // 当前实例的主机地址
	Port          int                 `json:"port"  validate:"required,lt=65536,gte=3306"` // 当前实例的端口
	CharSet       string              `json:"charset" validate:"required,checkCharset"`    // 字符集参数 传default过来，按照源数据库的字符集
	RootId        string              `json:"root_id"`
	BkCloudId     int                 `json:"bk_cloud_id"`
	DBCloudToken  string              `json:"db_cloud_token"`
	DumpDirName   string              `json:"dump_dir_name"` // dump目录名称 {}_schema {}_data
	FileServer    FileServer          `json:"fileserver"`
	OpenAreaParam []OneOpenAreaSchema `json:"open_area_param"`
}

// OneOpenAreaSchema 用于存放一个区库表的信息
type OneOpenAreaSchema struct {
	Schema string   `json:"schema"` // 指定dump的库
	Tbales []string `json:"tables"`
}

// OpenAreaDumpSchemaRunTimeCtx TODO
type OpenAreaDumpSchemaRunTimeCtx struct {
	charset     string // 当前实例的字符集
	dumpCmd     string // 中控位置不一样
	isSpider    bool   // 是否spider中控
	dumpDirPath string // dump目录绝对路径
	tarName     string // 压缩文件名称 {}.tar.gz
	workDir     string // schema目录所在的位置 即位于/data/install/mysql_open_area
	uploadFile  []UploadFile
}

// UploadFile TODO
type UploadFile struct {
	FilePath string // 上传文件的绝对路径
	FileName string // 上传文件的名称
}

// Example TODO
func (c *OpenAreaDumpSchemaComp) Example() interface{} {
	comp := OpenAreaDumpSchemaComp{
		Params: OpenAreaDumpSchemaParam{
			Host:    "0.0.0.0",
			Port:    3306,
			CharSet: "default",
			RootId:  "xxxxxxx",
			OpenAreaParam: []OneOpenAreaSchema{
				{
					Schema: "data1",
					Tbales: []string{"tb1", "tb2"},
				},
				{
					Schema: "data2",
					Tbales: []string{"tb1", "tb2"},
				},
			},
		},
	}
	return comp
}

// Init TODO
func (c *OpenAreaDumpSchemaComp) Init() (err error) {
	// 连接实例，查询版本和字符集 同时根据版本确认是否为中控
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
	// 获取版本，下面通过版本判断是否是中控节点
	version, err := conn.SelectVersion()
	if err != nil {
		logger.Error("获取version failed %s", err.Error())
		return err
	}
	c.isSpider = strings.Contains(version, "tdbctl")
	c.charset = c.Params.CharSet
	if c.Params.CharSet == "default" {
		if c.charset, err = conn.ShowServerCharset(); err != nil {
			logger.Error("获取实例的字符集失败：%s", err.Error())
			return err
		}
	}
	c.workDir = path.Join(cst.BK_PKG_INSTALL_PATH, "mysql_open_area")
	c.dumpDirPath = path.Join(c.workDir, c.Params.DumpDirName)
	c.tarName = fmt.Sprintf("%s.tar.gz", c.Params.DumpDirName)
	err = os.MkdirAll(c.dumpDirPath, 0755)
	if err != nil {
		logger.Error("开区目录创建失败！%s", err.Error())
		return err
	}

	return nil
}

// Precheck TODO
func (c *OpenAreaDumpSchemaComp) Precheck() (err error) {
	c.dumpCmd = path.Join(cst.MysqldInstallPath, "bin", "mysqldump")
	if c.isSpider {
		c.dumpCmd = path.Join(cst.TdbctlInstallPath, "bin", "mysqldump")
	}
	if !osutil.FileExist(c.dumpCmd) {
		return fmt.Errorf("dumpCmd: %s文件不存在", c.dumpCmd)
	}
	return
}

// OpenAreaDumpSchema TODO
func (c *OpenAreaDumpSchemaComp) OpenAreaDumpSchema() (err error) {

	for _, oneOpenAreaSchema := range c.Params.OpenAreaParam {
		var dumper mysqlutil.Dumper
		outputfileName := fmt.Sprintf("%s.sql", oneOpenAreaSchema.Schema)
		schema := fmt.Sprintf("%s %s",
			oneOpenAreaSchema.Schema, strings.Join(oneOpenAreaSchema.Tbales, " "),
		)

		dumper = &mysqlutil.MySQLDumperTogether{
			MySQLDumper: mysqlutil.MySQLDumper{
				DumpDir:      c.dumpDirPath,
				Ip:           c.Params.Host,
				Port:         c.Params.Port,
				DbBackupUser: c.GeneralParam.RuntimeAccountParam.AdminUser,
				DbBackupPwd:  c.GeneralParam.RuntimeAccountParam.AdminPwd,
				DbNames:      []string{schema},
				DumpCmdFile:  c.dumpCmd,
				Charset:      c.charset,
				MySQLDumpOption: mysqlutil.MySQLDumpOption{
					NoData:        true,
					AddDropTable:  false,
					DumpRoutine:   true,
					DumpTrigger:   false,
					GtidPurgedOff: true,
				},
			},
			OutputfileName: outputfileName,
		}
		if err := dumper.Dump(); err != nil {
			logger.Error("dump failed: ", err.Error())
			return err
		}
	}

	return nil
}

// OpenAreaDumpData TODO
func (c *OpenAreaDumpSchemaComp) OpenAreaDumpData() (err error) {

	for _, oneOpenAreaSchema := range c.Params.OpenAreaParam {
		var dumper mysqlutil.Dumper
		if len(oneOpenAreaSchema.Tbales) == 0 {

			continue
		}
		outputfileName := fmt.Sprintf("%s.sql", oneOpenAreaSchema.Schema)
		schema := fmt.Sprintf("%s %s",
			oneOpenAreaSchema.Schema, strings.Join(oneOpenAreaSchema.Tbales, " "),
		)

		dumper = &mysqlutil.MySQLDumperTogether{
			MySQLDumper: mysqlutil.MySQLDumper{
				DumpDir:      c.dumpDirPath,
				Ip:           c.Params.Host,
				Port:         c.Params.Port,
				DbBackupUser: c.GeneralParam.RuntimeAccountParam.AdminUser,
				DbBackupPwd:  c.GeneralParam.RuntimeAccountParam.AdminPwd,
				DbNames:      []string{schema},
				DumpCmdFile:  c.dumpCmd,
				Charset:      c.charset,
				MySQLDumpOption: mysqlutil.MySQLDumpOption{
					NoData:       false,
					AddDropTable: false,
					NeedUseDb:    false,
					NoCreateTb:   true,
					DumpRoutine:  false,
				},
			},
			OutputfileName: outputfileName,
		}
		if err := dumper.Dump(); err != nil {
			logger.Error("dump failed: ", err.Error())
			return err
		}
	}

	return nil
}

// CompressDumpDir TODO
func (c *OpenAreaDumpSchemaComp) CompressDumpDir() (err error) {
	// // 如果不上传制品库，则不用压缩
	// if reflect.DeepEqual(c.Params.FileServer, FileServer{}) {
	//	logger.Info("the fileserver parameter is empty no upload is required ~")
	//	return nil
	// }
	// tarPath是开区目录压缩文件的绝对路径
	tarPath := path.Join(c.workDir, c.tarName)
	schemaInfo := UploadFile{
		FilePath: tarPath,
		FileName: c.tarName,
	}
	c.uploadFile = append(c.uploadFile, schemaInfo)
	tarCmd := fmt.Sprintf("tar -zcf %s -C %s %s", tarPath, c.workDir, c.Params.DumpDirName)
	output, err := osutil.ExecShellCommand(false, tarCmd)
	if err != nil {
		logger.Error("execute(%s) get an error:%s,%s", tarCmd, output, err.Error())
		return err
	}

	// 获取压缩文件的MD5
	md5Val, err := osutil.GetFileMd5(tarPath)
	if err != nil {
		logger.Error("Failed to obtain the MD5 value of the file!Error:%s", err.Error())
		return err
	}
	md5FileName := fmt.Sprintf("%s.md5sum", c.Params.DumpDirName)
	md5FilePath := path.Join(c.workDir, md5FileName)
	md5Info := UploadFile{
		FilePath: md5FilePath,
		FileName: md5FileName,
	}
	c.uploadFile = append(c.uploadFile, md5Info)
	md5File, err := os.Create(md5FilePath)
	if err != nil {
		logger.Error("create file(%s) get an error:%s", md5FileName, err.Error())
		return err
	}
	defer md5File.Close()
	_, err = md5File.WriteString(md5Val)
	if err != nil {
		logger.Error("Write md5 value(%s) to file(%s) error: %s", md5Val, md5FileName, err.Error())
		return err
	}
	return nil
}

// Upload TODO
func (c *OpenAreaDumpSchemaComp) Upload() (err error) {
	// 这里不传FileServer相关内容，则不会上传到制品库
	if reflect.DeepEqual(c.Params.FileServer, FileServer{}) {
		logger.Info("the fileserver parameter is empty no upload is required ~")
		return nil
	}

	for _, uf := range c.uploadFile {
		r := path.Join("generic", c.Params.FileServer.Project, c.Params.FileServer.Bucket, c.Params.FileServer.UploadPath)
		uploadUrl, err := url.JoinPath(c.Params.FileServer.URL, r, "/")
		if err != nil {
			logger.Error("call url joinPath failed %s ", err.Error())
			return err
		}
		if c.Params.BkCloudId == 0 {
			// 此处设置上传的路径，注意最后是待上传文件名，不是文件路径
			uploadUrl, err = url.JoinPath(
				c.Params.FileServer.URL, path.Join(
					"/generic", c.Params.FileServer.Project,
					c.Params.FileServer.Bucket, c.Params.FileServer.UploadPath, uf.FileName,
				),
			)
			if err != nil {
				logger.Error("call url joinPath failed %s ", err.Error())
				return err
			}
		}
		logger.Info("bk_cloud_id:%d,upload url:%s", c.Params.BkCloudId, uploadUrl)
		resp, err := bkrepo.UploadFile(
			uf.FilePath, uploadUrl, c.Params.FileServer.Username, c.Params.FileServer.Password,
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
	}

	return nil
}
