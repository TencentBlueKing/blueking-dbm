package templates

import (
	"strings"

	"github.com/MakeNowJust/heredoc"
)

// Indentation TODO
const Indentation = `  `

// LongDesc TODO
func LongDesc(s string) string {
	if len(s) == 0 {
		return s
	}
	return normalizer{s}.heredoc().trim().string
}

type normalizer struct {
	string
}

func (s normalizer) heredoc() normalizer {
	s.string = heredoc.Doc(s.string)
	return s
}

func (s normalizer) trim() normalizer {
	s.string = strings.TrimSpace(s.string)
	return s
}
