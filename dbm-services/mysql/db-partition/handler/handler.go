// Package handler TODO
package handler

import (
	"errors"
	"fmt"
	"net/http"
	_ "runtime/debug" // debug TODO

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/db-partition/service"

	"github.com/gin-gonic/gin"
	"golang.org/x/exp/slog"
)

// DryRun TODO
func DryRun(r *gin.Context) {
	fmt.Println("do DryRun!")
	var input service.Checker
	if err := r.ShouldBind(&input); err != nil {
		slog.Error("msg", err)
		SendResponse(r, errno.ErrBind, nil)
		return
	}
	sqls, err := input.DryRun()
	SendResponse(r, err, sqls)
	return

}

// GetPartitionsConfig TODO
func GetPartitionsConfig(r *gin.Context) {
	var input service.QueryParititionsInput
	if err := r.ShouldBind(&input); err != nil {
		slog.Error(err.Error())
		SendResponse(r, errno.ErrBind, nil)
		return
	}
	slog.Info(fmt.Sprintf("bk_biz_id: %d, immute_domains: %s", input.BkBizId, input.ImmuteDomains))
	lists, count, err := input.GetPartitionsConfig()
	// ListResponse 返回信息
	type ListResponse struct {
		Count int64       `json:"count"`
		Items interface{} `json:"items"`
	}
	if err != nil {
		slog.Error(err.Error())
		SendResponse(r, err, nil)
		return
	}
	SendResponse(r, err, ListResponse{
		Count: count,
		Items: lists,
	})
	return
}

// GetPartitionLog TODO
func GetPartitionLog(r *gin.Context) {
	var input service.QueryLogInput
	if err := r.ShouldBind(&input); err != nil {
		slog.Error(err.Error())
		SendResponse(r, errno.ErrBind, nil)
		return
	}
	lists, count, err := input.GetPartitionLog()
	// ListResponse 返回信息
	type ListResponse struct {
		Count int64       `json:"count"`
		Items interface{} `json:"items"`
	}
	if err != nil {
		slog.Error(err.Error())
		SendResponse(r, err, nil)
		return
	}
	SendResponse(r, err, ListResponse{
		Count: count,
		Items: lists,
	})
	return
}

// DeletePartitionsConfig TODO
func DeletePartitionsConfig(r *gin.Context) {
	var input service.DeletePartitionConfigByIds
	if err := r.ShouldBind(&input); err != nil {
		err = errno.ErrReadEntity.Add(err.Error())
		slog.Error(err.Error())
		SendResponse(r, err, nil)
		return
	}
	slog.Info(fmt.Sprintf("bk_biz_id: %d, ids: %v", input.BkBizId, input.Ids))
	err := input.DeletePartitionsConfig()
	if err != nil {
		slog.Error(err.Error())
		SendResponse(r, err, nil)
		return
	}
	SendResponse(r, err, "分区配置信息删除成功！")
	return
}

// CreatePartitionsConfig TODO
func CreatePartitionsConfig(r *gin.Context) {
	var input service.CreatePartitionsInput
	if err := r.ShouldBind(&input); err != nil {
		err = errno.ErrReadEntity.Add(err.Error())
		slog.Error(err.Error())
		SendResponse(r, err, nil)
		return
	}
	slog.Info(fmt.Sprintf("bk_biz_id: %d, immute_domain: %s, creator: %s", input.BkBizId, input.ImmuteDomain,
		input.Creator))
	err, configIDs := input.CreatePartitionsConfig()
	if err != nil {
		slog.Error(err.Error())
		SendResponse(r, errors.New(fmt.Sprintf("添加分区配置失败!%s", err.Error())), nil)
		return
	}
	// 注意这里内部变量需要首字母大写，不然后面json无法访问
	data := struct {
		ConfigIDs []int  `json:"config_ids"`
		Info      string `json:"info"`
	}{configIDs, "分区配置信息创建成功！"}
	SendResponse(r, nil, data)
	return
}

// DisablePartition TODO
func DisablePartition(r *gin.Context) {
	var input service.DisablePartitionInput
	if err := r.ShouldBind(&input); err != nil {
		err = errno.ErrReadEntity.Add(err.Error())
		slog.Error(err.Error())
		SendResponse(r, err, nil)
		return
	}
	slog.Info(fmt.Sprintf("ids: %v, operator: %s", input.Ids, input.Operator))
	err := input.DisablePartitionConfig()
	if err != nil {
		slog.Error(err.Error())
		SendResponse(r, errors.New(fmt.Sprintf("分区禁用失败!%s", err.Error())), nil)
		return
	}
	SendResponse(r, nil, "分区禁用成功！")
	return
}

// EnablePartition TODO
func EnablePartition(r *gin.Context) {
	var input service.EnablePartitionInput
	if err := r.ShouldBind(&input); err != nil {
		err = errno.ErrReadEntity.Add(err.Error())
		slog.Error(err.Error())
		SendResponse(r, err, nil)
		return
	}
	slog.Info(fmt.Sprintf("ids: %v, operator: %s", input.Ids, input.Operator))
	err := input.EnablePartitionConfig()
	if err != nil {
		slog.Error(err.Error())
		SendResponse(r, errors.New(fmt.Sprintf("分区启用失败!%s", err.Error())), nil)
		return
	}
	SendResponse(r, nil, "分区启用成功！")
	return
}

// UpdatePartitionsConfig TODO
func UpdatePartitionsConfig(r *gin.Context) {
	var input service.CreatePartitionsInput
	if err := r.ShouldBind(&input); err != nil {
		err = errno.ErrReadEntity.Add(err.Error())
		slog.Error(err.Error())
		SendResponse(r, err, nil)
		return
	}
	slog.Info(fmt.Sprintf("bk_biz_id: %d, immute_domain: %s, creator: %s", input.BkBizId, input.ImmuteDomain,
		input.Creator))
	err := input.UpdatePartitionsConfig()
	if err != nil {
		slog.Error(err.Error())
		SendResponse(r, errors.New(fmt.Sprintf("更新分区配置失败!%s", err.Error())), nil)
		return
	}
	SendResponse(r, nil, "更新分区配置信息创建成功！")
	return
}

// Response TODO
type Response struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data"`
}

// SendResponse TODO
func SendResponse(r *gin.Context, err error, data interface{}) {
	code, message := errno.DecodeErr(err)
	dataErr, ok := data.(error)
	if ok {
		message += dataErr.Error()
	}
	// always return http.StatusOK
	r.JSON(http.StatusOK, Response{
		Code:    code,
		Message: message,
		Data:    data,
	})
}
