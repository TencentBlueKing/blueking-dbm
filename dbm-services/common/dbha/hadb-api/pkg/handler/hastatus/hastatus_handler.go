package hastatus

import (
	"encoding/json"
	"fmt"
	"time"

	"dbm-services/common/dbha/hadb-api/log"
	"dbm-services/common/dbha/hadb-api/model"
	"dbm-services/common/dbha/hadb-api/pkg/api"

	"github.com/valyala/fasthttp"
	"gorm.io/gorm"
)

const (
	haTableName = "ha_status"
)

/*
func Handler(ctx *fasthttp.RequestCtx) {
  result := &model.HaStatus{}
  response := api.ResponseInfo{
    Data:    result,
    Code:    api.RespOK,
    Message: "",
  }
  structName := reflect.TypeOf(model.HaStatus{})
  whereCondMap := make(map[string]interface{})
  ctx.QueryArgs().VisitAll(func(key, value []byte) {
    if _, ok := util.FieldByNameCaseIgnore(structName, string(key)); ok {
      whereCondMap[string(key)] = string(value)
    } else {
      log.Logger.Warnf("ignore invalid request argument:%s", string(key))
    }
  })
  if err := model.HADB.Self.Table(result.TableName()).Where(whereCondMap).Find(result).Error; err != nil {
    response.Code = api.RespErr
    response.Message = err.Error()
    response.Data = nil
    log.Logger.Errorf("query table failed:%s", err.Error())
  }
  log.Logger.Debugf("query result:%+v", result)
  api.SendResponse(ctx, response)
}
*/

const (
	// GetGmInfo TODO
	GetGmInfo = "agent_get_GM_info"
	// GetAgentInfo TODO
	GetAgentInfo = "agent_get_agent_info"
	// UpdateAgentInfo TODO
	UpdateAgentInfo = "reporter_agent_heartbeat"
	// UpdateGMInfo TODO
	UpdateGMInfo = "reporter_gm_heartbeat"
	// GetAliveAgentInfo TODO
	GetAliveAgentInfo = "get_alive_agent_info"
	// GetAliveGMInfo TODO
	GetAliveGMInfo = "get_alive_gm_info"
	// RegisterHaInfo TODO
	RegisterHaInfo = "register_dbha_info"
)

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
	case GetGmInfo, GetAgentInfo:
		GetHaInfo(ctx, param.QueryArgs)
	case UpdateAgentInfo:
		UpdateHaInfo(ctx, param.QueryArgs, param.SetArgs)
	case UpdateGMInfo:
		UpdateHaInfo(ctx, param.QueryArgs, param.SetArgs)
	case GetAliveGMInfo:
		GetAliveGmInfo(ctx, param.QueryArgs)
	case GetAliveAgentInfo:
		GetAliveHaInfo(ctx, param.QueryArgs)
	case RegisterHaInfo:
		ReplaceHaInfo(ctx, param.QueryArgs, param.SetArgs)
	default:
		api.SendResponse(ctx, api.ResponseInfo{
			Data:    nil,
			Code:    api.RespErr,
			Message: fmt.Sprintf("unknown api name[%s]", param.Name),
		})
	}
}

// GetHaInfo TODO
func GetHaInfo(ctx *fasthttp.RequestCtx, param interface{}) {
	var (
		result    = []model.HaStatus{}
		whereCond = &model.HaStatus{}
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

	if err := model.HADB.Self.Table(whereCond.TableName()).Where(whereCond).Find(&result).Error; err != nil {
		response.Code = api.RespErr
		response.Message = err.Error()
		response.Data = nil
		log.Logger.Errorf("query table failed:%s", err.Error())
	}
	log.Logger.Debugf("%+v", result)
}

// UpdateHaInfo TODO
func UpdateHaInfo(ctx *fasthttp.RequestCtx, queryParam interface{}, setParam interface{}) {
	var (
		result    = map[string]int64{}
		whereCond = struct {
			query model.HaStatus
			set   model.HaStatus
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

// GetAliveGmInfo TODO
func GetAliveGmInfo(ctx *fasthttp.RequestCtx, param interface{}) {
	var (
		result    = []model.HaStatus{}
		whereCond = &model.HaStatus{}
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
	log.Logger.Debugf("alive gm: %+v", whereCond)

	if err := model.HADB.Self.Table(whereCond.TableName()).
		Where("module = ? and cloud= ? and last_time > ?", whereCond.Module, whereCond.Cloud, whereCond.LastTime).
		Find(&result).Error; err != nil {
		response.Code = api.RespErr
		response.Message = err.Error()
		response.Data = nil
		log.Logger.Errorf("query table failed:%s", err.Error())
	}
	log.Logger.Debugf("%+v", result)
}

// GetAliveHaInfo TODO
func GetAliveHaInfo(ctx *fasthttp.RequestCtx, param interface{}) {
	var (
		result    = []string{}
		whereCond = &model.HaStatus{}
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

	// select ip from ha_status
	//		where city in (
	//		select city from ha_status where
	//		   ip = ? and db_type = ?
	//		)
	//	 and module = "agent" and status = "RUNNING"
	//	 and last_time > DATE_SUB(now(), interval 5 minute)
	//	 order by uid;
	db := model.HADB.Self
	subQuery := db.Table(haTableName).
		Where("ip = ? ", whereCond.IP).Select("city")
	db.Table(haTableName).Where("city in (?)", subQuery).Select("ip").
		Where("module = ? and status = ? and last_time > ? and db_type= ? and cloud= ?",
			whereCond.Module, whereCond.Status, whereCond.LastTime, whereCond.DbType, whereCond.Cloud).Order("uid").Find(&result)

	if err := db.Error; err != nil {
		response.Code = api.RespErr
		response.Message = err.Error()
		response.Data = nil
		log.Logger.Errorf("query table failed:%s", err.Error())
	}
	log.Logger.Debugf("%+v", result)
}

// ReplaceHaInfo TODO
func ReplaceHaInfo(ctx *fasthttp.RequestCtx, queryParam interface{}, setParam interface{}) {
	var (
		result    = map[string]int64{}
		whereCond = struct {
			query model.HaStatus
			set   model.HaStatus
		}{}
		response = api.ResponseInfo{
			Code:    api.RespOK,
			Message: "",
			Data:    &result,
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
	whereCond.set.LastTime = time.Now()

	log.Logger.Debugf("%+v", whereCond)

	if err := model.HADB.Self.Transaction(func(tx *gorm.DB) error {
		row := &model.HaStatus{}
		rt := tx.Table(whereCond.query.TableName()).Where(whereCond.query).First(row)
		if rt.Error != nil {
			if rt.Error == gorm.ErrRecordNotFound {
				tx = tx.Table(whereCond.set.TableName()).Create(setParam)
				if tx.Error != nil {
					return tx.Error
				} else {
					result[api.RowsAffect] = tx.RowsAffected
					return nil
				}
			} else {
				return rt.Error
			}
		} else {
			tx = tx.Table(whereCond.set.TableName()).Where(whereCond.query).Updates(whereCond.set)
			if tx.Error != nil {
				return tx.Error
			} else {
				log.Logger.Debugf("rowsaffected:%d", tx.RowsAffected)
				result[api.RowsAffect] = tx.RowsAffected
				return nil
			}
		}
	}); err != nil {
		response.Code = api.RespErr
		response.Message = err.Error()
		response.Data = nil
		log.Logger.Errorf("query table failed:%s", err.Error())
	}
	return
}
