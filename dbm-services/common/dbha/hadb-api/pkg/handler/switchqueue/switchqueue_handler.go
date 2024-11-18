package switchqueue

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
	// GetInsTotalSwitch query single ins switch total
	GetInsTotalSwitch = "query_single_total"
	// GetIpTotalSwitch query single ip switch total
	GetIpTotalSwitch = "query_interval_total"
	// GetIdcTotalSwitch query single idc switch total
	GetIdcTotalSwitch = "query_single_idc"
	// UpdateQueue TODO
	UpdateQueue = "update_switch_queue"
	// PutQueue TODO
	PutQueue = "insert_switch_queue"
	// GetQueue TODO
	GetQueue = "query_switch_queue"
	// GetQueueUid TODO
	GetQueueUid = "query_switch_queue_by_uid"
)

// TbMonSwitchQueueApi TODO
type TbMonSwitchQueueApi struct {
	Uid                int64  `json:"uid"`
	IP                 string `json:"ip"`
	Port               int    `json:"port"`
	ConfirmCheckTime   string `json:"confirm_check_time,omitempty"`
	DbRole             string `json:"db_role"`
	SlaveIP            string `json:"slave_ip"`
	SlavePort          int    `json:"slave_port"`
	Status             string `json:"status"`
	ConfirmResult      string `json:"confirm_result"`
	SwitchStartTime    string `json:"switch_start_time,omitempty"`
	SwitchFinishedTime string `json:"switch_finished_time,omitempty"`
	SwitchResult       string `json:"switch_result"`
	Remark             string `json:"remark"`
	App                string `json:"app"`
	DbType             string `json:"db_type"`
	IdcID              int    `json:"idc_id"`
	CloudID            int    `json:"cloud_id"`
	Cluster            string `json:"cluster"`
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
	case GetInsTotalSwitch:
		GetSingleInsTotal(ctx, param.QueryArgs)
	case GetIpTotalSwitch:
		GetSingleIpTotal(ctx, param.QueryArgs)
	case GetIdcTotalSwitch:
		GetSingleIdcTotal(ctx, param.QueryArgs)
	case UpdateQueue:
		UpdateSwitchQueue(ctx, param.QueryArgs, param.SetArgs)
	case PutQueue:
		PutSwitchQueue(ctx, param.SetArgs)
	case GetQueue:
		GetSwitchQueue(ctx, param.QueryArgs, param.PageArgs)
	case GetQueueUid:
		GetSwitchQueueUid(ctx, param.QueryArgs, param.PageArgs)
	default:
		api.SendResponse(ctx, api.ResponseInfo{
			Data:    nil,
			Code:    api.RespErr,
			Message: fmt.Sprintf("unknown api name[%s]", param.Name),
		})
	}
}

