package handler

import (
	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/priv-service/service"
	"encoding/json"
	"io/ioutil"

	"github.com/gin-gonic/gin"
	"golang.org/x/exp/slog"
)

// GetPassword 查询用户的密码
func (m *PrivService) GetPassword(c *gin.Context) {
	slog.Info("do GetPassword!")
	var input service.GetPasswordPara
	body, err := ioutil.ReadAll(c.Request.Body)
	if err != nil {
		slog.Error("msg", err)
		SendResponse(c, errno.ErrBind, err)
		return
	}
	if err = json.Unmarshal(body, &input); err != nil {
		slog.Error("msg", err)
		SendResponse(c, errno.ErrBind, err)
		return
	}
	batch, count, err := input.GetPassword()
	if err != nil {
		slog.Error(err.Error())
		SendResponse(c, err, nil)
		return
	}
	SendResponse(c, err, ListResponse{
		Count: int64(count),
		Items: batch,
	})
	return
}

// ModifyPassword 新增或者修改密码
func (m *PrivService) ModifyPassword(c *gin.Context) {
	slog.Info("do ModifyPassword!")
	var input service.ModifyPasswordPara
	body, err := ioutil.ReadAll(c.Request.Body)
	if err != nil {
		slog.Error("msg", err)
		SendResponse(c, errno.ErrBind, err)
		return
	}
	if err = json.Unmarshal(body, &input); err != nil {
		slog.Error("msg", err)
		SendResponse(c, errno.ErrBind, err)
		return
	}
	err = input.ModifyPassword()
	SendResponse(c, err, nil)
	return
}

// DeletePassword 删除密码
func (m *PrivService) DeletePassword(c *gin.Context) {
	slog.Info("do DeletePassword!")
	var input service.GetPasswordPara
	body, err := ioutil.ReadAll(c.Request.Body)
	if err != nil {
		slog.Error("msg", err)
		SendResponse(c, errno.ErrBind, err)
		return
	}
	if err = json.Unmarshal(body, &input); err != nil {
		slog.Error("msg", err)
		SendResponse(c, errno.ErrBind, err)
		return
	}
	err = input.DeletePassword()
	SendResponse(c, err, nil)
	return
}

// GetMysqlAdminPassword 查询ysql实例中管理用户的密码
func (m *PrivService) GetMysqlAdminPassword(c *gin.Context) {
	slog.Info("do GetMysqlAdminPassword!")
	var input service.GetAdminUserPasswordPara
	body, err := ioutil.ReadAll(c.Request.Body)
	if err != nil {
		slog.Error("msg", err)
		SendResponse(c, errno.ErrBind, err)
		return
	}
	if err = json.Unmarshal(body, &input); err != nil {
		slog.Error("msg", err)
		SendResponse(c, errno.ErrBind, err)
		return
	}
	batch, count, err := input.GetMysqlAdminPassword()
	if err != nil {
		slog.Error(err.Error())
		SendResponse(c, err, nil)
		return
	}
	SendResponse(c, err, ListResponse{
		Count: int64(count),
		Items: batch,
	})
	return
}

// ModifyMysqlAdminPassword 新增或者修改mysql实例中管理用户的密码，可用于随机化密码
func (m *PrivService) ModifyMysqlAdminPassword(c *gin.Context) {
	slog.Info("do ModifyMysqlAdminPassword!")
	var input service.ModifyAdminUserPasswordPara

	body, err := ioutil.ReadAll(c.Request.Body)
	if err != nil {
		slog.Error("msg", err)
		SendResponse(c, errno.ErrBind, err)
		return
	}

	if err = json.Unmarshal(body, &input); err != nil {
		slog.Error("msg", err)
		SendResponse(c, errno.ErrBind, err)
		return
	}
	// 随机化定时任务异步返回，避免占用资源
	if input.Async == true {
		SendResponse(c, nil, nil)
	}
	// 前端页面调用等同步返回，返回修改成功的实例以及没有修改成功的实例
	batch, err := input.ModifyMysqlAdminPassword()
	if input.Async == false {
		SendResponse(c, err, batch)
	}
	return
}

func (m *PrivService) MigratePlatformPassword(c *gin.Context) {
	slog.Info("do MigratePlatformPassword!")
	var input service.PlatformPara
	body, err := ioutil.ReadAll(c.Request.Body)
	if err != nil {
		slog.Error("msg", err)
		SendResponse(c, errno.ErrBind, err)
		return
	}
	if err = json.Unmarshal(body, &input); err != nil {
		slog.Error("msg", err)
		SendResponse(c, errno.ErrBind, err)
		return
	}
	err = input.MigratePlatformPassword()
	if err != nil {
		slog.Error("msg", "MigratePlatformPassword", err)
	}
	SendResponse(c, err, nil)
	return
}
