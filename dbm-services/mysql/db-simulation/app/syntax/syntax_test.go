package syntax_test

import (
	"testing"

	"github.com/stretchr/testify/assert"

	"dbm-services/mysql/db-simulation/app/syntax"
)

func TestKeywordFilter(t *testing.T) {
	matched, _ := syntax.KeyWordValidator("mysql-5.7", "call")
	assert.Equal(t, true, matched)
}
