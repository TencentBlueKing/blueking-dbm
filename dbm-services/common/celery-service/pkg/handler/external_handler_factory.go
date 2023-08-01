package handler

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os/exec"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/pkg/errors"

	"celery-service/pkg/config"
)

type ExternalHandler struct {
	et          *config.ExternalTask
	handlerFunc gin.HandlerFunc
}

func (e *ExternalHandler) ClusterType() string {
	return e.et.ClusterType
}

func (e *ExternalHandler) Name() string {
	return e.et.Name
}

func (e *ExternalHandler) Handler() gin.HandlerFunc {
	return e.handlerFunc
}

func newExternalHandler(et *config.ExternalTask) *ExternalHandler {
	return &ExternalHandler{
		et: et,
		handlerFunc: func(ctx *gin.Context) {
			cmd, err := newCommand(et, ctx)
			if err != nil {
				et.Logger.Error(err.Error())
				ctx.JSON(
					http.StatusBadRequest,
					gin.H{
						"code": 1,
						"data": "",
						"msg":  err.Error(),
					})
				return
			}

			err = runCommand(ctx, et, cmd)
			if err != nil {
				et.Logger.Error(err.Error())
				ctx.JSON(
					http.StatusInternalServerError,
					gin.H{
						"code": 1,
						"data": "",
						"msg":  err.Error(),
					})
				return
			}

			ctx.JSON(
				http.StatusOK,
				gin.H{
					"code": 0,
					"data": "",
					"msg":  "",
				})
			return
		},
	}
}

func addExternalHandler(et *config.ExternalTask) {
	if _, ok := Handlers[et.ClusterType]; !ok {
		Handlers[et.ClusterType] = []IHandler{}
	}

	Handlers[et.ClusterType] = append(
		Handlers[et.ClusterType],
		newExternalHandler(et),
	)
}

func wait(cmd *exec.Cmd) chan error {
	ec := make(chan error)
	go func() {
		ec <- cmd.Wait()
	}()
	return ec
}

func logOutput(et *config.ExternalTask, r io.Reader, logFunc func(string, ...any), latestCache *string) chan error {
	ec := make(chan error)
	go func() {
		scanner := bufio.NewScanner(r)
		scanner.Split(bufio.ScanLines)
		for scanner.Scan() {
			line := scanner.Text()
			logFunc(line)
			latestCache = &line
		}
		// 命令正常返回会关闭 pipeline, 这里也会触发一个错误
		//if err := scanner.Err(); err != nil {
		//	ec <- err
		//}
	}()
	return ec
}

func newCommand(et *config.ExternalTask, ctx *gin.Context) (*exec.Cmd, error) {
	body, err := io.ReadAll(ctx.Request.Body)
	if err != nil {
		return nil, err
	}

	var postArgs []string
	if len(body) > 0 {
		if err := json.Unmarshal(body, &postArgs); err != nil {
			return nil, err
		}
	}

	ex, args := newExecAndArgs(et, postArgs)
	cmd := exec.Command(ex, args...)
	//cmd.Env = os.Environ() // 似乎是默认行为

	return cmd, nil
}

func newExecAndArgs(et *config.ExternalTask, postArgs []string) (ex string, args []string) {
	splitExec := strings.Split(et.Executable, " ")

	switch et.Language {
	case "sh", "shell":
		ex = "sh"
		args = mergeSlices([]string{"-c"}, splitExec, et.Args, postArgs)
	case "bash":
		ex = "bash"
		args = mergeSlices([]string{"-c"}, splitExec, et.Args, postArgs)
	case "python", "python2", "python3", "perl":
		ex = et.Language
		args = mergeSlices(splitExec, et.Args, postArgs)
	case "binary":
		ex = splitExec[0]
		args = mergeSlices(splitExec[1:], et.Args, postArgs)
	}

	return
}

func mergeSlices[S ~[]E, E any](v ...S) S {
	ret := make(S, 0)
	for _, o := range v {
		ret = append(ret, o...)
	}
	return ret
}

func runCommand(ctx *gin.Context, et *config.ExternalTask, cmd *exec.Cmd) error {
	outPipe, err := cmd.StdoutPipe()
	if err != nil {
		return errors.Wrap(err, "get command stdout pipeline")
	}
	defer func() {
		_ = outPipe.Close()
	}()

	errPipe, err := cmd.StderrPipe()
	if err != nil {
		return errors.Wrap(err, "get command stderr, pipeline")
	}
	defer func() {
		_ = errPipe.Close()
	}()

	if err := cmd.Start(); err != nil {
		return errors.Wrap(err, "command start failed")
	}

	err = gatherCommandOutput(ctx, et, cmd, outPipe, errPipe)
	if err != nil {
		return err
	}

	return nil
}

/*
1. 所有 stdout 记录到日志文件
2. 所有 stderr 记录到日志文件
3. 返回 exit 信息
*/
func gatherCommandOutput(
	ctx *gin.Context, et *config.ExternalTask, cmd *exec.Cmd, stdoutPipe io.Reader, stderrPipe io.Reader) error {

	stdoutChan := logOutput(et, stdoutPipe, et.Logger.Info, &et.LatestStdout)
	stderrChan := logOutput(et, stderrPipe, et.Logger.Error, &et.LatestStderr)
	waitChan := wait(cmd)
	for {
		select {
		case err := <-stdoutChan: // 未启用
			return errors.Wrap(err, "read stdout pipe failed")
		case err := <-stderrChan: // 未启用
			return errors.Wrap(err, "read stderr pipe failed")
		case err := <-waitChan:
			if err == nil {
				return nil
			}
			return errors.Wrap(err, fmt.Sprintf("execute command failed: %s", et.LatestStderr))
		case <-ctx.Request.Context().Done():
			return ctx.Err()
		}
	}
}
