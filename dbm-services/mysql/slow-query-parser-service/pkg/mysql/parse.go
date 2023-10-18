package mysql

import (
	"bytes"
	"encoding/json"
	"io"
	"log/slog"
	"os"
	"os/exec"
)

// ParserPath TODO
var ParserPath *string

func parse(query string) (*Response, error) {
	slog.Info("mysql parse receive query", slog.String("query", query))

	inputFile, err := os.CreateTemp("/tmp", "mysql-slow-input")
	if err != nil {
		slog.Error("mysql parse create input file", slog.String("error", err.Error()))
		return nil, err
	}
	defer os.Remove(inputFile.Name())
	slog.Info("mysql parse create input file success", slog.String("input file", inputFile.Name()))

	outputFile, err := os.CreateTemp("/tmp", "mysql-slow-output")
	if err != nil {
		slog.Error("mysql parse create output file", slog.String("error", err.Error()))
		return nil, err
	}
	defer os.Remove(outputFile.Name())
	slog.Info("mysql parse create output file success", slog.String("output file", outputFile.Name()))

	_, err = inputFile.WriteString(query)
	if err != nil {
		slog.Error("mysql parse write query", slog.String("error", err.Error()))
		return nil, err
	}
	slog.Info("mysql parse write query success")

	cmd := exec.Command(*ParserPath,
		"--sql-file", inputFile.Name(),
		"--output-path", outputFile.Name(),
		"--print-query-mode", "2",
	)

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err = cmd.Run()
	if err != nil {
		slog.Error("mysql parse execute tmysqlparse",
			slog.String("error", err.Error()),
			slog.String("command", cmd.String()),
			slog.String("stderr", stderr.String()))
		return nil, err
	}
	slog.Info("mysql parse execute tmysqlparse",
		slog.String("command", cmd.String()),
		slog.String("stdout", stdout.String()),
	)

	outputFile.Seek(0, 0)
	content, err := io.ReadAll(outputFile)
	if err != nil {
		slog.Error(
			"mysql parse read output file",
			slog.String("error", err.Error()),
			slog.String("output file", outputFile.Name()),
		)
		return nil, err
	}
	slog.Info("mysql parse read output file success", slog.String("output file", outputFile.Name()))

	var cmdRet struct {
		Result []Response `json:"result"`
	}
	err = json.Unmarshal(content, &cmdRet)
	if err != nil {
		slog.Error(
			"mysql parse unmarshal result",
			slog.String("error", err.Error()),
			slog.String("result", string(content)),
		)
		return nil, err
	}
	cmdRet.Result[0].QueryLength = len(query)

	slog.Info("mysql parse unmarshal result", slog.Any("struct result", cmdRet))

	return &cmdRet.Result[0], nil
}
