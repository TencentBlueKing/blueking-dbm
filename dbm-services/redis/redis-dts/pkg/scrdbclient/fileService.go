package scrdbclient

import (
	"fmt"
	"net/http"
)

// GetFile from fileserver
func (c *Client) GetFile(fileStr string) (*http.Response, error) {
	var resp *http.Response
	var err error

	fullUrl := c.apiserver + "/fileserver/" + fileStr
	resp, err = http.Get(fullUrl)
	if err != nil {
		err = fmt.Errorf("http.Get fail,err:%v,fullURL:%s", err, fullUrl)
		c.logger.Error(err.Error())
		return nil, err
	}
	return resp, err
}
