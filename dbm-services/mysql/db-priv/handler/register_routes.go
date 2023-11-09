package handler

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

// PrivService Mysql 权限服务
type PrivService struct{}

/*
		a.账号规则：（1）账号+密码；（2）访问db+权限
		b."业务+账号+访问db" 唯一
		c.账号规则的数据库可以为db%或者db1,不可以用符号连接写成"db%,test"
		d.账号规则可以增删改查，不影响mysql实例中的授权
	    e.应用账号规则（执行授权）,原则:不影响已有账号的db范围以及密码,授权提单时做检查：如果实例存在此账号,不论是单点还是主从模式,规则中的密码要与已有账号密码一致，规则中的db范围与已有db范围不能有包含关系,权限可不一致
*/

// Routes 服务接口清单
func (m *PrivService) Routes() []*gin.RouteInfo {
	return []*gin.RouteInfo{
		// 账号
		{Method: http.MethodPost, Path: "add_account", HandlerFunc: m.AddAccount},
		{Method: http.MethodPost, Path: "get_account", HandlerFunc: m.GetAccount},
		{Method: http.MethodPost, Path: "modify_account", HandlerFunc: m.ModifyAccount},
		{Method: http.MethodPost, Path: "delete_account", HandlerFunc: m.DeleteAccount},

		// 账号规则
		{Method: http.MethodPost, Path: "get_account_rule_list", HandlerFunc: m.GetAccountRuleList},
		{Method: http.MethodPost, Path: "add_account_rule", HandlerFunc: m.AddAccountRule},
		{Method: http.MethodPost, Path: "delete_account_rule", HandlerFunc: m.DeleteAccountRule},
		{Method: http.MethodPost, Path: "modify_account_rule", HandlerFunc: m.ModifyAccountRule},

		// 授权
		{Method: http.MethodPost, Path: "add_priv_dry_run", HandlerFunc: m.AddPrivDryRun},
		{Method: http.MethodPost, Path: "add_priv", HandlerFunc: m.AddPriv},
		{Method: http.MethodPost, Path: "add_priv_without_account_rule", HandlerFunc: m.AddPrivWithoutAccountRule},

		// 实例间权限克隆
		{Method: http.MethodPost, Path: "clone_instance_priv_dry_run", HandlerFunc: m.CloneInstancePrivDryRun},
		{Method: http.MethodPost, Path: "clone_instance_priv", HandlerFunc: m.CloneInstancePriv},

		// 客户端权限克隆
		{Method: http.MethodPost, Path: "clone_client_priv_dry_run", HandlerFunc: m.CloneClientPrivDryRun},
		{Method: http.MethodPost, Path: "clone_client_priv", HandlerFunc: m.CloneClientPriv},

		// 获取公钥，用于传输过程中加密密码
		{Method: http.MethodPost, Path: "pub_key", HandlerFunc: m.GetPubKey},
	}
}

// RegisterRoutes 注册服务
func RegisterRoutes(router *gin.Engine, group string, routesInfo []*gin.RouteInfo) {
	r := router.Group(group)
	for _, route := range routesInfo {
		r.Handle(route.Method, route.Path, route.HandlerFunc)
	}
}
