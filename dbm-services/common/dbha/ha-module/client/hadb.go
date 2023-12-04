package client

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"time"

	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/util"
	"dbm-services/common/dbha/hadb-api/model"
	"dbm-services/common/dbha/hadb-api/pkg/handler/hashieldconfig"
)

// HaDBClient client use to request hadb api
type HaDBClient struct {
	Client
}

// GMInfo gm base info, use to report
type GMInfo struct {
	Ip      string `json:"ip"`
	Port    int    `json:"port"`
	CityID  int    `json:"city_id"`
	CloudID int    `json:"cloud_id"`
}

// HaStatusRequest request ha status table
type HaStatusRequest struct {
	DBCloudToken string          `json:"db_cloud_token"`
	BKCloudID    int             `json:"bk_cloud_id"`
	Name         string          `json:"name"`
	QueryArgs    *model.HaStatus `json:"query_args,omitempty"`
	SetArgs      *model.HaStatus `json:"set_args,omitempty"`
}

// HaStatusResponse ha status response
type HaStatusResponse struct {
	RowsAffected int `json:"rowsAffected"`
}

// DbStatusRequest request db status
type DbStatusRequest struct {
	DBCloudToken string            `json:"db_cloud_token"`
	BKCloudID    int               `json:"bk_cloud_id"`
	Name         string            `json:"name"`
	QueryArgs    *model.HADbStatus `json:"query_args,omitempty"`
	SetArgs      *model.HADbStatus `json:"set_args,omitempty"`
}

// DbStatusResponse db status response
type DbStatusResponse struct {
	RowsAffected int `json:"rowsAffected"`
	Uid          int `json:"uid"`
}

// SwitchQueueRequest request switch queue
type SwitchQueueRequest struct {
	DBCloudToken string               `json:"db_cloud_token"`
	BKCloudID    int                  `json:"bk_cloud_id"`
	Name         string               `json:"name"`
	QueryArgs    *model.HASwitchQueue `json:"query_args,omitempty"`
	SetArgs      *model.HASwitchQueue `json:"set_args,omitempty"`
}

// SwitchQueueResponse switch queue response
type SwitchQueueResponse struct {
	RowsAffected int  `json:"rowsAffected"`
	Uid          uint `json:"uid"`
}

// HaLogsRequest request ha_logs table
type HaLogsRequest struct {
	DBCloudToken string        `json:"db_cloud_token"`
	BKCloudID    int           `json:"bk_cloud_id"`
	Name         string        `json:"name"`
	QueryArgs    *model.HaLogs `json:"query_args,omitempty"`
	SetArgs      *model.HaLogs `json:"set_args,omitempty"`
}

// HaLogsResponse response for ha_logs
type HaLogsResponse struct {
	RowsAffected int `json:"rowsAffected"`
}

// SwitchLogRequest request switch log
type SwitchLogRequest struct {
	DBCloudToken string              `json:"db_cloud_token"`
	BKCloudID    int                 `json:"bk_cloud_id"`
	Name         string              `json:"name"`
	QueryArgs    *model.HASwitchLogs `json:"query_args,omitempty"`
	SetArgs      *model.HASwitchLogs `json:"set_args,omitempty"`
}

// SwitchLogResponse switch log response
type SwitchLogResponse struct {
	RowsAffected int `json:"rowsAffected"`
}

// ShieldConfigRequest request for shield config
type ShieldConfigRequest struct {
	DBCloudToken string          `json:"db_cloud_token"`
	BKCloudID    int             `json:"bk_cloud_id"`
	Name         string          `json:"name"`
	QueryArgs    *model.HAShield `json:"query_args,omitempty"`
	SetArgs      *model.HAShield `json:"set_args,omitempty"`
}

// AgentIp agent ip info
type AgentIp struct {
	Ip string `json:"ip"`
}

// NewHaDBClient init hadb client object
func NewHaDBClient(conf *config.APIConfig, cloudId int) *HaDBClient {
	c := NewAPIClient(conf, constvar.HaDBName, cloudId)
	return &HaDBClient{c}
}

