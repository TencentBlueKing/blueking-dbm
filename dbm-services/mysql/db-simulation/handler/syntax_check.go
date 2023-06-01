package handler

import (
	"os"
	"path"
	"strings"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app"
	"dbm-services/mysql/db-simulation/app/syntax"

	"github.com/gin-gonic/gin"
	"github.com/spf13/viper"
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
		workdir = "/tmp"
	}
}

// SyntaxHandler TODO
type SyntaxHandler struct{}

// CheckSqlStringParam TODO
type CheckSqlStringParam struct {
	ClusterType string   `json:"cluster_type" binding:"required"`
	Sqls        []string `json:"sqls" binding:"gt=0,dive,required"` // SQLS
	Version     string   `json:"version"`                           // mysql版本
}

// SyntaxCheckSQL TODO
func SyntaxCheckSQL(r *gin.Context) {
	requestId := r.GetString("request_id")
	var param CheckSqlStringParam
	// 将request中的数据按照json格式直接解析到结构体中
	if err := r.ShouldBindJSON(&param); err != nil {
		logger.Error("ShouldBind failed %s", err)
		SendResponse(r, err, nil, requestId)
		return
	}
	sqlContext := strings.Join(param.Sqls, "\n")
	fileName := "ce_" + cmutil.RandStr(10) + ".sql"
	f := path.Join(workdir, fileName)
	err := os.WriteFile(f, []byte(sqlContext), 0666)
	if err != nil {
		SendResponse(r, err, err.Error(), requestId)
		return
	}
	check := &syntax.TmysqlParseFile{
		TmysqlParse: syntax.TmysqlParse{
			TmysqlParseBinPath: tmysqlParserBin,
			BaseWorkdir:        workdir,
		},
		Param: syntax.CheckSqlFileParam{
			BkRepoBasePath: "",
			FileNames:      []string{fileName},
			MysqlVersion:   param.Version,
		},
	}
	var data map[string]*syntax.CheckInfo
	logger.Info("cluster type :%s", param.ClusterType)
	switch strings.ToLower(param.ClusterType) {
	case app.Spider, app.TendbCluster:
		data, err = check.DoSQL(app.Spider)
	case app.MySQL:
		data, err = check.DoSQL(app.MySQL)
	default:
		data, err = check.DoSQL(app.MySQL)
	}

	if err != nil {
		SendResponse(r, err, data, requestId)
		return
	}
	SendResponse(r, nil, data, requestId)
}

// CheckFileParam TODO
type CheckFileParam struct {
	ClusterType string   `json:"cluster_type"`
	Path        string   `json:"path" binding:"required"`            // 蓝鲸制品库SQL文件存储的相对路径
	Files       []string `json:"files" binding:"gt=0,dive,required"` // SQL 文件名
	Version     string   `json:"version"`                            // mysql版本
}

// SyntaxCheckFile 运行语法检查
//
//	@receiver s
//	@param r
func SyntaxCheckFile(r *gin.Context) {
	requestId := r.GetString("request_id")
	var param CheckFileParam
	// 将request中的数据按照json格式直接解析到结构体中
	if err := r.ShouldBindJSON(&param); err != nil {
		logger.Error("ShouldBind failed %s", err)
		SendResponse(r, err, nil, requestId)
		return
	}
	check := &syntax.TmysqlParseFile{
		TmysqlParse: syntax.TmysqlParse{
			TmysqlParseBinPath: tmysqlParserBin,
			BaseWorkdir:        workdir,
		},
		Param: syntax.CheckSqlFileParam{
			BkRepoBasePath: param.Path,
			FileNames:      param.Files,
			MysqlVersion:   param.Version,
		},
	}
	var data map[string]*syntax.CheckInfo
	var err error
	logger.Info("cluster type :%s", param.ClusterType)
	switch strings.ToLower(param.ClusterType) {
	case app.Spider, app.TendbCluster:
		data, err = check.Do(app.Spider)
	case app.MySQL:
		data, err = check.Do(app.MySQL)
	default:
		data, err = check.Do(app.MySQL)
	}

	if err != nil {
		SendResponse(r, err, data, requestId)
		return
	}
	SendResponse(r, nil, data, requestId)
}
