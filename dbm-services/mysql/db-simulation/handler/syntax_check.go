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
	"time"

	"github.com/gin-gonic/gin"
	"github.com/samber/lo"
	"github.com/spf13/viper"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app"
	"dbm-services/mysql/db-simulation/app/syntax"
)

var tmysqlParserBin string
var workdir string

// ForceDumpAll 是否强制 dump 所有库表
var ForceDumpAll bool

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
	ForceDumpAll = false
}

// SyntaxHandler 语法检查 handler
type SyntaxHandler struct {
	BaseHandler
}

// RegisterRouter 注册路由信息
func (s *SyntaxHandler) RegisterRouter(engine *gin.Engine) {
	r := engine.Group("/syntax")
	{
		// syntax
		r.POST("/check/file", s.SyntaxCheckFile)
		r.POST("/check/sql", s.SyntaxCheckSQL)
		r.POST("/upload/ddl/tbls", s.CreateAndUploadDDLTblListFile)
		r.POST("/parse/file/relation/db", s.ParseSQLFileRelationDb)
		r.POST("/parse/sql/relation/db", s.ParseSQLRelationDb)
		r.POST("/parse/set/dumpall", s.SetDumpAll)
	}
}

// CheckSQLStringParam sql string 语法检查参数
type CheckSQLStringParam struct {
	ClusterType string   `json:"cluster_type" binding:"required"`
	Versions    []string `json:"versions"`
	Sqls        []string `json:"sqls" binding:"gt=0,dive,required"`
}

// SetDumpAll set dump all
func (s *SyntaxHandler) SetDumpAll(r *gin.Context) {
	ForceDumpAll = !ForceDumpAll
	logger.Info("ForceDumpAll is: %v", ForceDumpAll)
}

