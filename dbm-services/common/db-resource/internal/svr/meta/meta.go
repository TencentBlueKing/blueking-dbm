// Package meta TODO
package meta

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/url"

	"dbm-services/common/db-resource/internal/config"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
)

// GetIdcCityByLogicCityParam TODO
type GetIdcCityByLogicCityParam struct {
	LogicCityName string `json:"logic_city_name"`
}

// IdcCitysResp TODO
type IdcCitysResp struct {
	Code      int      `json:"code"`
	Message   string   `json:"message"`
	Data      []string `json:"data"`
	RequestId string   `json:"request_id"`
}

func getRequestUrl() (string, error) {
	base := config.AppConfig.DbMeta
	if cmutil.IsEmpty(config.AppConfig.DbMeta) {
		base = "http://bk-dbm"
	}
	return url.JoinPath(base, "/apis/proxypass/dbmeta/bk_city_name/")
}

// GetIdcCityByLogicCity TODO
func GetIdcCityByLogicCity(logicCity string) (idcCitys []string, err error) {
	u, err := getRequestUrl()
	if err != nil {
		return
	}
	p := GetIdcCityByLogicCityParam{
		LogicCityName: logicCity,
	}
	client := &http.Client{} // 客户端,被Get,Head以及Post使用
	body, err := json.Marshal(p)
	if err != nil {
		logger.Error("marshal GetIdcCityByLogicCityParam body failed %s ", err.Error())
		return
	}
	request, err := http.NewRequest(u, "application/json;charset=utf-8",
		bytes.NewBuffer(body))
	if err != nil {
		return
	}
	request.AddCookie(&http.Cookie{Name: "bk_app_code", Path: "/", Value: config.AppConfig.BkSecretConfig.BkAppCode,
		MaxAge: 86400})
	request.AddCookie(&http.Cookie{Name: "bk_app_secret", Path: "/", Value: config.AppConfig.BkSecretConfig.BKAppSecret,
		MaxAge: 86400})
	resp, err := client.Do(request)
	if err != nil {
		logger.Error("request /apis/proxypass/dbmeta/bk_city_name/ failed %s", err.Error())
		return
	}
	defer resp.Body.Close()
	content, err := io.ReadAll(resp.Body)
	if err != nil {
		logger.Error("read respone body failed %s", err.Error())
		return
	}
	logger.Info("respone %v", string(content))
	var d IdcCitysResp
	if err = json.Unmarshal(content, &d); err != nil {
		return
	}
	return d.Data, nil
}
