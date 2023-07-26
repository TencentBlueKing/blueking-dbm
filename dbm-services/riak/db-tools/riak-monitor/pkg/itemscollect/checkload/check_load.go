package checkload

import (
	"dbm-services/riak/db-tools/riak-monitor/pkg/internal/cst"
	"dbm-services/riak/db-tools/riak-monitor/pkg/utils"
	"encoding/json"
	"fmt"
	"strings"

	"golang.org/x/exp/slog"
)

func CheckResponseTime() (string, error) {
	item := `^node_put_fsm_time_mean|^node_get_fsm_time_mean|^node_put_fsm_rejected|^node_get_fsm_rejected`
	format := `awk '{print "\""$1"\" "$3}' | awk '{printf("%s: %s,",$1,$2)}' | sed "{s/,$/\}/g}" | sed "{s/^/{/g}"`
	cmd := fmt.Sprintf(`%s status | grep -E '%s' | grep -E -v '_60s|_total' | %s`, cst.RiakAdminPath, item, format)
	resp, err := utils.ExecShellCommand(false, cmd)
	if err != nil {
		// 这个检查项是在此riak节点运行时，执行集群ring检查，发现其他异常节点；如果此节点异常，检查联通性时可探测到
		if strings.Contains(err.Error(), "Node did not respond to ping!") {
			slog.Warn(fmt.Sprintf("check load. execute [ %s ] error: %s.", cmd, err.Error()))
			return "", nil
		} else {
			errInfo := fmt.Sprintf("check load. execute [ %s ] error: %s", cmd, err.Error())
			return "", fmt.Errorf(errInfo)
		}
	}
	type CheckItems struct {
		GetTime        int `json:"node_get_fsm_time_mean"` // 客户端发起GET请求到收到响应时间间隔的均值,微妙
		PutTime        int `json:"node_put_fsm_time_mean"` // 客户端发起PUT请求到收到响应时间间隔的均值,微妙
		GetRejectedNum int `json:"node_get_fsm_rejected"`  // 被过载保护主动拒绝的GET FSM数量
		PutRejectedNum int `json:"node_put_fsm_rejected"`  // 被过载保护主动拒绝的PUT FSM数量
	}
	var items CheckItems
	if err = json.Unmarshal([]byte(resp), &items); err != nil {
		err = fmt.Errorf("unmarshall %s to %+v get an error:%s", resp, items, err.Error())
		slog.Error(err.Error())
		return "", err
	}
	var errList []string
	if items.GetTime > 300000 {
		errList = append(errList, fmt.Sprintf("get response time over than 0.3s"))
	}
	if items.PutTime > 500000 {
		errList = append(errList, fmt.Sprintf("put response time over than 0.5s"))
	}
	if items.GetRejectedNum > 0 {
		errList = append(errList, fmt.Sprintf("overload protection, get was rejected"))
	}
	if items.PutRejectedNum > 0 {
		errList = append(errList, fmt.Sprintf("overload protection, put was rejected"))
	}
	if len(errList) > 0 {
		return "", fmt.Errorf(strings.Join(errList, ","))
	}
	return "", nil
}
