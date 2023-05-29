package tencent_test

import (
	"fmt"
	"os"
	"testing"

	cbs "github.com/tencentcloud/tencentcloud-sdk-go/tencentcloud/cbs/v20170312"
	"github.com/tencentcloud/tencentcloud-sdk-go/tencentcloud/common"
	"github.com/tencentcloud/tencentcloud-sdk-go/tencentcloud/common/errors"
	"github.com/tencentcloud/tencentcloud-sdk-go/tencentcloud/common/profile"
	"github.com/tencentcloud/tencentcloud-sdk-go/tencentcloud/common/regions"
)

func TestDescribeTencentCloud(t *testing.T) {
	// 必要步骤：
	// 实例化一个认证对象，入参需要传入腾讯云账户密钥对 SecretId，SecretKey。
	// 硬编码密钥到代码中有可能随代码泄露而暴露，有安全隐患，并不推荐。
	// 为了保护密钥安全，建议将密钥设置在环境变量中或者配置文件中，请参考本文凭证管理章节。
	// credential := common.NewCredential("SecretId", "SecretKey")
	credential := common.NewCredential(
		os.Getenv("SecretId"),
		os.Getenv("SecretKey"),
	)

	// 非必要步骤
	// 实例化一个客户端配置对象，可以指定超时时间等配置
	cpf := profile.NewClientProfile()
	// SDK默认使用POST方法。
	// 如果你一定要使用GET方法，可以在这里设置。GET方法无法处理一些较大的请求。
	// 如非必要请不要修改默认设置。
	cpf.HttpProfile.ReqMethod = "POST"
	// SDK有默认的超时时间，如非必要请不要修改默认设置。
	// 如有需要请在代码中查阅以获取最新的默认值。
	cpf.HttpProfile.ReqTimeout = 30
	// SDK会自动指定域名。通常是不需要特地指定域名的，但是如果你访问的是金融区的服务，
	// 则必须手动指定域名，例如云服务器的上海金融区域名： cvm.ap-shanghai-fsi.tencentcloudapi.com
	cpf.HttpProfile.Endpoint = "cbs.internal.tencentcloudapi.com"
	// SDK默认用TC3-HMAC-SHA256进行签名，它更安全但是会轻微降低性能。
	// 如非必要请不要修改默认设置。
	cpf.SignMethod = "TC3-HMAC-SHA256"
	// SDK 默认用 zh-CN 调用返回中文。此外还可以设置 en-US 返回全英文。
	// 但大部分产品或接口并不支持全英文的返回。
	// 如非必要请不要修改默认设置。
	cpf.Language = "en-US"
	// 打印日志，默认是false
	// cpf.Debug = true

	// 实例化要请求产品(以cvm为例)的client对象
	// 第二个参数是地域信息，可以直接填写字符串ap-guangzhou，或者引用预设的常量
	client, _ := cbs.NewClient(credential, regions.Shanghai, cpf)
	// 实例化一个请求对象，根据调用的接口和实际情况，可以进一步设置请求参数
	// 你可以直接查询SDK源码确定DescribeInstancesRequest有哪些属性可以设置，
	// 属性可能是基本类型，也可能引用了另一个数据结构。
	// 推荐使用IDE进行开发，可以方便的跳转查阅各个接口和数据结构的文档说明。
	request := cbs.NewDescribeDisksRequest()

	// 基本类型的设置。
	// 此接口允许设置返回的实例数量。此处指定为只返回一个。
	// SDK采用的是指针风格指定参数，即使对于基本类型你也需要用指针来对参数赋值。
	// SDK提供对基本类型的指针引用封装函数

	// 数组类型的设置。
	// 此接口允许指定实例 ID 进行过滤，但是由于和接下来要演示的 Filter 参数冲突，先注释掉。
	// request.InstanceIds = common.StringPtrs([]string{"ins-r8hr2upy"})
	request.DiskIds = common.StringPtrs([]string{"disk-qayi7b9k"})
	// 复杂对象的设置。
	// 在这个接口中，Filters是数组，数组的元素是复杂对象Filter，Filter的成员Values是string数组。
	// request.Filters = []*cbs.Filter{
	// 	&cbs.Filter{
	// 		Name:   common.StringPtr("zone"),
	// 		Values: common.StringPtrs([]string{"ap-shanghai-1"}),
	// 	},
	// }

	// 通过client对象调用想要访问的接口，需要传入请求对象
	response, err := client.DescribeDisks(request)
	// 处理异常
	if _, ok := err.(*errors.TencentCloudSDKError); ok {
		fmt.Printf("An API error has returned: %s", err)
		return
	}
	// // 非SDK异常，直接失败。实际代码中可以加入其他的处理。
	if err != nil {
		panic(err)
	}
	// // 打印返回的json字符串
	fmt.Printf("%s\n", response.ToJsonString())
}
