package externalhandler

import (
	"regexp"
)

var splitPattern = regexp.MustCompile(`\s+`)

func splitBinArgs(item *externalItem) (bin string, args []string) {
	splitExec := splitPattern.Split(item.Executable, -1)

	switch item.Language {
	case "sh", "shell":
		bin = "sh"
		args = mergeSlices(splitExec, item.Args)
	case "bash":
		bin = "bash"
		args = mergeSlices(splitExec, item.Args)
	case "python", "python2", "python3", "perl":
		bin = item.Language
		args = mergeSlices(splitExec, item.Args)
	case "binary":
		bin = splitExec[0]
		args = mergeSlices(splitExec[1:], item.Args)
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
