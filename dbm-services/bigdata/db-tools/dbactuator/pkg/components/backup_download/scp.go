package backup_download

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/sftp"
	"dbm-services/common/go-pubpkg/logger"
	"fmt"
	"log"
	"time"
)

// DFScpComp 允许在目标机器上
type DFScpComp struct {
	Params DFScpParam `json:"extend"`

	scpConfig sftp.Config
	scpClient sftp.Client
	progress  *progress
}

type progress struct {
	Success []string
	Failed  []string
	Todo    []string
	Doing   []string
}

// DFScpParam TODO
type DFScpParam struct {
	DFBase
	// 下载源
	FileSrc FileSrc `json:"file_src" validate:"required"`
	// 下载目标
	FileTgt FileTgt `json:"file_tgt" validate:"required"`
}

// Example TODO
func (d *DFScpComp) Example() interface{} {
	comp := DFScpComp{
		Params: DFScpParam{
			DFBase: DFBase{
				BWLimitMB:   30,
				Concurrency: 1,
			},
			FileSrc: FileSrc{
				Path:     "/data/dbbak",
				FileList: []string{"xx.info", "xx"},
				SSHConfig: SSHConfig{
					SshHost: "source_host",
					SshPort: "22",
					SshUser: "mysql",
					SshPass: "xx",
				},
			},
			FileTgt: FileTgt{
				Path: "/data/dbbak",
			},
		},
	}
	return comp
}

// Init TODO
func (d *DFScpComp) Init() error {
	src := d.Params.FileSrc.SSHConfig
	scpConfig := sftp.Config{
		Username: src.SshUser,
		Password: src.SshPass,
		Server:   fmt.Sprintf("%s:%s", src.SshHost, src.SshPort),
		Timeout:  time.Second * 10,
	}
	if scpClient, err := sftp.New(scpConfig); err != nil {
		return err
	} else {
		scpClient.Close()
		// d.sshClient = sshClient
	}
	d.scpConfig = scpConfig

	if d.Params.BWLimitMB == 0 {
		d.Params.BWLimitMB = 20 // 20 MB/s by default
	}
	return nil
}

// PreCheck TODO
func (d *DFScpComp) PreCheck() error {
	// 创建本地目录
	return nil
}

// PostCheck TODO
func (d *DFScpComp) PostCheck() error {
	// 文件数、文件md5、文件连续性校验
	return nil
}

// Start TODO
func (d *DFScpComp) Start() error {
	if d.progress == nil {
		d.progress = &progress{
			Success: []string{},
			Failed:  []string{},
			Todo:    []string{},
			Doing:   []string{},
		}
	}

	fileList := d.Params.FileSrc.FileList
	p := d.Params
	for _, f := range fileList {
		if util.HasElem(f, d.progress.Success) {
			continue
		}
		err := sftp.Download(d.scpConfig, p.FileSrc.Path, p.FileTgt.Path, f, p.BWLimitMB) // @todo 下载超时2h
		if err != nil {
			log.Println(err)
			d.progress.Failed = append(d.progress.Failed, f)
			return err
		}
		d.progress.Success = append(d.progress.Success, f)
	}

	return nil
}

// Pause TODO
func (d *DFScpComp) Pause() error {
	return nil
}

// Stop TODO
func (d *DFScpComp) Stop() error {
	return nil
}

// Resume TODO
func (d *DFScpComp) Resume() error {
	return d.Start()
}

// Rollback TODO
func (d *DFScpComp) Rollback() error {
	return nil
}

// GetStatus TODO
func (d *DFScpComp) GetStatus() error {
	return nil
}

// WaitDone TODO
func (d *DFScpComp) WaitDone() error {
	totalList := d.Params.FileSrc.FileList
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

// SSHConfig ssh信息
type SSHConfig struct {
	SshHost string `json:"ssh_host" validate:"required"`
	SshPort string `json:"ssh_port" validate:"required"`
	SshUser string `json:"ssh_user" validate:"required"`
	SshPass string `json:"ssh_pass"`
}

// FileSrc TODO
type FileSrc struct {
	// scp 源机器地址
	SSHConfig
	// 源文件所在目录
	Path  string `json:"path" validate:"required"`
	Match string `json:"match"`
	// 源文件名列表，相对上面的 path
	FileList []string `json:"file_list" validate:"required"`
}

// FileTgt TODO
type FileTgt struct {
	// 文件下载目标目录
	Path string `json:"path" validate:"required"`
}
