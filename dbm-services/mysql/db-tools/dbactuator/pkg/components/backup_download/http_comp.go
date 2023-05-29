package backup_download

import (
	"fmt"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/httpclient"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

// DFHttpComp 允许在目标机器上
type DFHttpComp struct {
	Params   DFHttpParam `json:"extend"`
	progress *progress
}

// DFHttpParam TODO
type DFHttpParam struct {
	DFBase
	HttpGet
}

// HttpGet TODO
type HttpGet struct {
	// 下载 url
	Server string `json:"server" validate:"required,url"`
	// 下载哪些文件
	FileList []string `json:"file_list" validate:"required"`
	// 文件存放到本机哪个目录
	PathTgt string `json:"path_tgt" validate:"required"`
	// http url basic auth user
	AuthUser string `json:"auth_user"`
	// http url basic auth pass
	AuthPass string `json:"auth_pass"`
	// curl 命令路径，默认留空. 目前只用于测试 url
	CurlPath    string   `json:"curl_path"`
	CurlOptions []string `json:"curl_options"`

	curlCmd string
}

// Example TODO
func (d *DFHttpComp) Example() interface{} {
	comp := DFHttpComp{
		Params: DFHttpParam{
			DFBase: DFBase{
				BWLimitMB:   30,
				Concurrency: 1,
			},
			HttpGet: HttpGet{
				Server:   "http://server1:8082/datadbbak8082/",
				PathTgt:  "/data/dbbak",
				FileList: []string{"xx.info", "xx"},
				AuthUser: "xx",
				AuthPass: "yy",
			},
		},
	}
	return comp
}

// Init TODO
func (d *DFHttpComp) Init() error {
	if d.Params.CurlPath == "" {
		d.Params.CurlPath = "curl"
	}
	if d.Params.BWLimitMB == 0 {
		d.Params.BWLimitMB = 20
	}
	if !util.StringsHas(d.Params.CurlOptions, "--limit-rate") {
		// d.Params.CurlOptions = append(d.Params.CurlOptions, fmt.Sprintf(" --limit-rate %dm", d.Params.BWLimitMB))
		d.Params.CurlOptions = append(
			d.Params.CurlOptions,
			"--limit-rate", fmt.Sprintf("%dm", d.Params.BWLimitMB),
		)
	}
	if !util.StringsHas(d.Params.CurlOptions, " -s ") {
		d.Params.CurlOptions = append(d.Params.CurlOptions, "-s")
	}
	// -XGET
	if d.Params.AuthUser != "" {
		d.Params.CurlOptions = append(
			d.Params.CurlOptions,
			fmt.Sprintf(`-u "%s:%s"`, d.Params.AuthUser, d.Params.AuthPass),
		)
		/*
			authPassBase64 := base64.StdEncoding.EncodeToString([]byte(d.Params.AuthPass))
			d.Params.CurlOptions = append(d.Params.CurlOptions,
				"-H", fmt.Sprintf(`"Authorization: Basic %s"`, authPassBase64))
		*/
	}
	d.Params.curlCmd = fmt.Sprintf("%s %s", d.Params.CurlPath, strings.Join(d.Params.CurlOptions, " "))
	return nil
}

// PreCheck TODO
func (d *DFHttpComp) PreCheck() error {
	testCurl := fmt.Sprintf("%s '%s'", d.Params.curlCmd, d.Params.Server)
	logger.Info("test command: %s", testCurl)

	if out, err := osutil.ExecShellCommand(false, testCurl); err != nil {
		return err
	} else {
		if !strings.Contains(out, "<pre>") {
			return fmt.Errorf("no file list returned")
		}
	}
	return nil

}

// PostCheck TODO
func (d *DFHttpComp) PostCheck() error {
	return nil
}

// Start TODO
func (d *DFHttpComp) Start() error {
	if d.progress == nil {
		d.progress = &progress{
			Success: []string{},
			Failed:  []string{},
			Todo:    []string{},
			Doing:   []string{},
		}
	}

	fileList := d.Params.FileList
	p := d.Params
	for _, f := range fileList {
		if cmutil.HasElem(f, d.progress.Success) {
			continue
		}
		/*
			shellDownload := fmt.Sprintf("%s '%s%s' -o '%s/%s'",
				p.curlCmd, p.Server, f, p.PathTgt, f)
			logger.Info("download command: %s", shellDownload)
			out, err := osutil.ExecShellCommand(false, shellDownload)
			// 拼接的 curl 命令，可能被攻击。比如 bash -c "curl --limit-rate 20m -s -u \"xx:yy\" http://server1:8082/datadbbak8082/ls  -o /data1/dbbak/ls ;cd .. ; ls"
		*/

		err := httpclient.Download(p.Server, p.PathTgt, f, p.AuthUser, p.AuthPass, p.BWLimitMB)
		if err != nil {
			logger.Error("download %s got error %s", f, err.Error())
			d.progress.Failed = append(d.progress.Failed, f)
			return err
		}
		/*
			else if strings.TrimSpace(out) != "" {
				d.progress.Failed = append(d.progress.Failed, f)
				return fmt.Errorf("download %s expect stdout is empty, got %s", f, out)
			}
		*/
		d.progress.Success = append(d.progress.Success, f)
	}
	return nil
}

// WaitDone TODO
func (d *DFHttpComp) WaitDone() error {
	totalList := d.Params.FileList
	for true {
		if len(d.progress.Success)+len(d.progress.Failed) < len(totalList) && len(totalList) > 0 {
			time.Sleep(5 * time.Second)
		} else {
			break
		}
	}
	logger.Info("files download %+v", d.progress)
	if len(d.progress.Failed) > 0 {
		return fmt.Errorf("files download failed %d", len(d.progress.Failed))
	}
	return nil
}