// GetSwitchQueue TODO
func GetSwitchQueue(ctx *fasthttp.RequestCtx, param interface{}, page api.QueryPage) {
	var (
		result    = []model.HASwitchQueue{}
		whereCond = &model.HASwitchQueue{}
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
		response.Message = "must be Post request"
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

	if whereCond.SwitchStartTime != nil && !whereCond.SwitchStartTime.IsZero() {
		db = db.Where("switch_start_time > ?", whereCond.SwitchStartTime)
	}

	if whereCond.SwitchFinishedTime != nil && !whereCond.SwitchFinishedTime.IsZero() {
		db = db.Where("switch_finished_time < ?", whereCond.SwitchFinishedTime)
	}

	if page.Limit > 0 {
		if err := db.Limit(page.Limit).Offset(page.Offset).Order("uid DESC").Find(&result).Error; err != nil {
			response.Code = api.RespErr
			response.Message = err.Error()
			response.Data = nil
			log.Logger.Errorf("query table failed:%s", err.Error())
		}
	} else {
		log.Logger.Debugf("no page_args")
		if err := db.Order("uid DESC").Find(&result).Error; err != nil {
			response.Code = api.RespErr
			response.Message = err.Error()
			response.Data = nil
			log.Logger.Errorf("query table failed:%s", err.Error())
		}
	}

	response.Data = TransSwitchQueueToApi(result)
	log.Logger.Debugf("%+v", result)
}

// GetSwitchQueueUid get switch queue info by uid
func GetSwitchQueueUid(ctx *fasthttp.RequestCtx, param interface{}, page api.QueryPage) {
	var (
		result    = []model.HASwitchQueue{}
		whereCond = &model.HASwitchQueue{}
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
		response.Message = "must be Post request"
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
	db := model.HADB.Self.Table(whereCond.TableName()).Where("uid >= ?", whereCond.Uid)
	if page.Limit > 0 {
		if err := db.Limit(page.Limit).Offset(page.Offset).Order("uid DESC").Find(&result).Error; err != nil {
			response.Code = api.RespErr
			response.Message = err.Error()
			response.Data = nil
			log.Logger.Errorf("query table failed:%s", err.Error())
		}
	} else {
		log.Logger.Debugf("no page_args")
		if err := db.Order("uid DESC").Find(&result).Error; err != nil {
			response.Code = api.RespErr
			response.Message = err.Error()
			response.Data = nil
			log.Logger.Errorf("query table failed:%s", err.Error())
		}
	}

	response.Data = TransSwitchQueueToApi(result)
	log.Logger.Debugf("%+v", result)
}

// GetSingleInsTotal TODO
func GetSingleInsTotal(ctx *fasthttp.RequestCtx, param interface{}) {
	var (
		count  int64
		result = map[string]*int64{
			"count": &count,
		}
		whereCond = &model.HASwitchQueue{}
		response  = api.ResponseInfo{
			Data:    &result,
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

	if err := model.HADB.Self.Table(whereCond.TableName()).
		Where("confirm_check_time > ?", whereCond.ConfirmCheckTime).
		Where("ip = ? and port = ?", whereCond.IP, whereCond.Port).
		Count(&count).Error; err != nil {
		response.Code = api.RespErr
		response.Message = err.Error()
		response.Data = nil
		log.Logger.Errorf("query table failed:%s", err.Error())
	}
	log.Logger.Debugf("%+v", count)
}

// GetSingleIpTotal TODO
func GetSingleIpTotal(ctx *fasthttp.RequestCtx, param interface{}) {
	var (
		count  int64
		result = map[string]*int64{
			"count": &count,
		}
		whereCond = &model.HASwitchQueue{}
		response  = api.ResponseInfo{
			Data:    &result,
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

	if err := model.HADB.Self.Table(whereCond.TableName()).
		Where("confirm_check_time > ?", whereCond.ConfirmCheckTime).
		Distinct("ip").Count(&count).Error; err != nil {
		response.Code = api.RespErr
		response.Message = err.Error()
		response.Data = nil
		log.Logger.Errorf("query table failed:%s", err.Error())
	}
	log.Logger.Debugf("%+v", result)
}

// GetSingleIdcTotal TODO
func GetSingleIdcTotal(ctx *fasthttp.RequestCtx, param interface{}) {
	var (
		count  int64
		result = map[string]*int64{
			"count": &count,
		}
		whereCond = &model.HASwitchQueue{}
		response  = api.ResponseInfo{
			Data:    &result,
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

	if err := model.HADB.Self.Table(whereCond.TableName()).
		Where("confirm_check_time > ?", whereCond.ConfirmCheckTime).
		Where("idc_id = ? and ip <> ?", whereCond.IdcID, whereCond.IP).
		Distinct("ip").Count(&count).Error; err != nil {
		response.Code = api.RespErr
		response.Message = err.Error()
		response.Data = nil
		log.Logger.Errorf("query table failed:%s", err.Error())
	}
	log.Logger.Debugf("%+v", result)
}

// UpdateSwitchQueue TODO
func UpdateSwitchQueue(ctx *fasthttp.RequestCtx, queryParam interface{}, setParam interface{}) {
	var (
		result    = map[string]int64{}
		whereCond = struct {
			query model.HASwitchQueue
			set   model.HASwitchQueue
		}{}
		response = api.ResponseInfo{
			Data:    &result,
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
		return
	}

	// convert queryParam
	if bytes, err := json.Marshal(queryParam); err != nil {
		log.Logger.Errorf("convert param failed:%s", err.Error())
		response.Code = api.RespErr
		response.Message = err.Error()
		return
	} else {
		if err = json.Unmarshal(bytes, &whereCond.query); err != nil {
			response.Code = api.RespErr
			response.Message = err.Error()
			return
		}
	}

	// convert setParam
	if bytes, err := json.Marshal(setParam); err != nil {
		log.Logger.Errorf("convert param failed:%s", err.Error())
		response.Code = api.RespErr
		response.Message = err.Error()
		return
	} else {
		if err = json.Unmarshal(bytes, &whereCond.set); err != nil {
			response.Code = api.RespErr
			response.Message = err.Error()
			return
		}
	}
	log.Logger.Debugf("%+v", whereCond)

	db := model.HADB.Self.Table(whereCond.query.TableName()).Where(whereCond.query).Updates(whereCond.set)
	if err := db.Error; err != nil {
		response.Code = api.RespErr
		response.Message = err.Error()
		response.Data = nil
		log.Logger.Errorf("query table failed:%s", err.Error())
	}
	result[api.RowsAffect] = db.RowsAffected
	log.Logger.Debugf("%+v", result)
	return
}

// PutSwitchQueue TODO
func PutSwitchQueue(ctx *fasthttp.RequestCtx, setParam interface{}) {
	input := &model.HASwitchQueue{}
	response := api.ResponseInfo{
		Data:    nil,
		Code:    api.RespOK,
		Message: "",
	}
	defer func() { api.SendResponse(ctx, response) }()

	if !ctx.IsPost() {
		response.Code = api.RespErr
		response.Message = "must be POST method"
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

	response.Data = map[string]interface{}{
		api.RowsAffect: db.RowsAffected,
		"uid":          input.Uid,
	}
}

// TransSwitchQueueToApi TODO
func TransSwitchQueueToApi(result []model.HASwitchQueue) []TbMonSwitchQueueApi {
	loc, _ := time.LoadLocation("Asia/Shanghai")
	ApiResults := make([]TbMonSwitchQueueApi, 0)
	for _, switchQueue := range result {
		var switchStartTime string
		var switchFinishTime string
		// check SwitchStartTime is nil or not
		if switchQueue.SwitchStartTime != nil {
			switchStartTime = switchQueue.SwitchStartTime.In(loc).Format("2006-01-02T15:04:05-07:00")
		} else {
			switchStartTime = time.Now().In(loc).Format("2006-01-02T15:04:05-07:00")
		}

		// check SwitchFinishedTime is nil or not
		if switchQueue.SwitchFinishedTime != nil {
			switchFinishTime = switchQueue.SwitchFinishedTime.In(loc).Format("2006-01-02T15:04:05-07:00")
		} else {
			switchFinishTime = time.Now().In(loc).Format("2006-01-02T15:04:05-07:00")
		}

		switchQueueApi := TbMonSwitchQueueApi{
			Uid:                switchQueue.Uid,
			IP:                 switchQueue.IP,
			Port:               switchQueue.Port,
			ConfirmCheckTime:   switchQueue.ConfirmCheckTime.In(loc).Format("2006-01-02T15:04:05-07:00"),
			DbRole:             switchQueue.DbRole,
			SlaveIP:            switchQueue.SlaveIP,
			SlavePort:          switchQueue.SlavePort,
			Status:             switchQueue.Status,
			ConfirmResult:      switchQueue.ConfirmResult,
			SwitchStartTime:    switchStartTime,
			SwitchFinishedTime: switchFinishTime,
			SwitchResult:       switchQueue.SwitchResult,
			Remark:             switchQueue.Remark,
			App:                switchQueue.App,
			DbType:             switchQueue.DbType,
			IdcID:              switchQueue.IdcID,
			CloudID:            switchQueue.CloudID,
			Cluster:            switchQueue.Cluster,
		}

		ApiResults = append(ApiResults, switchQueueApi)
	}
	return ApiResults
}
