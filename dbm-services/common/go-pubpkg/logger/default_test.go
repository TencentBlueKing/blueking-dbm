package logger

import (
	"os"
	"testing"
)

func TestDefault(t *testing.T) {
	file, err := os.OpenFile("./access.log", os.O_CREATE|os.O_APPEND|os.O_WRONLY, os.ModePerm)
	if err != nil {
		panic(err)
	}

	logger := New(file, false, InfoLevel)
	ResetDefault(logger)
	defer Sync()

	Info("testing default info")
}
