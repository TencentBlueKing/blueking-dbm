// Package yunti get machine info  function
package yunti

import (
	"bk-dbconfig/pkg/core/logger"
	"bytes"
	"crypto/hmac"
	"crypto/sha1"
	"encoding/hex"
	"encoding/json"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"time"
)

// BaseParam BaseParam
type BaseParam struct {
	Id      string `json:"id"`
	Jsonrpc string `json:"jsonrpc"`
	Method  string `json:"method"`
}

// QueryCVMInstancesParam QueryCVMInstancesParam
type QueryCVMInstancesParam struct {
	BaseParam
	Params QueryCvmParam `json:"params"`
}

// QueryCvmParam QueryCvmParam
type QueryCvmParam struct {
	OrderId         []string `json:"orderId"`
	LanIp           []string `json:"lanIp"`
	InstanceAssetId []string `json:"instanceAssetId"`
}

// QueryCVMInstancesRespone respone data
type QueryCVMInstancesRespone struct {
	Id       string `json:"id"`
	Jsonrpc  string `json:"jsonrpc"`
	XTraceId string `json:"x_trace_id"`
	Result   struct {
		Total     int              `json:"total"`
		NextToken int              `json:"nextToken"`
		Data      []InstanceDetail `json:"data"`
	} `json:"result"`
}

// InstanceDetail InstanceDetail
type InstanceDetail struct {
	Cpu                int           `json:"cpu"`
	Memory             int           `json:"memory"`
	SystemDiskDisksize int           `json:"systemDiskDisksize"`
	InstanceType       string        `json:"instanceType"`
	LanIp              string        `json:"lanIp"`
	DatadiskList       []CvmDataDisk `json:"datadiskList"`
	CloudCampusName    string        `json:"cloudCampusName"`
	InstanceAssetId    string        `json:"instanceAssetId"`
}

// CvmDataDisk CvmDataDisk
type CvmDataDisk struct {
	DiskSize int    `json:"DiskSize"`
	DiskType string `json:"DiskType"`
	DiskId   string `json:"DiskId"`
}

// YuntiConfig yunti params
type YuntiConfig struct {
	Addr          string `yaml:"addr"`
	ApiKeyName    string `yaml:"api_key_name" mapstructure:"api_key_name"`
	ApiKeySecret  string `yaml:"api_key_secret" mapstructure:"api_key_secret"`
	InterfaceName string `yaml:"interface_name" mapstructure:"interface_name"`
}

// IsNotEmpty TODO
func (y YuntiConfig) IsNotEmpty() bool {
	var empty YuntiConfig
	return y != empty
}

// GetDataDiskTotalSize 计算磁盘大小之和
func GetDataDiskTotalSize(dataDiskList []CvmDataDisk) int {
	var totalSize int
	for _, v := range dataDiskList {
		totalSize += v.DiskSize
	}
	return totalSize
}

// GetUrl  interfaceName apply/api或者account/api等组件路由名称
// apiName 具体方法名，和method一致
func (y *YuntiConfig) GetUrl() string {
	rqv := url.Values{}
	timeStr := strconv.FormatInt(time.Now().Unix(), 10)
	rqv.Set("api_key", y.ApiKeyName)
	rqv.Set("api_sign", getSign(timeStr, y.ApiKeyName, y.ApiKeySecret))
	rqv.Set("api_ts", timeStr)
	u := url.URL{
		Scheme:   "http",
		Host:     y.Addr,
		Path:     y.InterfaceName,
		RawQuery: rqv.Encode(),
	}
	return u.String()
}

func hmacSHA1(apiKeySecret string, signData string) string {
	mac := hmac.New(sha1.New, []byte(apiKeySecret))
	mac.Write([]byte(signData))
	return hex.EncodeToString(mac.Sum(nil))
}

func getSign(time, apiKeyName, apiKeySecret string) string {
	signData := time + apiKeyName
	return hmacSHA1(apiKeySecret, signData)
}

// QueryCVMInstances 查询虚拟机
func (y *YuntiConfig) QueryCVMInstances(ipList []string) (d QueryCVMInstancesRespone, err error) {
	addr := y.GetUrl()
	cli := &http.Client{}
	p := QueryCVMInstancesParam{
		BaseParam: BaseParam{
			Jsonrpc: "2.0",
			Method:  "queryCVMInstances",
			Id:      "1",
		},
		Params: QueryCvmParam{
			LanIp: ipList,
			//	InstanceAssetId: []string{"TC220512001056"},
		},
	}
	bp, err := json.Marshal(p)
	if err != nil {
		return d, err
	}
	var bodyContent []byte
	req, err := http.NewRequest(http.MethodPost, addr, bytes.NewReader(bp))
	if err != nil {
		return d, err
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := cli.Do(req)
	if err != nil {
		return d, err
	}
	defer resp.Body.Close()
	if resp.Body != nil {
		bodyContent, err = io.ReadAll(resp.Body)
		if err != nil {
			return d, err
		}
	}
	if err = json.Unmarshal(bodyContent, &d); err != nil {
		logger.Error("yunti bodyContent %s", string(bodyContent))
		return d, err
	}
	return d, nil
}
