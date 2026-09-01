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
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/samber/lo"
	"github.com/spf13/viper"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app/syntax"
	"dbm-services/mysql/db-simulation/app/tmysqlver"
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
		r.POST("/check/inject", s.CheckSQLInject)
		r.POST("/upload/ddl/tbls", s.CreateAndUploadDDLTblListFile)
		r.POST("/parse/file/relation/db", s.ParseSQLFileRelationDb)
		r.POST("/parse/sql/relation/db", s.ParseSQLRelationDb)
		r.POST("/parse/sql/statement", s.ParseSQLTables)
		r.POST("/parse/file/statement", s.ParseSQLFileStatement)
		r.POST("/parse/set/dumpall", s.SetDumpAll)
	}
}

// SyntaxCheckParam 语法检查请求参数
type SyntaxCheckParam struct {
	BkBizID     int      `json:"bk_biz_id"`
	ClusterType string   `json:"cluster_type"`
	Versions    []string `json:"versions"`
}

// CheckFileParam 语法检查请求参数
type CheckFileParam struct {
	SyntaxCheckParam
	Path           string                     `json:"path" binding:"required"`
	Files          []string                   `json:"files" binding:"gt=0,dive,required"`
	ExecuteObjects []syntax.ExecuteSQLFileObj `json:"execute_objects"`
}

// fillBkBizIDFromPath 当 bk_biz_id 为 0 时，尝试从 path 最后一段解析业务 ID
// 例如 path="mysql/sqlfile/123" 时解析得到 bk_biz_id=123
func (p *CheckFileParam) fillBkBizIDFromPath() {
	if p.BkBizID != 0 {
		return
	}
	lastSeg := path.Base(strings.TrimRight(p.Path, "/"))
	bizID, err := strconv.Atoi(lastSeg)
	if err != nil || bizID <= 0 {
		return
	}
	p.BkBizID = bizID
	logger.Info("bk_biz_id is 0, parsed from path %s as %d", p.Path, bizID)
}

// InjectCheckParam SQL 注入检测请求参数
type InjectCheckParam struct {
	SyntaxCheckParam
	Sql                    string `json:"sql" binding:"required"`
	JudgeSubqueryDiffTable bool   `json:"judge_subquery_diff_table"`
}

// CheckSQLStringParam sql string 语法检查参数
type CheckSQLStringParam struct {
	SyntaxCheckParam
	Sqls []string `json:"sqls" binding:"gt=0,dive,required"`
}

// ParseSQLFileStatementParam 分析 SQL 文件语句请求参数
type ParseSQLFileStatementParam struct {
	CheckFileParam
	// IncludeSQLText 是否在 alter_tables 中返回 sql_text；不传时默认 true
	IncludeSQLText *bool `json:"include_sql_text"`
}

func (p ParseSQLFileStatementParam) includeSQLText() bool {
	return p.IncludeSQLText == nil || *p.IncludeSQLText
}

// ParseSQLTablesParam 单条 SQL string 解析表/语句类型参数
type ParseSQLTablesParam struct {
	SyntaxCheckParam
	Sql string `json:"sql" binding:"required"`
}

// SetDumpAll set dump all
func (s *SyntaxHandler) SetDumpAll(r *gin.Context) {
	ForceDumpAll = !ForceDumpAll
	logger.Info("ForceDumpAll is: %v", ForceDumpAll)
}

// SyntaxCheckSQL 语法检查入参SQL string
func (s *SyntaxHandler) SyntaxCheckSQL(r *gin.Context) {
	var param CheckSQLStringParam
	var versions []string
	// 将request中的数据按照json格式直接解析到结构体中
	if err := s.Prepare(r, &param); err != nil {
		logger.Error("Prepare Error %s", err.Error())
		return
	}

	logger.Info("versions: %v", param.Versions)
	if len(param.Versions) == 0 {
		versions = []string{""}
	} else {
		versions = tmysqlver.Rebuild(param.Versions)
	}

	sqlContext := strings.Join(param.Sqls, "\n")
	fileName := "ce_" + cmutil.RandStr(10) + ".sql"
	// 使用 MkdirTemp，避免同秒并发请求共享目录后被 DelTempDir 互相删除
	tpWorkdir, err := os.MkdirTemp(workdir, "syntax-sql-")
	if err != nil {
		s.SendResponse(r, err, err.Error())
		return
	}
	f := path.Join(tpWorkdir, fileName)
	if err = os.WriteFile(f, []byte(sqlContext), 0600); err != nil {
		_ = os.RemoveAll(tpWorkdir)
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
			BkBizID:        param.BkBizID,
			ClusterType:    param.ClusterType,
			BkRepoBasePath: "",
			FileNames:      []string{fileName},
			ExecuteObjects: []syntax.ExecuteSQLFileObj{
				{
					LineId:        0,
					SQLFiles:      []string{fileName},
					IgnoreDbNames: nil,
					// 不硬编码业务库名；由 SQL 自身 USE / 库表限定名表达上下文
					DbNames: nil,
				},
			},
		},
	}

	logger.Info("cluster type :%s,versions:%v", param.ClusterType, versions)
	data, err := check.RunSyntaxCheck(versions)
	if err != nil {
		s.SendResponse(r, err, data)
		return
	}
	s.SendResponse(r, nil, data)
}