// AgentGetGMInfo get gm info from hadb
func (c *HaDBClient) AgentGetGMInfo() ([]GMInfo, error) {
	req := HaStatusRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         constvar.AgentGetGMInfo,
		QueryArgs: &model.HaStatus{
			Module:  constvar.GM,
			CloudID: c.CloudId,
		},
	}

	log.Logger.Debugf("AgentGetGMInfo param:%#v", req)

	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.HaStatusUrl, ""), req, nil)
	if err != nil {
		return nil, err
	}
	if response.Code != 0 {
		return nil, fmt.Errorf("%s failed, return code:%d, msg:%s", util.AtWhere(), response.Code, response.Msg)
	}
	var result []GMInfo
	err = json.Unmarshal(response.Data, &result)
	if err != nil {
		return nil, err
	}
	if len(result) == 0 {
		return nil, fmt.Errorf("no gm available")
	}
	return result, nil
}

// ReportDBStatus report detected instance's status
func (c *HaDBClient) ReportDBStatus(
	agentIp string, ip string, port int, dbType string, status string,
) error {
	var result DbStatusResponse
	currentTime := time.Now()

	updateReq := DbStatusRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         constvar.UpdateInstanceStatus,
		QueryArgs: &model.HADbStatus{
			AgentIP: agentIp,
			IP:      ip,
			Port:    port,
		},
		SetArgs: &model.HADbStatus{
			DbType:   dbType,
			Status:   status,
			CloudID:  c.CloudId,
			LastTime: &currentTime,
		},
	}

	log.Logger.Debugf("update instance detect status param:%#v", updateReq)

	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.DbStatusUrl, ""), updateReq, nil)
	if err != nil {
		return err
	}
	if response.Code != 0 {
		return fmt.Errorf("%s failed, return code:%d, msg:%s", util.AtWhere(), response.Code, response.Msg)
	}
	err = json.Unmarshal(response.Data, &result)
	if err != nil {
		return err
	}
	if result.RowsAffected == 1 {
		return nil
	}
	if result.RowsAffected > 1 {
		log.Logger.Fatalf("bug: update instance status affect rows %d", result.RowsAffected)
	}

	insertReq := DbStatusRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         constvar.InsertInstanceStatus,
		SetArgs: &model.HADbStatus{
			AgentIP:  agentIp,
			IP:       ip,
			Port:     port,
			DbType:   dbType,
			Status:   status,
			CloudID:  c.CloudId,
			LastTime: &currentTime,
		},
	}

	log.Logger.Debugf("insert instance status param:%v", updateReq)

	response, err = c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.DbStatusUrl, ""), insertReq, nil)
	if err != nil {
		return err
	}
	if response.Code != 0 {
		return fmt.Errorf("%s failed, return code:%d, msg:%s", util.AtWhere(), response.Code, response.Msg)
	}
	err = json.Unmarshal(response.Data, &result)
	if err != nil {
		return err
	}

	return nil
}

// ReportHaLog report ha logs
func (c *HaDBClient) ReportHaLog(ip string, port int, module string, comment string) {
	var result HaLogsRequest
	log.Logger.Infof("reporter log. ip:%s, port:%d, module:%s, comment:%s",
		ip, port, module, comment)

	req := HaLogsRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         constvar.ReporterHALog,
		SetArgs: &model.HaLogs{
			IP:      ip,
			Port:    port,
			MonIP:   util.LocalIp,
			Module:  module,
			CloudID: c.CloudId,
			Comment: comment,
		},
	}

	log.Logger.Debugf("ReportHaLog param:%#v", req)

	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.HaLogsUrl, ""), req, nil)
	if err != nil {
		log.Logger.Errorf("reporter log failed. err:%s", err.Error())
		return
	}
	if response.Code != 0 {
		err = fmt.Errorf("%s failed, return code:%d, msg:%s", util.AtWhere(), response.Code, response.Msg)
		log.Logger.Errorf("reporter log failed. err:%s", err.Error())
		return
	}
	err = json.Unmarshal(response.Data, &result)
	if err != nil {
		log.Logger.Errorf("reporter log failed. err:%s", err.Error())
	}
}

