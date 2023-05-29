package ext3_check

import (
	"bufio"
	"bytes"
	"os/exec"
	"regexp"
	"strings"

	"github.com/pkg/errors"
	"golang.org/x/exp/slices"
)

func filterDirFs(dirs []string, filterFs ...string) (ftDirs []string, err error) {
	splitR := regexp.MustCompile(`\s+`)

	for _, dir := range dirs {
		var stdout, stderr bytes.Buffer
		cmd := exec.Command("df", "-P", "-T", dir)
		cmd.Stdout = &stdout
		cmd.Stderr = &stderr
		err = cmd.Run()
		if err != nil {
			return nil, errors.Wrapf(err, "df -P %s: %s", dir, stderr.String())
		}

		var lines []string
		scanner := bufio.NewScanner(strings.NewReader(stdout.String()))
		for scanner.Scan() {
			lines = append(lines, scanner.Text())
			err := scanner.Err()
			if err != nil {
				return nil, errors.Wrap(err, "scan failed")
			}
		}

		if len(lines) != 2 {
			err = errors.Errorf("parse df result failed: %s", stdout.String())
			return nil, err
		}

		splitLine := splitR.Split(lines[1], -1)
		if len(splitLine) != 7 {
			err = errors.Errorf("unexpect df output line: %s", lines[1])
			return nil, err
		}

		if slices.Index(filterFs, splitLine[1]) >= 0 {
			ftDirs = append(ftDirs, dir)
		}
	}

	return ftDirs, nil
}
