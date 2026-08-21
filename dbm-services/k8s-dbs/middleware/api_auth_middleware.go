// Package middleware 提供 API 路由中间件实现
package middleware

import (
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"strconv"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/tidwall/gjson"

	"k8s-dbs/common/api"
	"k8s-dbs/common/constant"
	apierrors "k8s-dbs/errors"
	infresp "k8s-dbs/infrastructure/response"
	"k8s-dbs/infrastructure/thirdapi"
)

// iamChecker 抽象 IAM 鉴权操作
type iamChecker interface {
	// SimpleCheckAllowed 调用 DBM simple_check_allowed 做鉴权。
	// bkAppCode/bkAppSecret 由实现方从环境变量 INNER_BK_APP_CODE / INNER_BK_APP_SECRET 获取。
	// 返回：allowed, applyData（无权限时非 nil）, err
	SimpleCheckAllowed(username, actionID string, bkBizID int, resourceID string) (bool, *infresp.ApplyData, error)
}

const iamExemptStorageWhitelistEnv = "K8S_DBS_IAM_EXEMPT_STORAGE_WHITELIST"

// APIAuthMiddleware API 权限校验中间件（调用 DBM IAM 接口做细粒度鉴权）
func APIAuthMiddleware() gin.HandlerFunc {
	resolver := NewDBClusterTypeResolver()
	return apiAuthMiddlewareWithDeps(thirdapi.GetDbmAPIService(), resolver)
}

// apiAuthMiddlewareWithDeps 接受 checker、resolver 接口，供测试注入 mock
func apiAuthMiddlewareWithDeps(checker iamChecker, resolver ClusterTypeResolver) gin.HandlerFunc {
	return func(c *gin.Context) {
		path := c.FullPath()
		method := c.Request.Method
		apiName := constant.GetAPIName(path)

		if apiName == "" || method == http.MethodGet {
			c.Next()
			return
		}

		reqBody := ParseReqBody(c)
		if len(reqBody) == 0 {
			api.ErrorResponse(c, apierrors.NewK8sDbsError(
				apierrors.ParameterInvalidError, fmt.Errorf("request body不能为空")))
			c.Abort()
			return
		}

		// 使用 gjson 验证 JSON 格式并按需提取字段，不再全量反序列化
		if !gjson.ValidBytes(reqBody) {
			slog.Warn("failed to parse request body: invalid JSON")
			api.ErrorResponse(c, apierrors.NewK8sDbsError(
				apierrors.ParameterInvalidError, fmt.Errorf("request body格式错误")))
			c.Abort()
			return
		}

		userName := gjson.GetBytes(reqBody, "bk_username").String()
		if userName == "" {
			slog.Warn("bk_username 缺失，拒绝请求", "api", apiName)
			api.ErrorResponse(c, apierrors.NewK8sDbsError(
				apierrors.ParameterInvalidError, fmt.Errorf("bk_username 不能为空")))
			c.Abort()
			return
		}

		allowed, applyData, authErr := checkIAMPermission(
			checker, resolver, apiName, reqBody, userName)
		if authErr != nil {
			if IsResolverError(authErr) {
				// 本地解析失败（DB 不可达、参数缺失、类型不匹配等）
				slog.Error("集群类型解析失败", "error", authErr, "user", userName, "api", apiName)
				api.ErrorResponse(c, apierrors.NewK8sDbsError(apierrors.ParameterInvalidError, authErr))
			} else {
				// IAM 远程调用失败
				slog.Error("IAM 鉴权失败", "error", authErr, "user", userName, "api", apiName)
				api.ErrorResponse(c, apierrors.NewK8sDbsError(apierrors.ThirdAPIError, authErr))
			}
			c.Abort()
			return
		}
		if !allowed {
			api.PermissionDeniedResponse(c, applyData)
			c.Abort()
			return
		}
		c.Next()
	}
}

