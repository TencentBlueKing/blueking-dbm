package middleware

import (
	"fmt"
	"k8s-dbs/common/api"
	"k8s-dbs/common/constant"
	commconst "k8s-dbs/common/constant"
	"k8s-dbs/common/util"
	apierrors "k8s-dbs/errors"
	metaentity "k8s-dbs/metadata/entity"
	metaprovider "k8s-dbs/metadata/provider"
	"log/slog"

	"github.com/gin-gonic/gin"
)

// APIAuthMiddleware API权限校验中间件
func APIAuthMiddleware(provider metaprovider.AuthUserRoleProvider) gin.HandlerFunc {
	return func(c *gin.Context) {
		// 获取请求路径
		path := c.FullPath()
		method := c.Request.Method
		// 获取当前Api名称
		apiName := constant.GetAPIURL(path)

		if (apiName == "") || (apiName != "" && method == "GET") {
			return
		}

		reqBody := ParseReqBody(c)
		// 没有请求体
		if len(reqBody) == 0 {
			api.ErrorResponse(c, apierrors.NewK8sDbsError(apierrors.ParameterInvalidError, fmt.Errorf("request body不能为空")))
			c.Abort()
			return
		}

		requestMap, err := util.JSONStrToMap(string(reqBody))
		if err != nil {
			slog.Warn("failed to parse request body to map", "error", err)
			api.ErrorResponse(c, apierrors.NewK8sDbsError(apierrors.ParameterInvalidError, fmt.Errorf("request body格式错误")))
			c.Abort()
			return
		}

		userName := requestMap["bk_username"]
		// 没有用户名
		if userName == nil {
			api.ErrorResponse(c, apierrors.NewK8sDbsError(apierrors.ParameterInvalidError, fmt.Errorf("请求参数中缺少bk_username字段")))
			c.Abort()
			return
		}

		params := metaentity.AuthUserRoleQueryParams{
			UserID: userName.(string),
			RoleID: commconst.AdminUserAuthRoleID,
		}

		ok := provider.CheckUserRole(params)
		// 没有权限
		if !ok {
			api.ErrorResponse(c, apierrors.NewK8sDbsError(apierrors.NotPermissionError, fmt.Errorf("您没有当前操作的权限")))
			c.Abort()
			return
		}

	}
}
