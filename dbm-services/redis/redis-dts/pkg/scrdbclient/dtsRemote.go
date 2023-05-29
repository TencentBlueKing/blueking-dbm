package scrdbclient

import (
	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/util"
	"encoding/json"
	"fmt"
	"log"
	"net/http"

	"github.com/spf13/viper"
	"go.uber.org/zap"
)

// IsDtsServerInBlachList dts_server是否在黑名单中
func (c *Client) IsDtsServerInBlachList(dtsSvr string) bool {
	type inBlacklistReq struct {
		IP string `json:"ip"`
	}
	type inBlacklistResp struct {
		In bool `json:"in"`
	}
	var subURL string
	param := inBlacklistReq{
		IP: dtsSvr,
	}
	ret := inBlacklistResp{}
	if c.servicename == constvar.DtsRemoteTendisxk8s {
		subURL = constvar.K8sIsDtsSvrInBlacklistURL
	} else if c.servicename == constvar.BkDbm {
		subURL = constvar.DbmIsDtsSvrInBlacklistURL
	}
	data, err := c.Do(http.MethodPost, subURL, param)
	if err != nil {
		return false
	}
	err = json.Unmarshal(data.Data, &ret)
	if err != nil {
		err = fmt.Errorf("IsDtsServerInBlachList unmarshal data fail,err:%v,resp.Data:%s", err.Error(), string(data.Data))
		c.logger.Error(err.Error())
		return false
	}
	if ret.In {
		return true
	}
	return false
}

// IsMyselfInBlacklist 本机器是否在黑名单中
func IsMyselfInBlacklist(logger *zap.Logger) bool {
	myLocalIP, err := util.GetLocalIP()
	if err != nil {
		logger.Error(err.Error())
		log.Fatal(err)
	}
	cli01, err := NewClient(viper.GetString("serviceName"), logger)
	if err != nil {
		log.Fatal(err.Error())
	}
	return cli01.IsDtsServerInBlachList(myLocalIP)
}

// DtsLockKey dts key上锁
func (c *Client) DtsLockKey(lockkey, holder string, ttlSec int) (lockOK bool, err error) {
	type dtsLockKeyReq struct {
		LockKey string `json:"lockkey"`
		Holder  string `json:"holder"`
		TTLSecs int    `json:"ttl_sec"`
	}

	var subURL string
	param := dtsLockKeyReq{
		LockKey: lockkey,
		Holder:  holder,
		TTLSecs: ttlSec,
	}
	var ret bool
	if c.servicename == constvar.DtsRemoteTendisxk8s {
		subURL = constvar.K8sDtsLockKeyURL
	} else if c.servicename == constvar.BkDbm {
		subURL = constvar.DbmDtsLockKeyURL
	}
	data, err := c.Do(http.MethodPost, subURL, param)
	if err != nil {
		return false, err
	}
	err = json.Unmarshal(data.Data, &ret)
	if err != nil {
		err = fmt.Errorf("DtsKeyLock unmarshal data fail,err:%v,resp.Data:%s", err.Error(), string(data.Data))
		c.logger.Error(err.Error())
		return false, err
	}
	return ret, nil
}

// DtsUnLockKey dts key解锁
func (c *Client) DtsUnLockKey(lockkey, holder string, ttlSec int, logger *zap.Logger) (err error) {
	type dtsUnlockKeyReq struct {
		LockKey string `json:"lockkey"`
		Holder  string `json:"holder"`
	}
	var subURL string
	param := dtsUnlockKeyReq{
		LockKey: lockkey,
		Holder:  holder,
	}
	if c.servicename == constvar.DtsRemoteTendisxk8s {
		subURL = constvar.K8sDtsUnlockKeyURL
	} else if c.servicename == constvar.BkDbm {
		subURL = constvar.DbmDtsUnlockKeyURL
	}
	_, err = c.Do(http.MethodPost, subURL, param)
	if err != nil {
		return err
	}
	return nil
}