// RegisterDBHAInfo register agent info to ha_status table
func (c *HaDBClient) RegisterDBHAInfo(
	ip string, port int, module string, cityId int, campus string, dbType string,
) error {
	var result HaStatusResponse

	req := HaStatusRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         constvar.RegisterDBHAInfo,
		QueryArgs: &model.HaStatus{
			IP:     ip,
			Module: module,
			DbType: dbType,
		},
		SetArgs: &model.HaStatus{
			IP:      ip,
			Port:    port,
			Module:  module,
			CityID:  cityId,
			Campus:  campus,
			CloudID: c.CloudId,
			DbType:  dbType,
			Status:  constvar.RUNNING,
		},
	}

	log.Logger.Debugf("RegisterDBHAInfo param:%#v", req)

	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.HaStatusUrl, ""), req, nil)
	if err != nil {
		return err
	}
	if response.Code != 0 {
		return fmt.Errorf("%s failed, return code:%d, msg:%s", util.AtWhere(), response.Code, response.Msg)
	}
	err = json.Unmarshal(response.Data, &result)
	if err != nil {
		return err
	}
	return nil
}

// GetAliveAgentInfo fetch alive agent info from ha_status table
func (c *HaDBClient) GetAliveAgentInfo(ip string, dbType string, interval int) ([]string, error) {
	var result []string

	currentTime := time.Now().Add(-time.Second * time.Duration(interval))
	req := HaStatusRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         constvar.GetAliveAgentInfo,
		QueryArgs: &model.HaStatus{
			IP:       ip,
			DbType:   dbType,
			Module:   constvar.Agent,
			Status:   constvar.RUNNING,
			CloudID:  c.CloudId,
			LastTime: &currentTime,
		},
	}

	log.Logger.Debugf("GetAliveAgentInfo param:%#v", req)

	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.HaStatusUrl, ""), req, nil)
	if err != nil {
		return nil, err
	}
	if response.Code != 0 {
		return nil, fmt.Errorf("%s failed, return code:%d, msg:%s", util.AtWhere(), response.Code, response.Msg)
	}
	err = json.Unmarshal(response.Data, &result)
	if err != nil {
		return nil, err
	}
	return result, nil
}

// GetAliveGMInfo get alive gm instance from ha_status table
func (c *HaDBClient) GetAliveGMInfo(interval int) ([]GMInfo, error) {
	currentTime := time.Now().Add(-time.Second * time.Duration(interval))
	req := HaStatusRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         constvar.GetAliveGMInfo,
		QueryArgs: &model.HaStatus{
			Module:   constvar.GM,
			CloudID:  c.CloudId,
			LastTime: &currentTime,
		},
	}

	log.Logger.Debugf("GetAliveGMInfo param:%#v", req)

	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.HaStatusUrl, ""), req, nil)
	if err != nil {
		log.Logger.Errorf("GetAliveGMInfo failed, do http fail,err:%s", err.Error())
		return nil, err
	}
	if response.Code != 0 {
		return nil, fmt.Errorf("%s failed, return code:%d, msg:%s", util.AtWhere(), response.Code, response.Msg)
	}

	result := make([]GMInfo, 0)
	err = json.Unmarshal(response.Data, &result)
	if err != nil {
		log.Logger.Errorf("GetAliveGMInfo failed, unmarshal failed, err:%s, data:%s", err.Error(), response.Data)
		return nil, err
	}
	if len(result) == 0 {
		return nil, fmt.Errorf("no gm available")
	}
	return result, nil
}

