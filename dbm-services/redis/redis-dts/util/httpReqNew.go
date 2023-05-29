package util

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"

	"go.uber.org/zap"
)

// HTTPPostJSON http POST请求,发送JSON数据
func HTTPPostJSON(url string, params interface{}, logger *zap.Logger) ([]byte, error) {
	var ret []byte
	var err error
	jsonStr, err := json.Marshal(params)
	if err != nil {
		logger.Error("HttpPostJSON json.Marshal fail", zap.Error(err),
			zap.String("url", url), zap.Any("params", params))
		return ret, fmt.Errorf("HttpPostJSON json.Marshal fail,err:%v", err)
	}
	logger.Info("post start ...", zap.String("url", url), zap.Any("params", params))
	req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonStr))
	if err != nil {
		logger.Error("new a post request fail", zap.Error(err),
			zap.String("url", url), zap.Any("params", params))
		return ret, fmt.Errorf("new a post request fail,err:%v,url:%v", err, url)
	}
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		logger.Error("do post request fail", zap.Error(err),
			zap.String("url", url), zap.Any("params", params))
		return ret, fmt.Errorf("do post request fail,err:%v,url:%v", err, url)
	}
	defer resp.Body.Close()

	fmt.Println("response status:", resp.Status)
	// fmt.Println("response headers:", resp.Header)
	// fmt.Println("response body:", resp.Body)
	ret, err = ioutil.ReadAll(resp.Body)
	if err != nil {
		logger.Error("post read response fail", zap.Error(err), zap.Any("respBody", resp.Body), zap.String("url", url),
			zap.Any("params", params))
		return ret, fmt.Errorf("post read response fail,err:%v", err)
	}
	if resp.StatusCode != 200 {
		logger.Error("do post request fail,resp.StatusCode != 200",
			zap.Int("statusCode", resp.StatusCode),
			zap.String("respStatus", resp.Status),
			zap.String("respBody", string(ret)),
			zap.String("url", url), zap.Any("params", params))
		err = fmt.Errorf("do post requst fail,resp.status:%s resp.StatusCode:%d err:%v",
			resp.Status, resp.StatusCode, err)
		return ret, err
	}
	return ret, nil
}

// HTTPGetURLParams http Get请求将参数解析到url中,然后再发送请求
func HTTPGetURLParams(url string, params interface{}, logger *zap.Logger) ([]byte, error) {
	var ret []byte
	var err error
	var jsonStr []byte
	var fullURL string
	if params != nil {
		jsonStr, err = json.Marshal(params)
		if err != nil {
			logger.Error("HttpGetUrlParams json.Marshal fail", zap.Error(err),
				zap.String("url", url), zap.Any("params", params))
			return ret, fmt.Errorf("HttpGetUrlParams json.Marshal fail,err:%v", err)
		}
		paramsMap := make(map[string]interface{})
		if err = json.Unmarshal(jsonStr, &paramsMap); err != nil {
			logger.Error("HttpGetUrlParams json.Unmarshal fail", zap.Error(err),
				zap.String("url", url), zap.Any("params", params))
			return ret, fmt.Errorf("HttpGetUrlParams json.Unmarshal fail,err:%v", err)
		}

		paramsStr := "?"
		for k, v := range paramsMap {
			if len(paramsStr) == 1 {
				paramsStr = paramsStr + fmt.Sprintf("%v=%v", k, v)
			} else {
				paramsStr = paramsStr + fmt.Sprintf("&%v=%v", k, v)
			}
		}
		fullURL = url + paramsStr
	} else {
		fullURL = url
	}
	resp, err := http.Get(fullURL)
	if err != nil {
		logger.Error("do get request fail", zap.Error(err), zap.String("fullURL", fullURL))
		return ret, fmt.Errorf("do get request fail,err:%v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		respStr, _ := json.Marshal(resp)
		logger.Error("get read response fail,resp.StatusCode != 200", zap.Int("statusCode", resp.StatusCode),
			zap.String("respStatus", resp.Status), zap.String("respBody", string(respStr)))
		err = fmt.Errorf("get read response fail,resp.status:%s!=200 resp.StatusCode:%d err:%v", resp.Status, resp.StatusCode,
			err)
		return ret, err
	}

	ret, err = ioutil.ReadAll(resp.Body)
	if err != nil {
		logger.Error("get read response fail", zap.Error(err),
			zap.String("fullURL", fullURL), zap.Any("respBody", resp.Body))
		return ret, fmt.Errorf("get read response fail,err:%v", err)
	}
	return ret, nil
}

// HTTPGetJSON  http Get请求,发送json数据
func HTTPGetJSON(url string, params interface{}, logger *zap.Logger) ([]byte, error) {
	var ret []byte
	var err error
	jsonStr, err := json.Marshal(params)
	if err != nil {
		logger.Error("HttpGetJSON json.Marshal fail", zap.Error(err),
			zap.String("url", url), zap.Any("params", params))
		return ret, fmt.Errorf("HttpGetJSON json.Marshal fail,err:%v", err)
	}
	logger.Info("get start ...", zap.String("url", url), zap.Any("params", params))
	req, err := http.NewRequest("GET", url, bytes.NewBuffer(jsonStr))
	if err != nil {
		logger.Error("new a get request fail", zap.Error(err),
			zap.String("url", url), zap.Any("params", params))
		return ret, fmt.Errorf("new a get request fail,err:%v,url:%v", err, url)
	}
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		logger.Error("do get request fail", zap.Error(err),
			zap.String("url", url), zap.Any("params", params))
		return ret, fmt.Errorf("do get request fail,err:%v,url:%v", err, url)
	}
	defer resp.Body.Close()

	// fmt.Println("response headers:", resp.Header)
	// fmt.Println("response body:", resp.Body)
	fmt.Println("response status:", resp.Status)
	ret, err = ioutil.ReadAll(resp.Body)
	if err != nil {
		logger.Error("get read response fail", zap.Error(err), zap.Any("respBody", resp.Body),
			zap.String("url", url), zap.Any("params", params))
		return ret, fmt.Errorf("get read response fail,err:%v", err)
	}
	if resp.StatusCode != 200 {
		logger.Error("do get json request fail,resp.StatusCode != 200", zap.Int("statusCode", resp.StatusCode),
			zap.String("respStatus", resp.Status), zap.String("respBody", string(ret)),
			zap.String("url", url), zap.Any("params", params))
		err = fmt.Errorf("do get json requst fail,resp.status:%s resp.StatusCode:%d err:%v",
			resp.Status, resp.StatusCode, err)
		return ret, err
	}
	return ret, nil
}