// CheckSQLInject 静态 SQL 注入启发式检测
func (s *SyntaxHandler) CheckSQLInject(r *gin.Context) {
	var param InjectCheckParam
	if err := s.Prepare(r, &param); err != nil {
		logger.Error("Prepare Error %s", err.Error())
		return
	}

	var versions []string
	if len(param.Versions) == 0 {
		versions = []string{""}
	} else {
		versions = tmysqlver.Rebuild(param.Versions)
		if len(versions) == 0 {
			versions = []string{""}
		}
	}
	version := versions[0]

	fileName := "ce_" + cmutil.RandStr(10) + ".sql"
	tmpWorkdir, err := os.MkdirTemp(workdir, "syntax-inject-")
	if err != nil {
		s.SendResponse(r, err, err.Error())
		return
	}
	f := path.Join(tmpWorkdir, fileName)
	if err = os.WriteFile(f, []byte(param.Sql), 0600); err != nil {
		_ = os.RemoveAll(tmpWorkdir)
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
			BkBizID:        param.BkBizID,
			ClusterType:    param.ClusterType,
			BkRepoBasePath: "",
			FileNames:      []string{fileName},
		},
	}
	defer p.DelTempDir()

	logger.Info("inject check cluster_type:%s version:%s judge_subquery_diff_table:%v",
		param.ClusterType, version, param.JudgeSubqueryDiffTable)
	result, err := p.DoInjectCheck(version, param.JudgeSubqueryDiffTable)
	if err != nil {
		s.SendResponse(r, err, nil)
		return
	}
	s.SendResponse(r, nil, result)
}

// SyntaxCheckFile 运行语法检查
func (s *SyntaxHandler) SyntaxCheckFile(r *gin.Context) {
	var param CheckFileParam
	var err error
	var versions []string
	// 将request中的数据按照json格式直接解析到结构体中
	if err = s.Prepare(r, &param); err != nil {
		logger.Error("ShouldBind failed %s", err)
		return
	}
	param.fillBkBizIDFromPath()

	if len(param.Versions) == 0 {
		versions = []string{""}
	} else {
		versions = tmysqlver.Rebuild(param.Versions)
	}

	check := &syntax.TmysqlParseFile{
		TmysqlParse: syntax.TmysqlParse{
			TmysqlParseBinPath: tmysqlParserBin,
			BaseWorkdir:        workdir,
		},
		Param: syntax.CheckSQLFileParam{
			BkBizID:        param.BkBizID,
			ClusterType:    param.ClusterType,
			BkRepoBasePath: param.Path,
			FileNames:      param.Files,
			ExecuteObjects: param.ExecuteObjects,
		},
	}
	data, err := check.RunSyntaxCheck(versions)
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
	defer p.DelTempDir()
	createDbs, dbs, allCommands, dumpAll, err := p.DoParseRelationDbs("")
	if err != nil {
		s.SendResponse(r, err, nil)
		return
	}
	if len(dbs) > 400 {
		s.SendResponse(r, nil, gin.H{
			"create_dbs": createDbs,
			"dbs":        []string{},
			"dump_all":   true,
			"timestamp":  time.Now().Unix(),
			"desc":       "too many tables,change to dump all",
		})
		return
	}
	defer p.DelTempDir()
	// 如果所有的命令都是alter table, dump指定库表
	if isAllOperateTable(allCommands) && !dumpAll {
		relationTbls, err := p.ParseSpecialTbls("")
		if err != nil {
			s.SendResponse(r, err, nil)
			return
		}
		byteCount := 0
		for _, tbl := range relationTbls {
			byteCount += len(strings.Join(tbl.Tbls, ""))
		}
		byteCount += len(strings.Join(dbs, ""))
		byteCount += len(strings.Join(createDbs, ""))
		// sql语句的变更表数量大于2000,防止mysqldump 拼接参数过长导致执行失败
		// job 参数最大长度47k byte,base64 编码后, 1个字节变成1.33个字节 会经过
		if byteCount > 28000 {
			s.SendResponse(r, nil, gin.H{
				"create_dbs": createDbs,
				"dbs":        dbs,
				"dump_all":   dumpAll,
				"timestamp":  time.Now().Unix(),
			})
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
		"dump_all":   dumpAll,
		"timestamp":  time.Now().Unix(),
	})
}

