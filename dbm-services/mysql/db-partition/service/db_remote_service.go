package service

import (
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"strings"

	"dbm-services/mysql/db-partition/util"
)

// OneAddressExecuteSqlBasic OneAddressExecuteSql 通过db-remote-service服务连接mysql实例执行sql语句
func OneAddressExecuteSqlBasic(vtype string, queryRequest QueryRequest) (oneAddressResult, error) {
	slog.Info("msg", "OneAddressExecuteSqlBasic", "begin")
	var errMsg []string
	var result oneAddressResult
	var temp []oneAddressResult
	var url string
	if vtype == "mysql" {
		url = "mysql/rpc/"
	} else if vtype == "proxy" {
		url = "proxy-admin/rpc/"
	}
	apiResp, err := util.DrsClient.Do(http.MethodPost, url, queryRequest)
	if err != nil {
		slog.Error("drs err", err)
		return result, err
	}
	if apiResp.Code != 0 {
		slog.Error("remote service api", fmt.Errorf(apiResp.Message))
		return result, fmt.Errorf(apiResp.Message)
	} else {
		if err := json.Unmarshal(apiResp.Data, &temp); err != nil {
			return result, err
		}
		if temp[0].ErrorMsg != "" {
			errMsg = append(errMsg, fmt.Sprintf("instance: %s err: %s", queryRequest.Addresses[0], temp[0].ErrorMsg))
		}
		for _, res := range temp[0].CmdResults {
			if res.ErrorMsg != "" {
				errMsg = append(errMsg, fmt.Sprintf("instance: %s execute: `%s` error:`%s`;",
					queryRequest.Addresses[0], strings.Replace(res.Cmd, "%", "%%", -1),
					strings.Replace(res.ErrorMsg, "%", "%%", -1)))
			}
		}
	}

	if len(errMsg) > 0 {
		slog.Error("msg", fmt.Errorf(strings.Join(errMsg, "\n")))
		return result, fmt.Errorf(strings.Join(errMsg, "\n"))
	}
	slog.Info("msg", "OneAddressExecuteSqlBasic", "end")
	return temp[0], nil

}

// OneAddressExecuteSql OneAddressExecuteSql 通过db-remote-service服务连接mysql实例执行sql语句
func OneAddressExecuteSql(queryRequest QueryRequest) (oneAddressResult, error) {
	slog.Info("msg", "queryRequest", queryRequest)
	result, err := OneAddressExecuteSqlBasic("mysql", queryRequest)
	if err != nil {
		return result, err
	}
	return result, nil
}

// QueryRequest OneAddressExecuteSql函数的入参
type QueryRequest struct {
	Addresses []string `form:"addresses" json:"addresses" url:"addresses"` // mysql实例数组，ip:port数组
	Cmds      []string `form:"cmds" json:"cmds" url:"cmds"`                // sql语句数组
	Force     bool     `form:"force" json:"force" url:"force"`             // 是否强制执行，强制：一个sql语句执行失败，不会中断，继续执行其他sql语句
	/*
			QueryTimeout是sql执行的超时时间，默认超时时间是30秒
			ctx, cancel := context.WithTimeout(context.Background(), time.Second*time.Duration(timeout))
		    defer cancel()
			rows, err := db.QueryxContext(ctx, cmd)
	*/
	QueryTimeout int `form:"query_timeout" json:"query_timeout" url:"query_timeout"` // sql执行超时时间
	BkCloudId    int `form:"bk_cloud_id" json:"bk_cloud_id" url:"bk_cloud_id"`       // mysql服务所在的云域
}

// oneAddressResult 在一个ip:port执行sql返回的结果
type oneAddressResult struct {
	Address    string      `json:"address"`
	CmdResults []cmdResult `json:"cmd_results"`
	ErrorMsg   string      `json:"error_msg"`
}

// cmdResult
type cmdResult struct {
	Cmd          string        `json:"cmd"`
	TableData    tableDataType `json:"table_data"`
	RowsAffected int           `json:"rows_affected"`
	ErrorMsg     string        `json:"error_msg"`
}

// tableDataType 查询返回记录
type tableDataType []map[string]interface{}

// PasswordResp mysql实例中user@host的密码以及加密类型
type PasswordResp struct {
	Psw     string `gorm:"column:psw;not_null;" json:"psw"`
	PwdType string `gorm:"column:psw_type;not_null;" json:"psw_type"`
}
