//go:build !windows
// +build !windows

package cmutil

import (
	"bytes"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"syscall"

	"github.com/pkg/errors"
)

func ExecCommandAsUser(bash bool, userName, cwd string, cmdName string, args ...string) ([]byte, []byte, error) {
	var cmd *exec.Cmd
	if bash {
		cmdStr := fmt.Sprintf(`%s %s`, cmdName, strings.Join(args, " "))
		cmd = exec.Command("bash", "-c", cmdStr)
	} else {
		if cmdName == "" {
			return nil, nil, errors.Errorf("command name should not be empty:%v", args)
		}
		// args should be list
		cmd = exec.Command(cmdName, args...)
	}
	if cwd != "" {
		cmd.Dir = cwd
	}
	if userName != "" {
		currentUser := os.Getenv("USER")
		if currentUser == userName {
			// cmd.Env = append(cmd.Env, fmt.Sprintf("USER=%s", userName))
		} else if currentUser != userName && currentUser == "root" {
			uid, gid, err := GetOSUserId(userName)
			if err != nil {
				return nil, nil, err
			}
			cmd.SysProcAttr = &syscall.SysProcAttr{
				Setpgid: true,
				Credential: &syscall.Credential{
					Uid: uint32(uid),
					Gid: uint32(gid),
				},
			}
		} else if currentUser != "root" {
			return nil, nil, errors.Errorf("current user is not root, but %s", currentUser)
		}
	}
	cmd.Env = append(cmd.Env, fmt.Sprintf(
		"PATH=%s:/bin:/usr/bin:/usr/local/bin:/sbin:/usr/sbin:/usr/local/sbin", os.Getenv("PATH")),
		fmt.Sprintf("LD_LIBRARY_PATH=%s", os.Getenv("LD_LIBRARY_PATH")))

	//logger.Info("PATH:%s cmd.Env:%v", os.Getenv("PATH"), cmd.Env)
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		//logger.Error("stdout:%s, stderr:%s, cmd:%s", stdout.String(), stderr.String(), cmd.String())
		return stdout.Bytes(), stderr.Bytes(), err
	}
	return stdout.Bytes(), stderr.Bytes(), nil
}
