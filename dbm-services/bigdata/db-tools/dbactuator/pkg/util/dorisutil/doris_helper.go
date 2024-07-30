package dorisutil

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
	"fmt"
	"io"
	"net/http"
)

// GetLocalNetwork 获取本地网络
func GetLocalNetwork() (string, error) {
	return osutil.ExecShellCommand(false, "ip a|grep eth1|grep inet |awk '{print $2}'")
}

// StartFeByHelper 通过helper启动fe
func StartFeByHelper(dorisHomeDir string, role string, masterIp string, rpcPort int) error {

	_, err := osutil.ExecShellCommand(false, fmt.Sprintf(
		"su - mysql -c \"%s/%s/bin/start_fe.sh --helper %s:%d --daemon\"",
		dorisHomeDir, role, masterIp, rpcPort))
	return err
}

// HttpGet 执行HTTP Get请求
func HttpGet(url string) ([]byte, error) {
	var responseBody []byte
	// 创建 GET 请求
	request, _ := http.NewRequest("GET", url, nil)
	// 发送请求并获取响应
	response, err := http.DefaultClient.Do(request)
	if err != nil {
		logger.Error("http get request failed %s", err.Error())
		return responseBody, err
	}
	defer response.Body.Close()
	// 检查响应状态码
	if response.StatusCode == 200 {
		logger.Debug("http get response code is 200")
	} else {
		logger.Error("http get failed, status code is %d", response.StatusCode)
	}
	// 读取响应体
	responseBody, err = io.ReadAll(response.Body)
	if err != nil {
		logger.Error("failed to read response body: %s", err.Error())
		return responseBody, err
	}
	return responseBody, nil
}
