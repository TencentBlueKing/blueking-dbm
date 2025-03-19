package clone_instance_priv

import (
	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/priv-service/service/v2/internal"
	"log/slog"
)

func (c *CloneInstancePrivPara) CloneInstancePriv(jsonPara string, ticket string) error {
	c.logger.Info(
		"",
		slog.String("jsonPara", jsonPara),
	)

	/*
		ToDo 实例类型检查
	*/
	if c.Source.Address == "" || c.Target.Address == "" {
		return errno.ClonePrivilegesFail.Add("source address or target address is empty")
	}

	if c.Source.Address == c.Target.Address {
		return errno.ClonePrivilegesFail.Add("source address or target address is the same")
	}

	c.logger.Info(
		"",
		slog.Any("system users", c.SystemUsers),
		slog.String("machine type", c.Source.MachineType),
	)

	if c.Source.MachineType == internal.MachineTypeProxy {
		return c.cloneProxyPriv()
	} else if c.Source.MachineType == internal.MachineTypeSpider {
		return c.cloneMySQLPriv(false)
	} else {
		return c.cloneMySQLPriv(true)
	}
}

/*
输入检查
1. machine type 要相等
2. 如果是 backend 或者 remote 时, source version <= target version
*/
func (c *CloneInstancePrivPara) validate() error {
	return nil
}
