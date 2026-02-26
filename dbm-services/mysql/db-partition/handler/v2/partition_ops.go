// Package v2 分区 v2 版本 HTTP 处理器：创建 / 更新 / 删除 / 启用 / 禁用
package v2

import (
	"fmt"
	"log/slog"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/db-partition/handler"
	"dbm-services/mysql/db-partition/service"
	servicev2 "dbm-services/mysql/db-partition/service/v2"

	"github.com/gin-gonic/gin"
)

// CreateConf v2 创建分区配置 /partition/v2/create_conf
func CreateConf(c *gin.Context) {
	var input service.CreatePartitionsInput
	if err := c.ShouldBind(&input); err != nil {
		err = errno.ErrReadEntity.Add(err.Error())
		slog.Error(err.Error())
		handler.SendResponse(c, err, nil)
		return
	}
	slog.Info("v2 create_conf",
		"bk_biz_id", input.BkBizId,
		"db_app_abbr", input.DbAppAbbr,
		"immute_domain", input.ImmuteDomain,
		"creator", input.Creator)

	err, configs := servicev2.CreatePartitionsConfig(&input)
	if err != nil {
		slog.Error(err.Error())
		handler.SendResponse(c, fmt.Errorf("添加分区配置失败!%s", err.Error()), nil)
		return
	}

	// 返回完整的分区配置信息（每条记录中已包含 config_id）
	resp := struct {
		Items []service.PartitionConfig `json:"items"`
		Info  string                    `json:"info"`
	}{
		Items: configs,
		Info:  "分区配置信息创建成功！",
	}
	handler.SendResponse(c, nil, resp)
}

// UpdateConf v2 更新分区配置 /partition/v2/update_conf
func UpdateConf(c *gin.Context) {
	var input service.CreatePartitionsInput
	if err := c.ShouldBind(&input); err != nil {
		err = errno.ErrReadEntity.Add(err.Error())
		slog.Error(err.Error())
		handler.SendResponse(c, err, nil)
		return
	}
	slog.Info("v2 update_conf",
		"bk_biz_id", input.BkBizId,
		"immute_domain", input.ImmuteDomain,
		"updator", input.Updator)

	err, configs := servicev2.UpdatePartitionsConfig(&input)
	if err != nil {
		slog.Error(err.Error())
		handler.SendResponse(c, fmt.Errorf("更新分区配置失败!%s", err.Error()), nil)
		return
	}

	resp := struct {
		Items []service.PartitionConfig `json:"items"`
		Info  string                    `json:"info"`
	}{
		Items: configs,
		Info:  "更新分区配置信息成功！",
	}
	handler.SendResponse(c, nil, resp)
}

// DelConf v2 删除分区配置 /partition/v2/del_conf
func DelConf(c *gin.Context) {
	var input service.DeletePartitionConfigByIds
	if err := c.ShouldBind(&input); err != nil {
		err = errno.ErrReadEntity.Add(err.Error())
		slog.Error(err.Error())
		handler.SendResponse(c, err, nil)
		return
	}
	slog.Info("v2 del_conf",
		"bk_biz_id", input.BkBizId,
		"ids", input.Ids)

	if err := servicev2.DeletePartitionsConfig(&input); err != nil {
		slog.Error(err.Error())
		handler.SendResponse(c, err, nil)
		return
	}
	handler.SendResponse(c, nil, "分区配置信息删除成功！")
}

// DisablePartition v2 禁用分区 /partition/v2/disable_partition
func DisablePartition(c *gin.Context) {
	var input service.DisablePartitionInput
	if err := c.ShouldBind(&input); err != nil {
		err = errno.ErrReadEntity.Add(err.Error())
		slog.Error(err.Error())
		handler.SendResponse(c, err, nil)
		return
	}
	slog.Info("v2 disable_partition",
		"ids", input.Ids,
		"operator", input.Operator)

	if err := servicev2.DisablePartition(&input); err != nil {
		slog.Error(err.Error())
		handler.SendResponse(c, fmt.Errorf("分区禁用失败!%s", err.Error()), nil)
		return
	}
	handler.SendResponse(c, nil, "分区禁用成功！")
}

// EnablePartition v2 启用分区 /partition/v2/enable_partition
func EnablePartition(c *gin.Context) {
	var input service.EnablePartitionInput
	if err := c.ShouldBind(&input); err != nil {
		err = errno.ErrReadEntity.Add(err.Error())
		slog.Error(err.Error())
		handler.SendResponse(c, err, nil)
		return
	}
	slog.Info("v2 enable_partition",
		"ids", input.Ids,
		"operator", input.Operator)

	if err := servicev2.EnablePartition(&input); err != nil {
		slog.Error(err.Error())
		handler.SendResponse(c, fmt.Errorf("分区启用失败!%s", err.Error()), nil)
		return
	}
	handler.SendResponse(c, nil, "分区启用成功！")
}