// SyntaxCheckSQL 语法检查入参SQL string
func (s *SyntaxHandler) SyntaxCheckSQL(r *gin.Context) {
	var param CheckSQLStringParam
	var data map[string]*syntax.CheckInfo
	var versions []string
	// 将request中的数据按照json格式直接解析到结构体中
	if err := s.Prepare(r, &param); err != nil {
		logger.Error("Preare Error %s", err.Error())
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
	tpWorkdir := path.Join(workdir, time.Now().Format("20060102150405"))
	if err := os.MkdirAll(tpWorkdir, 0755); err != nil {
		s.SendResponse(r, err, err.Error())
		return
	}
	f := path.Join(tpWorkdir, fileName)
	err := os.WriteFile(f, []byte(sqlContext), 0600)
	if err != nil {
		s.SendResponse(r, err, err.Error())
		return
	}

	check := &syntax.TmysqlParseFile{
		TmysqlParse: syntax.TmysqlParse{
			TmysqlParseBinPath: tmysqlParserBin,
			BaseWorkdir:        tpWorkdir,
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
		s.SendResponse(r, err, data)
		return
	}
	s.SendResponse(r, nil, data)
}

// CheckFileParam 语法检查请求参数
type CheckFileParam struct {
	ClusterType string   `json:"cluster_type"`
	Path        string   `json:"path" binding:"required"`
	Versions    []string `json:"versions"`
	Files       []string `json:"files" binding:"gt=0,dive,required"`
}

// SyntaxCheckFile 运行语法检查
func (s *SyntaxHandler) SyntaxCheckFile(r *gin.Context) {
	var param CheckFileParam
	var data map[string]*syntax.CheckInfo
	var err error
	var versions []string
	// 将request中的数据按照json格式直接解析到结构体中
	if err = s.Prepare(r, &param); err != nil {
		logger.Error("ShouldBind failed %s", err)
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
		s.SendResponse(r, err, data)
		return
	}
	s.SendResponse(r, nil, data)
}

// CreateAndUploadDDLTblListFile 分析变更SQL DDL操作的表，并将文件上传到制品库
func (s *SyntaxHandler) CreateAndUploadDDLTblListFile(r *gin.Context) {
	var param CheckFileParam
	// 将request中的数据按照json格式直接解析到结构体中
	if err := s.Prepare(r, &param); err != nil {
		logger.Error("ShouldBind failed %s", err)
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
		s.SendResponse(r, err, nil)
		return
	}
	s.SendResponse(r, nil, "ok")
}

// ParseSQLFileRelationDb 解析SQL文件中涉及到需要变更的数据库
func (s SyntaxHandler) ParseSQLFileRelationDb(r *gin.Context) {
	if ForceDumpAll {
		s.SendResponse(r, nil, gin.H{
			"create_dbs": []string{},
			"dbs":        []string{},
			"dump_all":   true,
			"timestamp":  time.Now().Unix(),
			"desc":       "force dump all",
		})
		return
	}
	var param CheckFileParam
	// 将request中的数据按照json格式直接解析到结构体中
	if err := s.Prepare(r, &param); err != nil {
		logger.Error("ShouldBind failed %s", err)
		return
	}
	p := &syntax.TmysqlParseFile{
		TmysqlParse: syntax.TmysqlParse{
			TmysqlParseBinPath: tmysqlParserBin,
			BaseWorkdir:        workdir,
		},
		Param: syntax.CheckSQLFileParam{
			BkRepoBasePath: param.Path,
			FileNames:      param.Files,
		},
	}
	createDbs, dbs, allCommands, dumpall, err := p.DoParseRelationDbs("")
	if err != nil {
		s.SendResponse(r, err, nil)
		return
	}
	// 如果所有的命令都是alter table, dump指定库表
	logger.Debug("debug: %v,%d", allCommands, len(allCommands))
	if isAllOperateTable(allCommands) || isAllCreateTable(allCommands) {
		relationTbls, err := p.ParseSpecialTbls("")
		if err != nil {
			s.SendResponse(r, err, nil)
			return
		}
		s.SendResponse(r, nil, gin.H{
			"create_dbs":             createDbs,
			"dbs":                    dbs,
			"dump_all":               false,
			"just_dump_special_tbls": true,
			"special_tbls":           relationTbls,
			"timestamp":              time.Now().Unix(),
		})
		return
	}

	s.SendResponse(r, nil, gin.H{
		"create_dbs": createDbs,
		"dbs":        dbs,
		"dump_all":   dumpall,
		"timestamp":  time.Now().Unix(),
	})
}

func isAllOperateTable(allCommands []string) bool {
	return lo.Every([]string{syntax.SQLTypeAlterTable, syntax.SQLTypeUseDb,
		syntax.SQLTypeCreateIndex, syntax.SQLTypeDropTable}, allCommands)
}

func isAllCreateTable(allCommands []string) bool {
	return lo.Every([]string{syntax.SQLTypeCreateTable, syntax.SQLTypeUseDb}, allCommands)
}

// ParseSQLRelationDb  语法检查入参SQL string
func (s *SyntaxHandler) ParseSQLRelationDb(r *gin.Context) {
	var param CheckSQLStringParam
	// 将request中的数据按照json格式直接解析到结构体中
	if err := s.Prepare(r, &param); err != nil {
		logger.Error("Preare Error %s", err.Error())
		return
	}
	sqlContext := strings.Join(param.Sqls, "\n")
	fileName := "ce_" + cmutil.RandStr(10) + ".sql"
	tmpWorkdir := path.Join(workdir, time.Now().Format("20060102150405"))
	if err := os.MkdirAll(tmpWorkdir, 0755); err != nil {
		s.SendResponse(r, err, err.Error())
		return
	}
	f := path.Join(tmpWorkdir, fileName)
	err := os.WriteFile(f, []byte(sqlContext), 0600)
	if err != nil {
		s.SendResponse(r, err, err.Error())
		return
	}

	p := &syntax.TmysqlParseFile{
		TmysqlParse: syntax.TmysqlParse{
			TmysqlParseBinPath: tmysqlParserBin,
			BaseWorkdir:        tmpWorkdir,
		},
		IsLocalFile: true,
		Param: syntax.CheckSQLFileParam{
			BkRepoBasePath: "",
			FileNames:      []string{fileName},
		},
	}
	// defer p.DelTempDir()
	createDbs, dbs, allCommands, dumpall, err := p.DoParseRelationDbs("")
	if err != nil {
		s.SendResponse(r, err, nil)
		return
	}
	// 如果所有的命令都是alter table, dump指定库表
	logger.Info("make debug: %v,%d", allCommands, len(allCommands))
	if isAllOperateTable(allCommands) || isAllCreateTable(allCommands) {
		relationTbls, err := p.ParseSpecialTbls("")
		if err != nil {
			s.SendResponse(r, err, nil)
			return
		}
		s.SendResponse(r, nil, gin.H{
			"create_dbs":             createDbs,
			"dbs":                    dbs,
			"dump_all":               false,
			"just_dump_special_tbls": true,
			"special_tbls":           relationTbls,
			"timestamp":              time.Now().Unix(),
		})
		return
	}

	s.SendResponse(r, nil, gin.H{
		"create_dbs": createDbs,
		"dbs":        dbs,
		"dump_all":   dumpall,
		"timestamp":  time.Now().Unix(),
	})
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
