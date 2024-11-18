package client

import (
	"encoding/json"
	"fmt"
	"net/http"
	"sort"
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

// AgentInfo gm base info, use to report
type AgentInfo struct {
	Ip      string `json:"ip"`
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
	DBCloudToken string             `json:"db_cloud_token"`
	BKCloudID    int                `json:"bk_cloud_id"`
	Name         string             `json:"name"`
	QueryArgs    *model.HAAgentLogs `json:"query_args,omitempty"`
	SetArgs      *model.HAAgentLogs `json:"set_args,omitempty"`
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
	RowsAffected int   `json:"rowsAffected"`
	Uid          int64 `json:"uid"`
}

// HaLogsRequest request ha_logs table
type HaLogsRequest struct {
	DBCloudToken string          `json:"db_cloud_token"`
	BKCloudID    int             `json:"bk_cloud_id"`
	Name         string          `json:"name"`
	QueryArgs    *model.HaGMLogs `json:"query_args,omitempty"`
	SetArgs      *model.HaGMLogs `json:"set_args,omitempty"`
}

// HaLogsResponse response for ha_logs
type HaLogsResponse struct {
	RowsAffected int   `json:"rowsAffected"`
	Uid          int64 `json:"uid"`
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

// GetDBDetectInfo get gm info from hadb
func (c *HaDBClient) GetDBDetectInfo() ([]model.HAAgentLogs, error) {
	req := DbStatusRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         constvar.GetInstanceStatus,
		QueryArgs:    &model.HAAgentLogs{},
	}

	log.Logger.Debugf("AgentGetGMInfo param:%#v", req)

	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.DbStatusUrl, ""), req, nil)
	if err != nil {
		return nil, err
	}
	if response.Code != 0 {
		return nil, fmt.Errorf("%s failed, return code:%d, msg:%s", util.AtWhere(), response.Code, response.Msg)
	}
	var result []model.HAAgentLogs
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
func (c *HaDBClient) ReportDBStatus(app, agentIp, ip string, port int, dbType, status, bindGM string) error {
	var result DbStatusResponse
	currentTime := time.Now()

	updateReq := DbStatusRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         constvar.UpdateInstanceStatus,
		QueryArgs: &model.HAAgentLogs{
			App:     app,
			AgentIP: agentIp,
			IP:      ip,
			Port:    port,
		},
		SetArgs: &model.HAAgentLogs{
			App:      app,
			DbType:   dbType,
			Status:   status,
			CloudID:  c.CloudId,
			LastTime: &currentTime,
			ReportGM: bindGM,
		},
	}

	log.Logger.Debugf("update instance detect status param:%#v", util.GraceStructString(updateReq))

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
		log.Logger.Errorf("bug: update instance status affect rows %d", result.RowsAffected)
	}

	insertReq := DbStatusRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         constvar.InsertInstanceStatus,
		SetArgs: &model.HAAgentLogs{
			AgentIP:  agentIp,
			App:      app,
			IP:       ip,
			Port:     port,
			DbType:   dbType,
			Status:   status,
			CloudID:  c.CloudId,
			LastTime: &currentTime,
		},
	}

	log.Logger.Debugf("insert instance status param:%v", util.GraceStructString(updateReq))

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

// ReportHaLogRough report ha logs
func (c *HaDBClient) ReportHaLogRough(monIP, app, ip string, port int, module, comment string) {
	_, _ = c.ReportHaLog(monIP, app, ip, port, module, comment)
}

// ReportHaLog report ha logs
func (c *HaDBClient) ReportHaLog(monIP, app, ip string, port int, module, comment string) (int64, error) {
	var result HaLogsResponse
	log.Logger.Infof("reporter log. ip:%s, port:%d, module:%s, comment:%s",
		ip, port, module, comment)

	req := HaLogsRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         constvar.ReporterHALog,
		SetArgs: &model.HaGMLogs{
			App:     app,
			IP:      ip,
			Port:    port,
			MonIP:   monIP,
			Module:  module,
			CloudID: c.CloudId,
			Comment: comment,
		},
	}

	log.Logger.Debugf("ReportHaLog param:%#v", util.GraceStructString(req))

	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.HaLogsUrl, ""), req, nil)
	if err != nil {
		return 0, fmt.Errorf("reporter ha log failed. err:%s", err.Error())
	}
	if response.Code != 0 {
		return 0, fmt.Errorf("%s failed, return code:%d, msg:%s", util.AtWhere(), response.Code, response.Msg)
	}
	err = json.Unmarshal(response.Data, &result)
	if err != nil {
		return 0, fmt.Errorf("reporter ha log failed. err:%s", err.Error())
	}

	return result.Uid, err
}

// RegisterDBHAInfo register agent info to ha_status table
func (c *HaDBClient) RegisterDBHAInfo(
	ip string, port int, module string, cityId int, campus string, dbType string,
) error {
	var result HaStatusResponse
	currentTime := time.Now()

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
			IP:        ip,
			Port:      port,
			Module:    module,
			CityID:    cityId,
			Campus:    campus,
			CloudID:   c.CloudId,
			DbType:    dbType,
			Status:    constvar.RUNNING,
			StartTime: &currentTime,
		},
	}

	log.Logger.Debugf("RegisterDBHAInfo param:%#v", util.GraceStructString(req))

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
func (c *HaDBClient) GetAliveAgentInfo(cityID int, dbType string, interval int) ([]string, error) {
	var result []string

	currentTime := time.Now().Add(-time.Second * time.Duration(interval))
	req := HaStatusRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         constvar.GetAliveAgentInfo,
		QueryArgs: &model.HaStatus{
			CityID:   cityID,
			DbType:   dbType,
			Module:   constvar.Agent,
			Status:   constvar.RUNNING,
			CloudID:  c.CloudId,
			LastTime: &currentTime,
		},
	}

	log.Logger.Debugf("GetAliveAgentInfo param:%#v", util.GraceStructString(req))

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

	//after unmarshal, need to sort, otherwise hash value may incorrect
	sort.Strings(result)
	return result, nil
}

