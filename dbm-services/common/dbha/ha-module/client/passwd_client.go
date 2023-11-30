package client

import (
	"encoding/json"
	"fmt"
	"net/http"

	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/util"
)

// PasswdClient password service client
type PasswdClient struct {
	Client
}

// PasswdInstance the instance info of password
type PasswdInstance struct {
	Ip    string `json:"ip"`
	Port  int    `json:"port"`
	Cloud int    `json:"bk_cloud_id"`
}

// PasswdUser the user info of password
type PasswdUser struct {
	UserName  string `json:"username"`
	Component string `json:"component"`
}

// PasswdItem the item of password response data
type PasswdItem struct {
	Ip         string `json:"ip"`
	Port       int    `json:"port"`
	Cloud      int    `json:"bk_cloud_id"`
	User       string `json:username`
	Passwd     string `json:"password"`
	Component  string `json:"component"`
	LockUtil   string `json:"lock_util"`
	Operator   string `json:"operator"`
	UpdateTime string `json:"update_time"`
}

// GetPasswdRequest the request of password
type GetPasswdRequest struct {
	DBCloudToken string           `json:"db_cloud_token"`
	BKCloudID    int              `json:"bk_cloud_id"`
	Instances    []PasswdInstance `json:"instances"`
	Users        []PasswdUser     `json:"users"`
	Limit        int              `json:"limit"`
	Offset       int              `json:"offset"`
}

// GetPasswdResponse the response of password
type GetPasswdResponse struct {
	Count int          `json:"count"`
	Items []PasswdItem `json:"items"`
}

// NewPasswdClient create new password service instance
func NewPasswdClient(conf *config.APIConfig, cloudId int) *PasswdClient {
	c := NewAPIClient(conf, constvar.DBConfigName, cloudId)
	return &PasswdClient{c}
}

// GetBatchPasswd the batch api for password
func (c *PasswdClient) GetBatchPasswd(
	pins []PasswdInstance, pusers []PasswdUser, limit int,
) ([]PasswdItem, error) {
	rsp := GetPasswdResponse{}
	req := GetPasswdRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Instances:    pins,
		Users:        pusers,
		Limit:        limit,
	}

	log.Logger.Debugf("BatchGetConfigItem param:%v", req)
	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.BKPasswdQueryUrl, ""), req, nil)

	if err != nil {
		return nil, err
	}

	if response.Code != 0 {
		cmdbErr := fmt.Errorf("%s failed, return code:%d, msg:%s",
			util.AtWhere(), response.Code, response.Msg)
		return nil, cmdbErr
	}

	// log.Logger.Debugf("GetBatchPasswd code:%d, rspMsg:%s, rspData:%s",
	//	response.Code, response.Msg, response.Data)
	err = json.Unmarshal(response.Data, &rsp)
	if err != nil {
		return nil, err
	}

	return rsp.Items, nil
}
