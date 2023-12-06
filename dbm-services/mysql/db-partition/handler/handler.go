// Package handler TODO
package handler

import (
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	_ "runtime/debug" // debug TODO
	"strconv"
	"strings"
	"time"

	"dbm-services/mysql/db-partition/cron"

	cron_pkg "github.com/robfig/cron/v3"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/db-partition/service"

	"github.com/gin-gonic/gin"
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

// DeletePartitionsConfigByCluster TODO
func DeletePartitionsConfigByCluster(r *gin.Context) {
	// 集群下架时，通过cluster_id来删除相关分区配置
	var input service.DeletePartitionConfigByClusterIds
	if err := r.ShouldBind(&input); err != nil {
		err = errno.ErrReadEntity.Add(err.Error())
		slog.Error(err.Error())
		SendResponse(r, err, nil)
		return
	}
	slog.Info(fmt.Sprintf("bk_biz_id: %d, cluster_ids: %v", input.BkBizId, input.ClusterIds))
	err, info := input.DeletePartitionsConfigByCluster()

	if err != nil {
		slog.Error(err.Error())
		SendResponse(r, err, nil)
		return
	}
	SendResponse(r, err, info)
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

// CreatePartitionLog 用于创建分区后马上执行分区规则，将执行单据的信息记录到日志表中
func CreatePartitionLog(r *gin.Context) {
	var input service.CreatePartitionCronLog
	err := r.ShouldBind(&input)
	if err != nil {
		err = errno.ErrReadEntity.Add(err.Error())
		slog.Error(err.Error())
		SendResponse(r, err, nil)
		return
	}
	// 计算单据处于集群时区的日期
	offsetStr := strings.Split(input.TimeZone, ":")[0]
	offset, _ := strconv.Atoi(offsetStr)
	offetSeconds := offset * 60 * 60
	name := fmt.Sprintf("UTC%s", offsetStr)
	zone := time.FixedZone(name, offetSeconds)
	date := time.Now().In(zone).Format("20060102")
	err = service.AddLog(input.ConfigId, input.BkBizId, input.ClusterId, input.BkCloudId, input.TicketId,
		input.ImmuteDomain, input.TimeZone, date, "from_ticket", "",
		service.ExecuteAsynchronous, input.ClusterType)
	if err != nil {
		slog.Error(err.Error())
		SendResponse(r, err, nil)
		return
	}
	SendResponse(r, nil, "插入分区日志成功")
	return
}

// CronEntries 查询定时任务
func CronEntries(r *gin.Context) {
	var entries []cron_pkg.Entry
	for _, v := range cron.CronList {
		entries = append(entries, v.Entries()...)
	}
	slog.Info("msg", "entries", entries)
	SendResponse(r, nil, entries)
	return
}

// CronStop 关闭分区定时任务
func CronStop(r *gin.Context) {
	for _, v := range cron.CronList {
		v.Stop()
	}
	SendResponse(r, nil, "关闭分区定时任务成功")
	return
}

// CronStart 开启分区定时任务
func CronStart(r *gin.Context) {
	for _, v := range cron.CronList {
		v.Start()
	}
	SendResponse(r, nil, "开启分区定时任务成功")
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