// ReporterAgentHeartbeat report agent heartbeat to ha_status table
func (c *HaDBClient) ReporterAgentHeartbeat(detectType string, interval int, gmInfo string) error {
	var result HaStatusResponse

	currentTime := time.Now()
	req := HaStatusRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         constvar.ReporterAgentHeartbeat,
		QueryArgs: &model.HaStatus{
			IP:     util.LocalIp,
			DbType: detectType,
		},
		SetArgs: &model.HaStatus{
			ReportInterval: interval,
			LastTime:       &currentTime,
			TakeOverGm:     gmInfo,
		},
	}

	log.Logger.Debugf("ReporterAgentHeartbeat param:%#v", req)

	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.HaStatusUrl, ""), req, nil)
	if err != nil {
		return err
	}
	if response.Code != 0 {
		return fmt.Errorf("%s failed, return code:%d, msg:%s", util.AtWhere(), response.Code, response.Msg)
	}
	err = json.Unmarshal(response.Data, &result)
	if err != nil {
		return err
	}

	return nil
}

// ReporterGMHeartbeat report gm heartbeat to ha_status
func (c *HaDBClient) ReporterGMHeartbeat(module string, interval int) error {
	var result HaStatusResponse

	currentTime := time.Now()
	req := HaStatusRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         constvar.ReporterGMHeartbeat,
		QueryArgs: &model.HaStatus{
			IP:     util.LocalIp,
			Module: module,
		},
		SetArgs: &model.HaStatus{
			ReportInterval: interval,
			LastTime:       &currentTime,
		},
	}

	log.Logger.Debugf("ReporterGMHeartbeat param:%#v", req)

	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.HaStatusUrl, ""), req, nil)
	if err != nil {
		return err
	}
	if response.Code != 0 {
		return fmt.Errorf("%s failed, return code:%d, msg:%s", util.AtWhere(), response.Code, response.Msg)
	}
	err = json.Unmarshal(response.Data, &result)
	if err != nil {
		return err
	}
	return nil
}

// QuerySingleTotal check same instance's switch number in a given time period
func (c *HaDBClient) QuerySingleTotal(ip string, port int, interval int) (int, error) {
	var result struct {
		Count int `json:"count"`
	}
	confirmTime := time.Now().Add(-time.Second * time.Duration(interval))
	req := SwitchQueueRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         constvar.QuerySingleTotal,
		QueryArgs: &model.HASwitchQueue{
			IP:               ip,
			Port:             port,
			ConfirmCheckTime: &confirmTime,
		},
	}

	log.Logger.Debugf("QuerySingleTotal param:%#v", req)

	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.SwitchQueueUrl, ""), req, nil)
	if err != nil {
		return 0, err
	}
	if response.Code != 0 {
		return 0, fmt.Errorf("%s failed, return code:%d, msg:%s", util.AtWhere(), response.Code, response.Msg)
	}
	err = json.Unmarshal(response.Data, &result)
	if err != nil {
		return 0, err
	}
	return result.Count, nil
}

// QueryIntervalTotal get total switch number in a given time period
func (c *HaDBClient) QueryIntervalTotal(interval int) (int, error) {
	var result struct {
		Count int `json:"count"`
	}

	confirmTime := time.Now().Add(-time.Second * time.Duration(interval))
	req := SwitchQueueRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         constvar.QueryIntervalTotal,
		QueryArgs: &model.HASwitchQueue{
			ConfirmCheckTime: &confirmTime,
		},
	}

	log.Logger.Debugf("QueryIntervalTotal param:%#v", req)

	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.SwitchQueueUrl, ""), req, nil)
	if err != nil {
		return 0, err
	}
	if response.Code != 0 {
		return 0, fmt.Errorf("%s failed, return code:%d, msg:%s", util.AtWhere(), response.Code, response.Msg)
	}
	err = json.Unmarshal(response.Data, &result)
	if err != nil {
		return 0, err
	}
	return result.Count, nil
}

