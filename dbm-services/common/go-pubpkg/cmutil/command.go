package cmutil

import (
	"bytes"
	"fmt"
	"os"
	"os/exec"
	"strings"

	"github.com/pkg/errors"
)

// ExecShellCommand 执行 shell 命令
// 如果有 err, 返回 stderr; 如果没有 err 返回的是 stdout
// 后续尽量不要用这个方法,因为通过标准错误来判断有点不靠谱
func ExecShellCommand(isSudo bool, param string) (stdoutStr string, err error) {
	if isSudo {
		param = "sudo " + param
	}
	cmd := exec.Command("bash", "-c", param)
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	err = cmd.Run()
	if err != nil {
		// return stderr.String(), err
		return stderr.String(), errors.WithMessage(err, stderr.String())
	}

	if len(stderr.String()) > 0 {
		err = fmt.Errorf("execute shell command(%s) error:%s", param, stderr.String())
		return stderr.String(), err
	}

	return stdout.String(), nil
}

// ExecCommand bash=true: bash -c 'cmdName args', bash=false: ./cmdName args list
// ExecCommand(false, "df", "-k /data") will get `df '-k /data'` error command. you need change it to (false, "df", "-k", "/data")  or (true, "df -k /data")
// bash=false need PATH
// cwd is the command work dir
// return stdout, stderr ,err
func ExecCommand(bash bool, cwd string, cmdName string, args ...string) (string, string, error) {
	stdout, stderr, err := ExecCommandReturnBytes(bash, cwd, cmdName, args...)
	if err != nil {
		return "", "", err
	}
	stdoutStr := strings.TrimSpace(string(stdout))
	stderrStr := strings.TrimSpace(string(stderr))
	return stdoutStr, stderrStr, nil
}

// ExecCommandReturnBytes run exec.Command
// return stdout, stderr ,err
func ExecCommandReturnBytes(bash bool, cwd string, cmdName string, args ...string) ([]byte, []byte, error) {
	var cmd *exec.Cmd
	if bash {
		if cmdName != "" {
			cmdName += " "
		}
		cmdStr := fmt.Sprintf(`%s%s`, cmdName, strings.Join(args, " "))
		cmd = exec.Command("bash", "-c", cmdStr)
	} else {
		if cmdName == "" {
			return nil, nil, errors.Errorf("command name should not be empty:%v", args)
		}
		// args should be list
		cmd = exec.Command(cmdName, args...)
	}
	cmd.Env = []string{
		fmt.Sprintf(
			"PATH=%s:/bin:/usr/bin:/usr/local/bin:/sbin:/usr/sbin:/usr/local/sbin",
			os.Getenv("PATH"),
		),
	}
	if cwd != "" {
		cmd.Dir = cwd
	}
	//logger.Info("PATH:%s cmd.Env:%v", os.Getenv("PATH"), cmd.Env)
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {

		//logger.Error("stdout:%s, stderr:%s, cmd:%s", stdout.String(), stderr.String(), cmd.String())
		return stdout.Bytes(), stderr.Bytes(), errors.Wrap(err, cmd.String())
	}
	return stdout.Bytes(), stderr.Bytes(), nil
}
