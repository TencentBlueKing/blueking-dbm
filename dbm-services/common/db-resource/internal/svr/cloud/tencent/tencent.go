// Package tencent TODO
package tencent

import (
	"fmt"

	"dbm-services/common/db-resource/internal/config"
	"dbm-services/common/go-pubpkg/logger"

	cbs "github.com/tencentcloud/tencentcloud-sdk-go/tencentcloud/cbs/v20170312"
	"github.com/tencentcloud/tencentcloud-sdk-go/tencentcloud/common"
	"github.com/tencentcloud/tencentcloud-sdk-go/tencentcloud/common/errors"
	"github.com/tencentcloud/tencentcloud-sdk-go/tencentcloud/common/profile"
)

var credential *common.Credential
var cpf *profile.ClientProfile

// TencentDisker TODO
var TencentDisker BcsClient

func init() {
	if config.AppConfig.CloudCertificate != nil {
		credential = common.NewCredential(
			config.AppConfig.CloudCertificate.SecretId,
			config.AppConfig.CloudCertificate.SecretKey,
		)
	}
	cpf = profile.NewClientProfile()
	cpf.HttpProfile.ReqTimeout = 30
	// SDK会自动指定域名。通常是不需要特地指定域名的，但是如果你访问的是金融区的服务，
	// 则必须手动指定域名，例如云服务器的上海金融区域名： cvm.ap-shanghai-fsi.tencentcloudapi.com
	cpf.HttpProfile.Endpoint = "cbs.internal.tencentcloudapi.com"
}

// BcsClient TODO
type BcsClient struct{}

// IsOk TODO
func (t BcsClient) IsOk() bool {
	return credential != nil
}

// DescribeDisk TODO
func (t BcsClient) DescribeDisk(diskIds []string, region string) (diskTypeDic map[string]string, err error) {
	client, _ := cbs.NewClient(credential, region, cpf)
	request := cbs.NewDescribeDisksRequest()
	request.DiskIds = common.StringPtrs(diskIds)
	response, err := client.DescribeDisks(request)
	// 处理异常
	if _, ok := err.(*errors.TencentCloudSDKError); ok {
		fmt.Printf("An API error has returned: %s", err)
		return
	}
	// // 非SDK异常，直接失败。实际代码中可以加入其他的处理。
	if err != nil {
		logger.Error("call describe disk failed %s", err.Error())
		return
	}
	logger.Info("disk info %s", response.ToJsonString())
	diskTypeDic = make(map[string]string)
	for _, disk := range response.Response.DiskSet {
		diskTypeDic[*disk.DiskId] = *disk.DiskType
	}
	return
}