func isAllOperateTable(allCommands []string) bool {
	if len(allCommands) == 0 {
		return false
	}
	// 不允许只用use db
	if len(allCommands) == 1 && allCommands[0] == syntax.SQLTypeUseDb {
		return false
	}
	return lo.Every([]string{
		syntax.SQLTypeAlterTable, syntax.SQLTypeUseDb,
		syntax.SQLTypeCreateIndex, syntax.SQLTypeDropTable,
		syntax.SQLTypeInsert, syntax.SQLTypeDelete, syntax.SQLTypeUpdate,
		syntax.SQLTypeCreateTable, syntax.SQLTypeReplace,
	}, allCommands)
}

// ParseSQLFileStatement 分析制品库 SQL 文件：按 command 合计计数，并按文件返回 ALTER TABLE 明细
func (s *SyntaxHandler) ParseSQLFileStatement(r *gin.Context) {
	var param ParseSQLFileStatementParam
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
	defer p.DelTempDir()
	byFile, err := p.DoParseSQLTablesByFile("")
	if err != nil {
		s.SendResponse(r, err, nil)
		return
	}
	summary, err := syntax.SummarizeParsedStatements(byFile, param.Files, param.includeSQLText())
	if err != nil {
		s.SendResponse(r, err, nil)
		return
	}
	s.SendResponse(r, nil, summary)
}

// ParseSQLTables 解析单条 SQL string，返回 []ParseIncludeTableBase
func (s *SyntaxHandler) ParseSQLTables(r *gin.Context) {
	var param ParseSQLTablesParam
	if err := s.Prepare(r, &param); err != nil {
		logger.Error("Prepare Error %s", err.Error())
		return
	}
	var versions []string
	if len(param.Versions) == 0 {
		versions = []string{""}
	} else {
		versions = tmysqlver.Rebuild(param.Versions)
		if len(versions) == 0 {
			versions = []string{""}
		}
	}
	version := versions[0]

	fileName := "ce_" + cmutil.RandStr(10) + ".sql"
	tmpWorkdir := path.Join(workdir, time.Now().Format("20060102150405"))
	if err := os.MkdirAll(tmpWorkdir, 0755); err != nil {
		s.SendResponse(r, err, err.Error())
		return
	}
	f := path.Join(tmpWorkdir, fileName)
	if err := os.WriteFile(f, []byte(param.Sql), 0600); err != nil {
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
			ClusterType:    param.ClusterType,
			BkRepoBasePath: "",
			FileNames:      []string{fileName},
		},
	}
	defer p.DelTempDir()
	queries, err := p.DoParseSQLTables(version)
	if err != nil {
		s.SendResponse(r, err, nil)
		return
	}
	s.SendResponse(r, nil, queries)
}

// ParseSQLRelationDb  语法检查入参SQL string
func (s *SyntaxHandler) ParseSQLRelationDb(r *gin.Context) {
	var param CheckSQLStringParam
	// 将request中的数据按照json格式直接解析到结构体中
	if err := s.Prepare(r, &param); err != nil {
		logger.Error("Prepare Error %s", err.Error())
		return
	}
	sqlContext := strings.Join(param.Sqls, "\n")
	fileName := "ce_" + cmutil.RandStr(10) + ".sql"
	tmpWorkdir, err := os.MkdirTemp(workdir, "syntax-sql-")
	if err != nil {
		s.SendResponse(r, err, err.Error())
		return
	}
	f := path.Join(tmpWorkdir, fileName)
	if err = os.WriteFile(f, []byte(sqlContext), 0600); err != nil {
		_ = os.RemoveAll(tmpWorkdir)
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
	defer p.DelTempDir()
	createDbs, dbs, allCommands, dumpAll, err := p.DoParseRelationDbs("")
	if err != nil {
		s.SendResponse(r, err, nil)
		return
	}
	// 如果所有的命令都是alter table, dump指定库表
	logger.Info("all command types: %v,%d", allCommands, len(allCommands))
	if isAllOperateTable(allCommands) && !dumpAll {
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
		"dump_all":   dumpAll,
		"timestamp":  time.Now().Unix(),
	})
}