// GetAliveHAComponent get alive gm instance from ha_status table
func (c *HaDBClient) GetAliveHAComponent(module string, interval int) ([]GMInfo, error) {
	currentTime := time.Now().Add(-time.Second * time.Duration(interval))
	req := HaStatusRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         constvar.GetAliveHAInfo,
		QueryArgs: &model.HaStatus{
			Module:   module,
			CloudID:  c.CloudId,
			LastTime: &currentTime,
		},
	}

	log.Logger.Debugf("GetAliveHAInfo param:%#v", util.GraceStructString(req))

	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.HaStatusUrl, ""), req, nil)
	if err != nil {
		log.Logger.Errorf("GetAliveHAInfo failed, do http fail,err:%s", err.Error())
		return nil, err
	}
	if response.Code != 0 {
		return nil, fmt.Errorf("%s failed, return code:%d, msg:%s", util.AtWhere(), response.Code, response.Msg)
	}

	result := make([]GMInfo, 0)
	err = json.Unmarshal(response.Data, &result)
	if err != nil {
		log.Logger.Errorf("GetAliveHAInfo failed, unmarshal failed, err:%s, data:%s", err.Error(), response.Data)
		return nil, err
	}
	if len(result) == 0 {
		return nil, fmt.Errorf("no HA component found")
	}
	return result, nil
}

// ReporterAgentHeartbeat report agent heartbeat to ha_status table
func (c *HaDBClient) ReporterAgentHeartbeat(agentIP, detectType string, interval, mod, modValue int) error {
	var result HaStatusResponse

	currentTime := time.Now()
	req := HaStatusRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         constvar.ReporterAgentHeartbeat,
		QueryArgs: &model.HaStatus{
			IP:     agentIP,
			DbType: detectType,
		},
		SetArgs: &model.HaStatus{
			ReportInterval: interval,
			LastTime:       &currentTime,
			HashMod:        &mod,
			HashValue:      &modValue,
		},
	}

	log.Logger.Debugf("ReporterAgentHeartbeat param:%#v", util.GraceStructString(req))

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
func (c *HaDBClient) ReporterGMHeartbeat(gmIP, module string, interval int) error {
	var result HaStatusResponse

	currentTime := time.Now()
	req := HaStatusRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         constvar.ReporterGMHeartbeat,
		QueryArgs: &model.HaStatus{
			IP:     gmIP,
			Module: module,
		},
		SetArgs: &model.HaStatus{
			ReportInterval: interval,
			LastTime:       &currentTime,
		},
	}

	log.Logger.Debugf("ReporterGMHeartbeat param:%#v", util.GraceStructString(req))

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

	log.Logger.Debugf("QuerySingleTotal param:%#v", util.GraceStructString(req))

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

	log.Logger.Debugf("QueryIntervalTotal param:%#v", util.GraceStructString(req))

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

	log.Logger.Debugf("QuerySingleIDC param:%#v", util.GraceStructString(req))

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

	log.Logger.Debugf("UpadteTimeDelay param:%#v", util.GraceStructString(req))

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
	return nil
}

// InsertSwitchQueue insert pre-switch instance to switch queue
func (c *HaDBClient) InsertSwitchQueue(reqInfo *SwitchQueueRequest) (int64, error) {
	var result SwitchQueueResponse

	log.Logger.Debugf("InsertSwitchQueue param:%#v", util.GraceStructString(reqInfo))

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

	log.Logger.Debugf("UpdateSwitchQueue param:%#v", util.GraceStructString(reqInfo))

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
func (c *HaDBClient) InsertSwitchLog(swId int64, ip string, port int, app, result,
	comment string, switchFinishTime time.Time) error {
	var res SwitchLogResponse
	req := SwitchLogRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         constvar.InsertSwitchLog,
		SetArgs: &model.HASwitchLogs{
			App:      app,
			SwitchID: swId,
			IP:       ip,
			Port:     port,
			Result:   result,
			Comment:  comment,
			Datetime: &switchFinishTime,
		},
	}

	log.Logger.Debugf("InsertSwitchLog param:%#v", util.GraceStructString(req))

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
func (c *HaDBClient) AgentGetHashValue(agentIP string, cityID int, dbType string, interval int) (int, int, error) {
	//	select ip from ha_status where city_id = ? and db_type = ?
	//	and module = "agent" and status = "RUNNING"
	//	and last_time > DATE_SUB(now(), interval 5 minute)
	//	order by uid;
	agents, err := c.GetAliveAgentInfo(cityID, dbType, interval)
	if err != nil {
		log.Logger.Errorf("get agent list failed. err:%s", err.Error())
		return 0, 0, err
	}
	var mod int
	var modValue int
	var find bool
	mod = len(agents)
	for index, agent := range agents {
		if agent == agentIP {
			if find {
				log.Logger.Errorf("multi agent with same agentIP:%s", agentIP)
				return 0, 0, err
			}
			find = true
			modValue = index
		}
	}
	if !find {
		err = fmt.Errorf("bug: can't find in agent list. agentIP:%s, dbType:%s", agentIP, dbType)
		log.Logger.Errorf(err.Error())
		//report invalid mod info
		_ = c.ReporterAgentHeartbeat(agentIP, dbType, interval, 0, 0)

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
