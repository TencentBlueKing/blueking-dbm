package httpclient

import (
	"encoding/base64"
	"fmt"
	"io"
	"net/http"
	"os"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
)

// Download TODO
func Download(server, dstDir string, fileName string, authUser, authPass string, bwlimitMB int64) error {
	srcFile := fmt.Sprintf("%s%s", server, fileName)
	tgtFile := fmt.Sprintf("%s/%s", dstDir, fileName)
	if fileName == "" {
		return fmt.Errorf("fileName to download cannot be empty")
		// tgtFile = fmt.Sprintf("%s/%s", dstDir, "__empty_file_list__")
	}
	logger.Info("start download to %s", tgtFile)
	f, err := os.Create(tgtFile)
	if err != nil {
		return err
	}
	defer f.Close()
	resp, err := DoWithBA(http.MethodGet, srcFile, nil, authUser, authPass)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("bad status: %s", resp.Status)
	}
	done := make(chan int, 1)
	defer close(done)
	go func(chan int) {
		osutil.PrintFileSizeIncr(tgtFile, 1, 10, logger.Info, done)
	}(done)
	_, err = util.IOLimitRate(f, resp.Body, bwlimitMB)
	if err != nil {
		return err
	}
	return nil
}

func basicAuth(username, password string) string {
	auth := username + ":" + password
	return base64.StdEncoding.EncodeToString([]byte(auth))
}

func redirectPolicyFunc(req *http.Request, via []*http.Request) error {
	req.Header.Add("Authorization", "Basic "+basicAuth("username1", "password123"))
	return nil
}

// DoWithBA TODO
// http do with basic auth
func DoWithBA(method string, url string, payload io.Reader, username, password string) (*http.Response, error) {
	req, err := http.NewRequest(method, url, payload)
	if err != nil {
		return nil, err
	}
	// Set the auth for the request.
	req.SetBasicAuth(username, password)

	client := &http.Client{
		CheckRedirect: redirectPolicyFunc,
	}
	return client.Do(req)
}
