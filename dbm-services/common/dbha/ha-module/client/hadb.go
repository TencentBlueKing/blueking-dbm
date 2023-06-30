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
)

// HaDBClient client use to request hadb api
type HaDBClient struct {
	Client
}

// GMInfo gm base info, use to report
type GMInfo struct {
	Ip    string `json:"ip"`
	Port  int    `json:"port"`
	City  string `json:"city"`
	Cloud string `json:"cloud"`
}

// HaStatus api for ha_status table
type HaStatus struct {
	Uid            uint       `json:"uid,omitempty"`
	IP             string     `json:"ip,omitempty"`
	Port           int        `json:"port,omitempty"`
	Module         string     `json:"module,omitempty"`
	City           string     `json:"city,omitempty"`
	Campus         string     `json:"campus,omitempty"`
	Cloud          string     `json:"cloud,omitempty"`
	DbType         string     `json:"db_type,omitempty"`
	StartTime      *time.Time `json:"start_time,omitempty"`
	LastTime       *time.Time `json:"last_time,omitempty"`
	Status         string     `json:"status,omitempty"`
	TakeOverGm     string     `json:"take_over_gm,omitempty"`
	ReportInterval int        `json:"report_interval,omitempty"`
}

// HaStatusRequest request ha status table
type HaStatusRequest struct {
	DBCloudToken string    `json:"db_cloud_token"`
	BKCloudID    int       `json:"bk_cloud_id"`
	Name         string    `json:"name"`
	QueryArgs    *HaStatus `json:"query_args,omitempty"`
	SetArgs      *HaStatus `json:"set_args,omitempty"`
}

// HaStatusResponse ha status response
type HaStatusResponse struct {
	RowsAffected int `json:"rowsAffected"`
}

// DbStatus api for db_status table
type DbStatus struct {
	Uid      uint       `json:"uid,omitempty"`
	AgentIP  string     `json:"agent_ip,omitempty"`
	IP       string     `json:"ip,omitempty"`
	Port     int        `json:"port,omitempty"`
	DbType   string     `json:"db_type,omitempty"`
	Status   string     `json:"status,omitempty"`
	Cloud    string     `json:"cloud,omitempty"`
	LastTime *time.Time `json:"last_time,omitempty"`
}

// DbStatusRequest request db status
type DbStatusRequest struct {
	DBCloudToken string    `json:"db_cloud_token"`
	BKCloudID    int       `json:"bk_cloud_id"`
	Name         string    `json:"name"`
	QueryArgs    *DbStatus `json:"query_args,omitempty"`
	SetArgs      *DbStatus `json:"set_args,omitempty"`
}

// DbStatusResponse db status response
type DbStatusResponse struct {
	RowsAffected int `json:"rowsAffected"`
	Uid          int `json:"uid"`
}

// SwitchQueue api for tb_mon_switch_queue table
type SwitchQueue struct {
	Uid                uint       `json:"uid,omitempty"`
	IP                 string     `json:"ip,omitempty"`
	Port               int        `json:"port,omitempty"`
	ConfirmCheckTime   *time.Time `json:"confirm_check_time,omitempty"`
	DbRole             string     `json:"db_role,omitempty"`
	SlaveIP            string     `json:"slave_ip,omitempty"`
	SlavePort          int        `json:"slave_port,omitempty"`
	Status             string     `json:"status,omitempty"`
	ConfirmResult      string     `json:"confirm_result,omitempty"`
	SwitchStartTime    *time.Time `json:"switch_start_time,omitempty"`
	SwitchFinishedTime *time.Time `json:"switch_finished_time,omitempty"`
	SwitchResult       string     `json:"switch_result,omitempty"`
	Remark             string     `json:"remark,omitempty"`
	App                string     `json:"app,omitempty"`
	DbType             string     `json:"db_type,omitempty"`
	Idc                string     `json:"idc,omitempty"`
	Cloud              string     `json:"cloud,omitempty"`
	Cluster            string     `json:"cluster,omitempty"`
}

// SwitchQueueRequest request switch queue
type SwitchQueueRequest struct {
	DBCloudToken string       `json:"db_cloud_token"`
	BKCloudID    int          `json:"bk_cloud_id"`
	Name         string       `json:"name"`
	QueryArgs    *SwitchQueue `json:"query_args,omitempty"`
	SetArgs      *SwitchQueue `json:"set_args,omitempty"`
}

// SwitchQueueResponse switch queue response
type SwitchQueueResponse struct {
	RowsAffected int  `json:"rowsAffected"`
	Uid          uint `json:"uid"`
}

