package config

import (
	"fmt"
	"regexp"

	"github.com/spf13/cast"
)

type SSHConfig struct {
	EnableRemote  bool   `json:"enable_remote" ini:"EnableRemote"`
	SshHost       string `json:"ssh_host" ini:"SshHost" validate:"required"`
	SshPort       int    `json:"ssh_port" ini:"SshPort" validate:"required"`
	SshUser       string `json:"ssh_user" ini:"SshUser" validate:"required"`
	SshPass       string `json:"ssh_pass" ini:"SshPass"`
	SshPrivateKey string `json:"ssh_private_key" ini:"SshPrivateKey"`

	NcPort  int    `json:"nc_port" ini:"NcPort"`
	SaveDir string `json:"save_dir" ini:"SaveDir" validate:"required"`
}

// ParseSshDsn
// SSHDsnFormat := "user:pass@ssh(host:port)/dir?ncport=0"
// ssh://user:pass@host:port//data/dbbak
func ParseSshDsn(dsn string) (*SSHConfig, error) {
	//dsnFormat := fmt.Sprintf(`(?P<user>.+):(?P<pass>.+)@ssh\((?P<host>.+):(?P<port>\d+)\)\/(?P<dir>.+)(?P<params>\?.*)?`)
	dsnFormat := fmt.Sprintf(`ssh://(?P<user>.+):(?P<pass>.+)@(?P<host>.+):(?P<port>\d+)\/(?P<dir>.+)(?P<params>\?.*)?`)
	dsnRe := regexp.MustCompile(dsnFormat)
	match := dsnRe.FindStringSubmatch(dsn)
	if len(match) == 0 {
		return nil, fmt.Errorf("invalid ssh dsn: %s", dsn)
	}
	groupNames := dsnRe.SubexpNames()
	result := make(map[string]string)
	for i, name := range groupNames {
		if i != 0 && name != "" { // 第一个分组为空（也就是整个匹配）
			result[name] = match[i]
		}
	}
	return &SSHConfig{
		EnableRemote:  true,
		SshHost:       result["host"],
		SshPort:       cast.ToInt(result["port"]),
		SshUser:       result["user"],
		SshPass:       result["pass"],
		SshPrivateKey: "",
		NcPort:        0,
		SaveDir:       result["dir"],
	}, nil
}
