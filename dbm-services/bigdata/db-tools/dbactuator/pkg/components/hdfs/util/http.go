package util

import (
	"io/ioutil"
	"net/http"

	"dbm-services/common/go-pubpkg/logger"
)

// HttpGet TODO
func HttpGet(url string) ([]byte, error) {
	var responseBody []byte
	request, _ := http.NewRequest("GET", url, nil)
	response, err := http.DefaultClient.Do(request)
	if err != nil {
		logger.Error("http get request failed %s", err.Error())
		return responseBody, err
	}
	defer response.Body.Close()
	if response.StatusCode == 200 {
		logger.Debug("http get response code is 200")
	} else {
		logger.Error("http get failed, status code is %d", response.StatusCode)
	}

	return ioutil.ReadAll(response.Body)

}
