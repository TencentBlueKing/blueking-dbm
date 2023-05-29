package manage

import (
	"dbm-services/common/db-resource/internal/controller"
	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"fmt"

	rf "github.com/gin-gonic/gin"
)

// LableHandler TODO
type LableHandler struct {
	controller.BaseHandler
}

// LableEditInput TODO
type LableEditInput struct {
	BkHostIds []int             `json:"bk_host_ids"  binding:"required"`
	Labels    map[string]string `json:"labels"`
}

// Edit TODO
func (c *LableHandler) Edit(r *rf.Context) {
	var input LableEditInput
	if err := c.Prepare(r, &input); err != nil {
		logger.Error(fmt.Sprintf("Preare Error %s", err.Error()))
		return
	}
	requestId := r.GetString("request_id")
	lableJson, err := cmutil.ConverMapToJsonStr(cmutil.CleanStrMap(input.Labels))
	if err != nil {
		logger.Error(fmt.Sprintf("ConverLableToJsonStr Failed,Error:%s", err.Error()))
		c.SendResponse(r, err, nil, requestId)
		return
	}
	if len(input.BkHostIds) <= 0 {
		c.SendResponse(r, nil, nil, requestId)
		return
	}
	err = model.DB.Self.Table(model.TbRpDetailName()).Where("bk_host_id in ? ", input.BkHostIds).Update("label",
		lableJson).
		Error
	if err != nil {
		logger.Error(fmt.Sprintf("Update Lable Failed %s", err.Error()))
		c.SendResponse(r, err, nil, requestId)
		return
	}
	c.SendResponse(r, nil, nil, requestId)
}