// QuerySingleIDC get current idc total switch number in a given time period
func (c *HaDBClient) QuerySingleIDC(ip string, idc int) (int, error) {
	var result struct {
		Count int `json:"count"`
	}

	confirmTime := time.Now().Add(-time.Minute)
	req := SwitchQueueRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         constvar.QuerySingleIDC,
		QueryArgs: &model.HASwitchQueue{
			IP:               ip,
			IdcID:            idc,
			ConfirmCheckTime: &confirmTime,
		},
	}

	log.Logger.Debugf("QuerySingleIDC param:%#v", req)

	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.SwitchQueueUrl, ""), req, nil)
	if err != nil {
		return 0, err
	}
	if response.Code != 0 {
		return 0, fmt.Errorf("%s failed, return code:%d, msg:%s", util.AtWhere(), response.Code, response.Msg)
	}
	err = json.Unmarshal(response.Data, &result)
	if err != nil {
		return 0, err
	}
	return result.Count, nil
}

// UpdateTimeDelay update time delay for delay switch
func (c *HaDBClient) UpdateTimeDelay(ip string, port int, app string) error {
	var result struct {
		RowsNum int `json:"rowsAffected"`
	}

	req := SwitchQueueRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         constvar.QuerySingleIDC,
		QueryArgs: &model.HASwitchQueue{
			IP:   ip,
			Port: port,
			App:  app,
		},
	}

	log.Logger.Debugf("UpadteTimeDelay param:%#v", req)

	response, err := c.DoNew(http.MethodPost, c.SpliceUrl(constvar.UpdateTimeDelay, ""), req, nil)
	if err != nil {
		return err
	}
	if response.Code != 0 {
		return fmt.Errorf("%s failed, return code:%d, msg:%s", util.AtWhere(), response.Code, response.Msg)
	}
	err = json.Unmarshal(response.Data, &result)
	if err != nil {
		return err
	}
	// if result.RowsNum != 1 {
	// 	log.Logger.Fatalf("bug: ReporterAgentHeartbeat affect rows %d", result.RowsNum)
	// }
	return nil
}

// InsertSwitchQueue insert pre-switch instance to switch queue
func (c *HaDBClient) InsertSwitchQueue(reqInfo *SwitchQueueRequest) (uint, error) {
	var result SwitchQueueResponse

	log.Logger.Debugf("InsertSwitchQueue param:%#v", reqInfo)

	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.SwitchQueueUrl, ""), reqInfo, nil)
	if err != nil {
		return 0, err
	}
	if response.Code != 0 {
		return 0, fmt.Errorf("%s failed, return code:%d, msg:%s", util.AtWhere(), response.Code, response.Msg)
	}
	err = json.Unmarshal(response.Data, &result)
	if err != nil {
		return 0, err
	}
	return result.Uid, err
}

// QuerySlaveCheckConfig query slave check configure from hadb
// whether to do checksum, whether omit delay
func (c *HaDBClient) QuerySlaveCheckConfig(ip string, port int, app string) (int, int, error) {
	var result struct {
		DoChecksum  int `json:"do_checksum"`
		DoTimeDelay int `json:"do_timedelay"`
	}

	req := c.ConvertParamForGetRequest(map[string]string{
		"ip":   ip,
		"port": strconv.Itoa(port),
		"app":  app,
	})

	log.Logger.Debugf("QuerySlaveCheckConfig param:%#v", req)

	response, err := c.DoNew(http.MethodGet, c.SpliceUrl(constvar.QuerySlaveCheckConfig, req), nil, nil)
	if err != nil {
		return 0, 0, err
	}
	if response.Code != 0 {
		return 0, 0, fmt.Errorf("%s failed, return code:%d, msg:%s", util.AtWhere(), response.Code, response.Msg)
	}
	err = json.Unmarshal(response.Data, &result)
	if err != nil {
		return 0, 0, err
	}
	return result.DoChecksum, result.DoTimeDelay, err
}

