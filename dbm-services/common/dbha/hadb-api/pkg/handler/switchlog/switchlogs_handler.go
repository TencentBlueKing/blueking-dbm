package switchlog

import (
	"encoding/json"
	"fmt"
	"time"

	"dbm-services/common/dbha/hadb-api/log"
	"dbm-services/common/dbha/hadb-api/model"
	"dbm-services/common/dbha/hadb-api/pkg/api"

	"github.com/valyala/fasthttp"
)

const (
	// PutLog TODO
	PutLog = "insert_switch_log"
	// GetLog TODO
	GetLog = "query_switch_log"
)

// SwitchLogsApi TODO
type SwitchLogsApi struct {
	UID      int64  `json:"uid"`
	SwitchID int64  `json:"sw_id"`
	App      string `json:"app"`
	IP       string `json:"ip"`
	Result   string `json:"result"`
	Datetime string `json:"datetime,omitempty"`
	Comment  string `json:"comment"`
	Port     int    `json:"port"`
}

// Handler TODO
func Handler(ctx *fasthttp.RequestCtx) {
	param := &api.RequestInfo{}
	if err := json.Unmarshal(ctx.PostBody(), param); err != nil {
		log.Logger.Errorf("parse request body failed:%s", err.Error())
		api.SendResponse(ctx, api.ResponseInfo{
			Data:    nil,
			Code:    api.RespErr,
			Message: err.Error(),
		})
		return
	}
	switch param.Name {
	case GetLog:
		GetSwitchLogs(ctx, param.QueryArgs)
	case PutLog:
		PutSwitchLogs(ctx, param.SetArgs)
	default:
		api.SendResponse(ctx, api.ResponseInfo{
			Data:    nil,
			Code:    api.RespErr,
			Message: fmt.Sprintf("unknown api name[%s]", param.Name),
		})
	}
}

// GetSwitchLogs TODO
func GetSwitchLogs(ctx *fasthttp.RequestCtx, param interface{}) {
	var (
		result    = []model.HASwitchLogs{}
		whereCond = &model.HASwitchLogs{}
		response  = api.ResponseInfo{
			Data:    nil,
			Code:    api.RespOK,
			Message: "",
		}
	)
	// NB:couldn't user api.SendResponse(ctx, response) directly, otherwise
	// deepCopy response first
	defer func() { api.SendResponse(ctx, response) }()

	if !ctx.IsPost() {
		response.Message = "must be POST request"
		response.Code = api.RespErr
		log.Logger.Errorf("must by post request, param:%+v", param)
		return
	}

	if bytes, err := json.Marshal(param); err != nil {
		log.Logger.Errorf("convert param failed:%s", err.Error())
		response.Code = api.RespErr
		response.Message = err.Error()
		return
	} else {
		if err = json.Unmarshal(bytes, whereCond); err != nil {
			response.Code = api.RespErr
			response.Message = err.Error()
			return
		}
	}
	log.Logger.Debugf("%+v", whereCond)

	db := model.HADB.Self.Table(whereCond.TableName())
	if whereCond.App != "" {
		db = db.Where("app = ?", whereCond.App)
	}

	if whereCond.SwitchID > 0 {
		db = db.Where("sw_id = ?", whereCond.SwitchID)
	}

	if err := db.Order("uid DESC").Find(&result).Error; err != nil {
		response.Code = api.RespErr
		response.Message = err.Error()
		response.Data = nil
		log.Logger.Errorf("query table failed:%s", err.Error())
	}

	response.Data = TransSwitchLogsToApi(result)
	log.Logger.Debugf("%+v", result)
	log.Logger.Debugf("apiResult:%v", response.Data)
}

// PutSwitchLogs TODO
func PutSwitchLogs(ctx *fasthttp.RequestCtx, setParam interface{}) {
	input := &model.HASwitchLogs{}
	response := api.ResponseInfo{
		Data:    nil,
		Code:    api.RespOK,
		Message: "",
	}
	defer func() { api.SendResponse(ctx, response) }()

	if !ctx.IsPost() {
		response.Code = api.RespErr
		response.Message = "must be post method"
		return
	}
	// convert setParam
	if bytes, err := json.Marshal(setParam); err != nil {
		log.Logger.Errorf("convert param failed:%s", err.Error())
		response.Code = api.RespErr
		response.Message = err.Error()
		return
	} else {
		if err = json.Unmarshal(bytes, input); err != nil {
			response.Code = api.RespErr
			response.Message = err.Error()
			return
		}
	}

	db := model.HADB.Self.Table(input.TableName()).Create(input)
	if err := db.Error; err != nil {
		response.Code = api.RespErr
		response.Message = err.Error()
		response.Data = nil
		log.Logger.Errorf("insert table failed:%s", err.Error())
		return
	}

	response.Data = map[string]interface{}{api.RowsAffect: db.RowsAffected}
}

// TransSwitchLogsToApi TODO
func TransSwitchLogsToApi(result []model.HASwitchLogs) []SwitchLogsApi {
	apiResult := make([]SwitchLogsApi, 0)
	loc, _ := time.LoadLocation("Asia/Shanghai")
	for _, log := range result {
		logApi := SwitchLogsApi{
			UID:      log.UID,
			SwitchID: log.SwitchID,
			App:      log.App,
			IP:       log.IP,
			Result:   log.Result,
			Datetime: log.Datetime.In(loc).Format("2006-01-02T15:04:05-07:00"),
			Comment:  log.Comment,
			Port:     log.Port,
		}
		apiResult = append(apiResult, logApi)
	}
	return apiResult
}
