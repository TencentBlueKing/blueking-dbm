/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package handler

import (
	"os"
	"path"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/spf13/viper"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app"
	"dbm-services/mysql/db-simulation/app/syntax"
)

var tmysqlParserBin string
var workdir string

func init() {
	tmysqlParserBin = strings.TrimSpace(viper.GetString("tmysqlparser_bin"))
	// 容器环境会把 tmysqlparse 打包进来
	// 放到和 svr 程序一个目录下
	// 所以在使用这个工程的 img 时, 可以不用设置这个 env
	if len(tmysqlParserBin) == 0 {
		tmysqlParserBin = "/tmysqlparse"
	}
	workdir = strings.TrimSpace(viper.GetString("workdir"))
	if workdir == "" {
		if cmutil.FileExists("/tmp") {
			workdir = "/tmp"
			return
		}
		workdir = "/"
	}
}

// SyntaxHandler 语法检查 handler
type SyntaxHandler struct{}

// CheckSQLStringParam sql string 语法检查参数
type CheckSQLStringParam struct {
	ClusterType string   `json:"cluster_type" binding:"required"`
	Versions    []string `json:"versions"`
	Sqls        []string `json:"sqls" binding:"gt=0,dive,required"`
}

// SyntaxCheckSQL 语法检查入参SQL string
func SyntaxCheckSQL(r *gin.Context) {
	requestID := r.GetString("request_id")
	var param CheckSQLStringParam
	var data map[string]*syntax.CheckInfo
	var versions []string
	// 将request中的数据按照json格式直接解析到结构体中
	if err := r.ShouldBindJSON(&param); err != nil {
		logger.Error("ShouldBind failed %s", err)
		SendResponse(r, err, nil, requestID)
		return
	}

	logger.Info("versions: %v", param.Versions)
	if len(param.Versions) == 0 {
		versions = []string{""}
	} else {
		versions = rebuildVersion(param.Versions)
	}

	sqlContext := strings.Join(param.Sqls, "\n")
	fileName := "ce_" + cmutil.RandStr(10) + ".sql"
	f := path.Join(workdir, fileName)
	err := os.WriteFile(f, []byte(sqlContext), 0600)
	if err != nil {
		SendResponse(r, err, err.Error(), requestID)
		return
	}

	check := &syntax.TmysqlParseFile{
		TmysqlParse: syntax.TmysqlParse{
			TmysqlParseBinPath: tmysqlParserBin,
			BaseWorkdir:        workdir,
		},
		IsLocalFile: true,
		Param: syntax.CheckSQLFileParam{
			BkRepoBasePath: "",
			FileNames:      []string{fileName},
		},
	}

	logger.Info("cluster type :%s,versions:%v", param.ClusterType, versions)

	switch strings.ToLower(param.ClusterType) {
	case app.Spider, app.TendbCluster:
		data, err = check.Do(app.Spider, []string{""})
	case app.MySQL:
		data, err = check.Do(app.MySQL, versions)
	default:
		data, err = check.Do(app.MySQL, versions)
	}

	if err != nil {
		SendResponse(r, err, data, requestID)
		return
	}
	SendResponse(r, nil, data, requestID)
}

// CheckFileParam 语法检查请求参数
type CheckFileParam struct {
	ClusterType string   `json:"cluster_type"`
	Path        string   `json:"path" binding:"required"`
	Versions    []string `json:"versions"`
	Files       []string `json:"files" binding:"gt=0,dive,required"`
}

// SyntaxCheckFile 运行语法检查
func SyntaxCheckFile(r *gin.Context) {
	requestID := r.GetString("request_id")
	var param CheckFileParam
	var data map[string]*syntax.CheckInfo
	var err error
	var versions []string
	// 将request中的数据按照json格式直接解析到结构体中
	if err = r.ShouldBindJSON(&param); err != nil {
		logger.Error("ShouldBind failed %s", err)
		SendResponse(r, err, nil, requestID)
		return
	}

	if len(param.Versions) == 0 {
		versions = []string{""}
	} else {
		versions = rebuildVersion(param.Versions)
	}

	check := &syntax.TmysqlParseFile{
		TmysqlParse: syntax.TmysqlParse{
			TmysqlParseBinPath: tmysqlParserBin,
			BaseWorkdir:        workdir,
		},
		Param: syntax.CheckSQLFileParam{
			BkRepoBasePath: param.Path,
			FileNames:      param.Files,
		},
	}

	logger.Info("cluster type :%s", param.ClusterType)
	switch strings.ToLower(param.ClusterType) {
	case app.Spider, app.TendbCluster:
		data, err = check.Do(app.Spider, []string{""})
	case app.MySQL:
		data, err = check.Do(app.MySQL, versions)
	default:
		data, err = check.Do(app.MySQL, versions)
	}

	if err != nil {
		SendResponse(r, err, data, requestID)
		return
	}
	SendResponse(r, nil, data, requestID)
}

// CreateAndUploadDDLTblListFile 分析变更SQL DDL操作的表，并将文件上传到制品库
func CreateAndUploadDDLTblListFile(r *gin.Context) {
	requestID := r.GetString("request_id")
	var param CheckFileParam
	// 将request中的数据按照json格式直接解析到结构体中
	if err := r.ShouldBindJSON(&param); err != nil {
		logger.Error("ShouldBind failed %s", err)
		SendResponse(r, err, nil, requestID)
		return
	}
	check := &syntax.TmysqlParseFile{
		TmysqlParse: syntax.TmysqlParse{
			TmysqlParseBinPath: tmysqlParserBin,
			BaseWorkdir:        workdir,
		},
		Param: syntax.CheckSQLFileParam{
			BkRepoBasePath: param.Path,
			FileNames:      param.Files,
		},
	}
	if err := check.CreateAndUploadDDLTblFile(); err != nil {
		SendResponse(r, err, nil, requestID)
		return
	}
	SendResponse(r, nil, "ok", requestID)
}

// rebuildVersion  tmysql 需要指定特殊的version
func rebuildVersion(versions []string) (rebuildVers []string) {
	if len(versions) == 0 {
		return
	}
	rebuildVers = make([]string, 0)
	for _, bVer := range versions {
		switch {
		case strings.Contains(bVer, "5.5"):
			rebuildVers = append(rebuildVers, "5.5.24")
		case strings.Contains(bVer, "5.6"):
			rebuildVers = append(rebuildVers, "5.6.24")
		case strings.Contains(bVer, "5.7"):
			rebuildVers = append(rebuildVers, "5.7.20")
		case strings.Contains(bVer, "8.0"):
			rebuildVers = append(rebuildVers, "8.0.18")
		}
	}
	return rebuildVers
}
