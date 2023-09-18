package checkringstatus

import (
	"dbm-services/riak/db-tools/riak-monitor/pkg/internal/cst"
	"dbm-services/riak/db-tools/riak-monitor/pkg/utils"
	"fmt"
	"regexp"
	"strings"

	"golang.org/x/exp/slog"
)

func CheckRingStatus() (string, error) {
	cmd := fmt.Sprintf("%s ringready", cst.RiakAdminPath)
	resp, err := utils.ExecShellCommand(false, cmd)
	if err != nil {
		// 这个检查项是在此riak节点运行时，执行集群ring检查，发现其他异常节点；如果此节点异常，检查联通性时可探测到
		if strings.Contains(err.Error(), "Node did not respond to ping!") {
			slog.Warn(fmt.Sprintf("execute [ %s ] error: %s.", cmd, err.Error()))
		} else if strings.Contains(resp, "FALSE") {
			// FALSE ['riak@xxx','riak@xxx'] down.  All nodes need to be up to check.
			slog.Error(resp)
			re := regexp.MustCompile(`\[[^[]*\] down`)
			matchArr := re.FindStringSubmatch(resp)
			if len(matchArr) == 1 {
				return "", fmt.Errorf(matchArr[0])
			} else {
				return "", fmt.Errorf(resp)
			}
		} else {
			errInfo := fmt.Sprintf("execute [ %s ] error: %s", cmd, err.Error())
			slog.Error(errInfo)
			return "", fmt.Errorf(errInfo)
		}
	}
	return "", nil
}