// UpdateSwitchQueue TODO
func (c *HaDBClient) UpdateSwitchQueue(reqInfo *SwitchQueueRequest) error {
	var result SwitchQueueResponse

	log.Logger.Debugf("UpdateSwitchQueue param:%#v", reqInfo)

	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.SwitchQueueUrl, ""), reqInfo, nil)
	if err != nil {
		return err
	}
	if response.Code != 0 {
		return fmt.Errorf("%s failed, return code:%d, msg:%s", util.AtWhere(), response.Code, response.Msg)
	}
	err = json.Unmarshal(response.Data, &result)
	if err != nil {
		return err
	}

	return nil
}

// InsertSwitchLog insert switch log to hadb
func (c *HaDBClient) InsertSwitchLog(swId uint, ip string, port int, result string,
	comment string, switchFinishTime time.Time) error {
	var res SwitchLogResponse
	req := SwitchLogRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         constvar.InsertSwitchLog,
		SetArgs: &model.HASwitchLogs{
			SwitchID: swId,
			IP:       ip,
			Port:     port,
			Result:   result,
			Comment:  comment,
			Datetime: &switchFinishTime,
		},
	}

	log.Logger.Debugf("InsertSwitchLog param:%#v", req)

	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.SwitchLogUrl, ""), req, nil)
	if err != nil {
		return err
	}

	if response.Code != 0 {
		return fmt.Errorf("%s failed, return code:%d, msg:%s", util.AtWhere(), response.Code, response.Msg)
	}
	err = json.Unmarshal(response.Data, &res)
	if err != nil {
		return err
	}
	return nil
}

// AgentGetHashValue get agent's module value and hash value.
// fetch all agents by current agent's city, db_type
//
//	mod value  : agent number
//	hash value : agent's index
func (c *HaDBClient) AgentGetHashValue(agentIP string, dbType string, interval int) (uint32, uint32, error) {
	//	select * from ha_status
	//		where city in (
	//		select city from ha_status where
	//			agentIP = ? and db_type = ?
	//		)
	//	and module = "agent" and status = "RUNNING"
	//	and last_time > DATE_SUB(now(), interval 5 minute)
	//	order by uid;
	agents, err := c.GetAliveAgentInfo(agentIP, dbType, interval)
	if err != nil {
		log.Logger.Errorf("get agent list failed. err:%s", err.Error())
		return 0, 0, err
	}
	var mod uint32
	var modValue uint32
	var find bool
	mod = uint32(len(agents))
	for index, agentIp := range agents {
		if agentIp == agentIP {
			if find {
				log.Logger.Errorf("multi agent with same agentIP:%s", agentIP)
				return 0, 0, err
			}
			find = true
			modValue = uint32(index)
		}
	}
	if !find {
		err = fmt.Errorf("bug: can't find in agent list. agentIP:%s, dbType:%s", agentIP, dbType)
		log.Logger.Errorf(err.Error())
		_ = c.ReporterAgentHeartbeat(dbType, interval, "N/A")

		return mod, modValue, err
	}
	return mod, modValue, nil
}

// GetShieldConfig get shield config from HADB
func (c *HaDBClient) GetShieldConfig(shield *model.HAShield) (map[string]model.HAShield, error) {
	shieldConfigMap := make(map[string]model.HAShield)
	req := ShieldConfigRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         hashieldconfig.GetShieldInfo,
		QueryArgs:    shield,
	}

	log.Logger.Debugf("GetShieldConfig param:%#v", req)

	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.ShieldConfigUrl, ""), req, nil)
	if err != nil {
		return nil, err
	}
	if response.Code != 0 {
		return nil, fmt.Errorf("%s failed, return code:%d, msg:%s", util.AtWhere(), response.Code, response.Msg)
	}
	var result []model.HAShield
	err = json.Unmarshal(response.Data, &result)
	if err != nil {
		return nil, err
	}
	if len(result) == 0 {
		log.Logger.Debugf("no shield config found")
		return shieldConfigMap, nil
	}
	for _, row := range result {
		shieldConfigMap[row.Ip] = row
	}
	return shieldConfigMap, nil
}
