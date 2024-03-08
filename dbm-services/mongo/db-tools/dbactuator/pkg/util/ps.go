package util

import (
	"github.com/pkg/errors"
	"os/exec"
	"strconv"
	"strings"
)

// LinuxProcess represents a process in Linux.
type LinuxProcess struct {
	Pid  int
	Ppid int
	Comm string
}

// ListProcess lists all processes. It returns a list of processes and an error. just like ps -e -o pid,ppid,comm
func ListProcess() ([]LinuxProcess, error) {
	cmd := exec.Command("ps", "-e", "-o", "pid,ppid,comm")
	output, err := cmd.Output()
	if err != nil {
		return nil, err
	}

	lines := SplitLines(string(output))

	var processes []LinuxProcess
	if len(lines) < 2 {
		return nil, errors.New("no process")
	}
	for _, line := range lines[1:] {
		line = strings.TrimSpace(line) // remove leading and trailing spaces
		if line == "" {
			continue
		}
		fields := strings.Fields(line)
		if len(fields) < 3 {
			return nil, errors.Errorf("invalid fields: %q output: %q", line, string(output))
		}
		pid, err := strconv.Atoi(fields[0])
		if err != nil {
			return nil, err
		}
		ppid, err := strconv.Atoi(fields[1])
		if err != nil {
			return nil, err
		}
		processes = append(processes, LinuxProcess{
			Pid:  pid,
			Ppid: ppid,
			Comm: fields[2],
		})
	}
	return processes, nil
}
