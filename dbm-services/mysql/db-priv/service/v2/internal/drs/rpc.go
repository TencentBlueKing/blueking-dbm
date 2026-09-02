package drs

import (
	"encoding/json"
	"log/slog"
	"net/http"

	"github.com/pkg/errors"
)

type TableDataType []map[string]interface{}

type CmdResult struct {
	Cmd          string        `json:"cmd"`
	TableData    TableDataType `json:"table_data"`
	RowsAffected int64         `json:"rows_affected"`
	ErrorMsg     string        `json:"error_msg"`
}

type OneAddressResult struct {
	Address    string      `json:"address"`
	CmdResults []CmdResult `json:"cmd_results"`
	ErrorMsg   string      `json:"error_msg"`
}

func (c *OneAddressResult) String() string {
	b, _ := json.Marshal(c)
	return string(b)
}

type drsRequest struct {
	Addresses []string `form:"addresses" json:"addresses" url:"addresses"` // mysql实例数组，ip:port数组
	Cmds      []string `form:"cmds" json:"cmds" url:"cmds"`                // sql语句数组
	Force     bool     `form:"force" json:"force" url:"force"`             // 是否强制执行，强制：一个sql语句执行失败，不会中断，继续执行其他sql语句
	/*
			QueryTimeout是sql执行的超时时间，默认超时时间是30秒
			ctx, cancel := context.WithTimeout(context.Background(), time.Second*time.Duration(timeout))
		    defer cancel()
			rows, err := db.QueryxContext(ctx, cmd)
	*/
	QueryTimeout int64 `form:"query_timeout" json:"query_timeout" url:"query_timeout"` // sql执行超时时间
	BkCloudId    int64 `form:"bk_cloud_id" json:"bk_cloud_id" url:"bk_cloud_id"`       // mysql服务所在的云域
	SkipSetNames bool  `form:"skip_set_names" json:"skip_set_names" url:"skip_set_names"`
}

/*
	{
	  "code": 0,
	  "data": [
	    {
	      "address": "x.x.x.x:20000",
	      "cmd_results": [
	        {
	          "cmd": "elect * from test.dba_grant_result where id = \"276e5624-b142-11ef-bf35-5254006e4b4c\"",
	          "table_data": null,
	          "rows_affected": 0,
	          "error_msg": "" 执行 sql 出错, 比如语法错误
	        }
	      ],
	      "error_msg": "" 连接 addr 出错, 比如 ip 不对
	    }
	  ],
	  "msg": ""  调用 api 出错, 比如 request body 结构不对
	}
*/
func (c *drsClient) rpc(path string, req *drsRequest) (res []*OneAddressResult, err error) {
	b, err := json.Marshal(req)
	if err != nil {
		slog.Error("drs rpc", slog.String("err", err.Error()))
		return nil, err
	}

	apiRes, err := c.do(
		http.MethodPost,
		path,
		b,
	)
	if err != nil {
		slog.Error("drs rpc", slog.String("err", err.Error()))
		return nil, err
	}

	if apiRes.Code != 0 {
		err := errors.New(apiRes.Message)
		slog.Error("drs rpc", slog.String("err", err.Error()))
		return nil, err
	}

	err = json.Unmarshal(apiRes.Data, &res)
	if err != nil {
		slog.Error("drs rpc", slog.String("err", err.Error()))
		return nil, err
	}

	return res, err
}
