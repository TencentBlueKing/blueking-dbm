package mysql

import (
	"encoding/json"
	"fmt"
	"strings"

	"dbm-services/common/go-pubpkg/logger"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
)

// OSCmdRunComp TODO
type OSCmdRunComp struct {
	Params   OSCmds `json:"extend"`
	results  []*SimpleCmdResult
	errIndex int
}

// OSCmds TODO
type OSCmds struct {
	Cmds    []SimpleCmd `json:"cmds" validate:"required"`
	WorkDir string      `json:"work_dir"`
	RunUser string      `json:"run_user"`
}
type SimpleCmd struct {
	CmdName string   `json:"cmd_name" validate:"required"`
	CmdArgs []string `json:"cmd_args"`
}

type SimpleCmdResult struct {
	CmdLine   string `json:"cmd_line"`
	CmdStdout string `json:"cmd_stdout"`
	CmdStderr string `json:"cmd_stderr"`
	ErrMsg    string `json:"err_msg"`
	err       error
}

type OSCmdRunResp struct {
	Code    int                `json:"code"`
	Message string             `json:"message"`
	Data    []*SimpleCmdResult `json:"data"`
}

func (s *SimpleCmd) Run(workDir string) *SimpleCmdResult {
	cmdLine := fmt.Sprintf(`%s %s`, s.CmdName, strings.Join(s.CmdArgs, " "))
	cmdResult := &SimpleCmdResult{CmdLine: cmdLine}
	if strings.Contains(cmdLine, ";") {
		cmdResult.err = errors.New("danger cmd")
		cmdResult.ErrMsg = cmdResult.err.Error()
		return cmdResult
	}
	fmt.Println(cmdLine)
	switch s.CmdName {
	case "mkdir", "ls", "cd", "chown", "chmod":
		logger.Info("oscmd_run command:", cmdLine)
		stdout, stderr, err := cmutil.ExecCommand(false, workDir, s.CmdName, s.CmdArgs...)
		cmdResult.CmdStdout = stdout
		cmdResult.CmdStderr = stderr
		cmdResult.err = err
	default:
		cmdResult.err = errors.New("cmd_name is not allowed")
		cmdResult.ErrMsg = cmdResult.err.Error()
		return cmdResult
	}
	if cmdResult.err != nil {
		cmdResult.ErrMsg = cmdResult.err.Error()
	}
	return cmdResult
}

// Example TODO
func (s *OSCmdRunComp) Example() interface{} {
	comp := OSCmdRunComp{
		Params: OSCmds{
			Cmds: []SimpleCmd{
				{CmdName: "mkdir", CmdArgs: []string{"/data/dbbak/123"}},
				{CmdName: "ls", CmdArgs: []string{"/data/dbbak"}},
			}},
	}
	return comp
}

// String 用于打印
func (s *OSCmdRunComp) String() string {
	str, _ := json.Marshal(s)
	return string(str)
}

// Start TODO
func (s *OSCmdRunComp) Start() error {
	s.errIndex = -1
	for i, c := range s.Params.Cmds {
		res := c.Run(s.Params.WorkDir)
		s.results = append(s.results, res)
		if res.err != nil {
			s.errIndex = i
			_ = s.OutputCtx()
			return res.err
		}
	}
	return s.OutputCtx()
}

// WaitDone TODO
func (s *OSCmdRunComp) WaitDone() error {
	return nil
}

// OutputCtx TODO
func (s *OSCmdRunComp) OutputCtx() error {
	var resp OSCmdRunResp
	if s.errIndex >= 0 {
		resp = OSCmdRunResp{
			Message: s.results[s.errIndex].CmdStderr,
			Code:    1,
			Data:    s.results,
		}
	} else {
		resp = OSCmdRunResp{
			Code: 0,
			Data: s.results,
		}
	}
	ss, err := components.WrapperOutput(resp)
	if err != nil {
		return err
	}
	fmt.Println(ss)
	return nil
}