// HaLogs api for ha_logs table
type HaLogs struct {
	Uid      uint       `json:"uid,omitempty"`
	IP       string     `json:"ip,omitempty"`
	Port     int        `json:"port,omitempty"`
	MonIP    string     `json:"mon_ip,omitempty"`
	Module   string     `json:"module,omitempty"`
	Cloud    string     `json:"cloud,omitempty"`
	DateTime *time.Time `json:"date_time,omitempty"`
	Comment  string     `json:"comment,omitempty"`
}

// HaLogsRequest request ha_logs table
type HaLogsRequest struct {
	DBCloudToken string  `json:"db_cloud_token"`
	BKCloudID    int     `json:"bk_cloud_id"`
	Name         string  `json:"name"`
	QueryArgs    *HaLogs `json:"query_args,omitempty"`
	SetArgs      *HaLogs `json:"set_args,omitempty"`
}

// HaLogsResponse response for ha_logs
type HaLogsResponse struct {
	RowsAffected int `json:"rowsAffected"`
}

// SwitchLogs api for switch_logs table
type SwitchLogs struct {
	UID      uint       `json:"uid,omitempty"`
	SwitchID uint       `json:"sw_id,omitempty"`
	IP       string     `json:"ip,omitempty"`
	Result   string     `json:"result,omitempty"`
	Datetime *time.Time `json:"datetime,omitempty"`
	Comment  string     `json:"comment,omitempty"`
	Port     int        `json:"port,omitempty"`
}

// SwitchLogRequest request switch log
type SwitchLogRequest struct {
	DBCloudToken string      `json:"db_cloud_token"`
	BKCloudID    int         `json:"bk_cloud_id"`
	Name         string      `json:"name"`
	QueryArgs    *SwitchLogs `json:"query_args,omitempty"`
	SetArgs      *SwitchLogs `json:"set_args,omitempty"`
}

// SwitchLogResponse switch log response
type SwitchLogResponse struct {
	RowsAffected int `json:"rowsAffected"`
}

// AgentIp agent ip info
type AgentIp struct {
	Ip string `json:"ip"`
}

// NewHaDBClient init hadb client object
func NewHaDBClient(conf *config.APIConfig, cloudId int) (*HaDBClient, error) {
	c, err := NewAPIClient(conf, constvar.HaDBName, cloudId)
	return &HaDBClient{c}, err
}