// checkIAMPermission 调用 DBM SaaS 的 simple_check_allowed 做鉴权。
// DBM 负责实际的 IAM 查询和审计日志记录，k8s-dbs 只传递用户身份和操作上下文。
func checkIAMPermission(
	checker iamChecker,
	resolver ClusterTypeResolver,
	apiName string,
	rawJSON []byte,
	userName string,
) (allowed bool, applyData *infresp.ApplyData, err error) {
	actionTemplate, exists := constant.APIToIAMAction[apiName]
	if !exists {
		return true, nil, nil
	}

	// Addon 操作：固定 action_id，仅校验业务级权限，无需 resolver
	if isAddonAPI(apiName) {
		return checkAddonPermission(checker, actionTemplate, userName)
	}

	// 通过 resolver 自动推断集群类型（创建操作从请求体，非创建操作从 DB）
	result, resolveErr := resolver.Resolve(apiName, rawJSON)
	if resolveErr != nil {
		return false, nil, resolveErr
	}

	if isStorageIAMExempted(result.AddonType) {
		slog.Info("存储类型命中 IAM 鉴权豁免白名单，跳过权限检查",
			"addonType", result.AddonType, "api", apiName, "user", userName)
		return true, nil, nil
	}

	iamPrefix, ok := constant.ClusterTypeToIAMPrefix[result.ClusterType]
	if !ok {
		return false, nil, newResolverError("未知的集群类型: %s", result.ClusterType)
	}

	actionID := strings.Replace(actionTemplate, "{type}", iamPrefix, 1)

	var bkBizID int
	var resourceID string
	if apiName == constant.APIClusterCreate {
		bizID := gjsonFirstInt(rawJSON, "bkBizId", "basicInfo.bkBizId")
		if bizID <= 0 {
			return false, nil, newResolverError("bkBizId 缺失或无效")
		}
		bkBizID = int(bizID)
		resourceID = ""
	} else {
		if result.DbmClusterID <= 0 {
			clusterName := gjsonFirstString(rawJSON, "clusterName", "basicInfo.clusterName")
			slog.Error("本地 DbmClusterID 为 0，无法进行实例级鉴权",
				"cluster", clusterName, "api", apiName)
			return false, nil, newResolverError(
				"集群 %q 的 DBM 集群 ID 未就绪（本地记录为 0），无法进行实例级鉴权，"+
					"请检查集群同步状态或稍后重试", clusterName)
		}
		resourceID = fmt.Sprintf("%d", result.DbmClusterID)
		if bizID := gjsonFirstInt(rawJSON, "bkBizId", "basicInfo.bkBizId"); bizID > 0 {
			bkBizID = int(bizID)
		}
	}

	return checker.SimpleCheckAllowed(userName, actionID, bkBizID, resourceID)
}

// isStorageIAMExempted 判断 addonType 是否命中 IAM 鉴权豁免白名单。
// 白名单由 K8S_DBS_IAM_EXEMPT_STORAGE_WHITELIST 配置，逗号分隔，大小写不敏感。
// 未配置或解析后为空时，不启用豁免，保持原有鉴权行为。
func isStorageIAMExempted(addonType string) bool {
	whitelist := os.Getenv(iamExemptStorageWhitelistEnv)
	if whitelist == "" || addonType == "" {
		return false
	}

	target := strings.ToLower(strings.TrimSpace(addonType))
	if target == "" {
		return false
	}
	for _, item := range strings.Split(whitelist, ",") {
		if strings.ToLower(strings.TrimSpace(item)) == target {
			return true
		}
	}
	return false
}

// isAddonAPI 判断是否为 addon 管理操作。
// addon 操作作用于 K8s 集群级别（非存储实例级别），使用统一的 action_id。
func isAddonAPI(apiName string) bool {
	switch apiName {
	case constant.APIAddonInstall, constant.APIAddonUninstall, constant.APIAddonUpgrade:
		return true
	}
	return false
}

// checkAddonPermission addon 操作鉴权：固定 action_id = "k8s_addon_manage"，
// related_resource_types = [BUSINESS]，bk_biz_id 从环境变量 BKBASE_BK_BIZ_ID 读取。
func checkAddonPermission(
	checker iamChecker,
	actionID string,
	userName string,
) (bool, *infresp.ApplyData, error) {
	raw := os.Getenv("BKBASE_BK_BIZ_ID")
	if raw == "" {
		return false, nil, newResolverError("环境变量 BKBASE_BK_BIZ_ID 未配置")
	}
	bizID, err := strconv.Atoi(raw)
	if err != nil || bizID <= 0 {
		return false, nil, newResolverError("环境变量 BKBASE_BK_BIZ_ID 无效: %s", raw)
	}
	return checker.SimpleCheckAllowed(userName, actionID, bizID, "")
}
