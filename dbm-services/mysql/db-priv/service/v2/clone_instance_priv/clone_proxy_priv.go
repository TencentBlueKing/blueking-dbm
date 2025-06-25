package clone_instance_priv

import (
	"dbm-services/mysql/priv-service/service/v2/clone_instance_priv/internal/proxy"
	"fmt"
)

func (c *CloneInstancePrivPara) cloneProxyPriv() error {
	userList, err := proxy.QueryUserList(*c.BkCloudId, c.Source.Address, c.logger)
	if err != nil {
		c.logger.Error(
			fmt.Sprintf("query user list failed, address: %s, err: %s", c.Source.Address, err.Error()),
		)
		return err
	}

	c.logger.Info(
		fmt.Sprintf("query proxy user list, users count: %d", len(userList)),
	)
	// ToDo 这里想加一个正确性验证, 把非法的白名单排除掉, 就可以慢慢纠正白名单的诡异错误

	err = proxy.ImportUserList(*c.BkCloudId, c.Target.Address, userList, c.logger)
	if err != nil {
		c.logger.Info(
			fmt.Sprintf("import proxy user list, address: %s, err: %s", c.Source.Address, err.Error()),
		)
		return err
	}

	c.logger.Info("clone proxy users import finish")
	return nil
}