// AgentGetGMInfo get gm info from hadb
func (c *HaDBClient) AgentGetGMInfo() ([]GMInfo, error) {
	req := HaStatusRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         constvar.AgentGetGMInfo,
		QueryArgs: &HaStatus{
			Module: constvar.GM,
			Cloud:  strconv.Itoa(c.CloudId),
		},
	}

	log.Logger.Debugf("AgentGetGMInfo param:%v", req)

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
		QueryArgs: &DbStatus{
			AgentIP: agentIp,
			IP:      ip,
			Port:    port,
		},
		SetArgs: &DbStatus{
			DbType:   dbType,
			Status:   status,
			Cloud:    strconv.Itoa(c.CloudId),
			LastTime: &currentTime,
		},
	}

	log.Logger.Debugf("update instance status param:%v", updateReq)

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
		SetArgs: &DbStatus{
			AgentIP:  agentIp,
			IP:       ip,
			Port:     port,
			DbType:   dbType,
			Status:   status,
			Cloud:    strconv.Itoa(c.CloudId),
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
		SetArgs: &HaLogs{
			IP:      ip,
			Port:    port,
			MonIP:   util.LocalIp,
			Module:  module,
			Cloud:   strconv.Itoa(c.CloudId),
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
	ip string, port int, module string, city string, campus string, dbType string,
) error {
	var result HaStatusResponse

	req := HaStatusRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         constvar.RegisterDBHAInfo,
		QueryArgs: &HaStatus{
			IP:     ip,
			Module: module,
			DbType: dbType,
		},
		SetArgs: &HaStatus{
			IP:     ip,
			Port:   port,
			Module: module,
			City:   city,
			Campus: campus,
			Cloud:  strconv.Itoa(c.CloudId),
			DbType: dbType,
			Status: constvar.RUNNING,
		},
	}

	log.Logger.Debugf("RegisterDBHAInfo param:%v", req)

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
		QueryArgs: &HaStatus{
			IP:       ip,
			DbType:   dbType,
			Module:   constvar.Agent,
			Status:   constvar.RUNNING,
			Cloud:    strconv.Itoa(c.CloudId),
			LastTime: &currentTime,
		},
	}

	log.Logger.Debugf("GetAliveAgentInfo param:%v", req)

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
		QueryArgs: &HaStatus{
			Module:   constvar.GM,
			Cloud:    strconv.Itoa(c.CloudId),
			LastTime: &currentTime,
		},
	}

	log.Logger.Debugf("GetAliveGMInfo param:%v", req)

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
func (c *HaDBClient) ReporterAgentHeartbeat(dbType string, interval int) error {
	var result HaStatusResponse

	currentTime := time.Now()
	req := HaStatusRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         constvar.ReporterAgentHeartbeat,
		QueryArgs: &HaStatus{
			IP:     util.LocalIp,
			DbType: dbType,
		},
		SetArgs: &HaStatus{
			ReportInterval: interval,
			LastTime:       &currentTime,
		},
	}

	log.Logger.Debugf("ReporterAgentHeartbeat param:%v", req)

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
		QueryArgs: &HaStatus{
			IP:     util.LocalIp,
			Module: module,
		},
		SetArgs: &HaStatus{
			ReportInterval: interval,
			LastTime:       &currentTime,
		},
	}

	log.Logger.Debugf("ReporterGMHeartbeat param:%v", req)

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
		QueryArgs: &SwitchQueue{
			IP:               ip,
			Port:             port,
			ConfirmCheckTime: &confirmTime,
		},
	}

	log.Logger.Debugf("QuerySingleTotal param:%v", req)

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
		QueryArgs: &SwitchQueue{
			ConfirmCheckTime: &confirmTime,
		},
	}

	log.Logger.Debugf("QueryIntervalTotal param:%v", req)

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
func (c *HaDBClient) QuerySingleIDC(ip string, idc string) (int, error) {
	var result struct {
		Count int `json:"count"`
	}

	confirmTime := time.Now().Add(-time.Minute)
	req := SwitchQueueRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         constvar.QuerySingleIDC,
		QueryArgs: &SwitchQueue{
			IP:               ip,
			Idc:              idc,
			ConfirmCheckTime: &confirmTime,
		},
	}

	log.Logger.Debugf("QuerySingleIDC param:%v", req)

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
		QueryArgs: &SwitchQueue{
			IP:   ip,
			Port: port,
			App:  app,
		},
	}

	log.Logger.Debugf("UpadteTimeDelay param:%v", req)

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
func (c *HaDBClient) InsertSwitchQueue(ip string, port int, idc string, confirmCheckTime time.Time,
	app string, dbType string, cluster string) (uint, error) {
	var result SwitchQueueResponse

	currentTime := time.Now()
	req := SwitchQueueRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         constvar.InsertSwitchQueue,
		SetArgs: &SwitchQueue{
			IP:               ip,
			Port:             port,
			Idc:              idc,
			App:              app,
			ConfirmCheckTime: &confirmCheckTime,
			DbType:           dbType,
			Cloud:            strconv.Itoa(c.CloudId),
			Cluster:          cluster,
			SwitchStartTime:  &currentTime,
		},
	}

	log.Logger.Debugf("InsertSwitchQueue param:%v", req)

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

	log.Logger.Debugf("QuerySlaveCheckConfig param:%v", req)

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
func (c *HaDBClient) UpdateSwitchQueue(uid uint, ip string, port int, status string,
	slaveIp string, slavePort int, confirmResult string, switchResult string, dbRole string) error {
	var result SwitchQueueResponse

	currentTime := time.Now()
	req := SwitchQueueRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Name:         constvar.UpdateSwitchQueue,
		QueryArgs: &SwitchQueue{
			Uid: uid,
		},
		SetArgs: &SwitchQueue{
			IP:                 ip,
			Port:               port,
			Status:             status,
			ConfirmResult:      confirmResult,
			SwitchResult:       switchResult,
			DbRole:             dbRole,
			SlaveIP:            slaveIp,
			SlavePort:          slavePort,
			SwitchFinishedTime: &currentTime,
		},
	}

	log.Logger.Debugf("UpdateSwitchQueue param:%v", req)

	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.SwitchQueueUrl, ""), req, nil)
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
		SetArgs: &SwitchLogs{
			SwitchID: swId,
			IP:       ip,
			Port:     port,
			Result:   result,
			Comment:  comment,
			Datetime: &switchFinishTime,
		},
	}

	log.Logger.Debugf("InsertSwitchLog param:%v", req)

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
		log.Logger.Fatalf(err.Error())
		return mod, modValue, err
	}
	return mod, modValue, nil
}
